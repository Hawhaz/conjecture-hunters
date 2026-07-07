#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lora_train.py — LoRA SFT de google/gemma-3-4b-it como operador de mutacion
espectral (PatternBoost / self-improvement), pensado para correr en la AMD
MI300X (ROCm). Consume finetune/data/sft_mutador.jsonl (formato chat cosechado
por cosechar.py) y produce un adapter LoRA + (opcional) un merge para servir con
vLLM.

Por que MI300X sin cuantizacion: la MI300X tiene 192 GB de HBM3; un modelo de 4B
en bf16 (~8 GB de pesos) + activaciones + estados de LoRA cabe holgadamente, asi
que NO se usa 4-bit/QLoRA (bitsandbytes ni siquiera es de primera clase en ROCm).
Entrenamos en bf16 puro con device_map="auto".

Este archivo se ESCRIBE y se compila (py_compile) en la maquina de desarrollo
(Windows, sin GPU), pero NO se ejecuta aqui: la guarda de dispositivo detecta la
ausencia de CUDA/ROCm e imprime las instrucciones exactas para lanzarlo en la
MI300X, saliendo con codigo 0 (no es un error: es el flujo esperado).

Dependencias (ver finetune/requirements.txt): transformers, peft, trl, datasets,
accelerate, y torch con ruedas ROCm (indice rocm) en la MI300X.

Uso (en la MI300X, tras `pip install -r finetune/requirements.txt`):
    # 1) entrenar el adapter LoRA
    python finetune/lora_train.py \
        --data finetune/data/sft_mutador.jsonl \
        --base google/gemma-3-4b-it \
        --out finetune/out/adapter \
        --epochs 3

    # 2) mergear el adapter al base para servir con vLLM
    python finetune/lora_train.py --merge \
        --base google/gemma-3-4b-it \
        --adapter finetune/out/adapter \
        --merged finetune/out/merged

    # 3) servir con vLLM (ROCm) y apuntar el orquestador:
    #    vllm serve finetune/out/merged --port 8000 --dtype bfloat16
    #    set CONJ_API_BASE=http://<host-mi300x>:8000/v1
    #    set CONJ_MODEL=finetune/out/merged
    #    python orquestador/orquestar.py --conjeturas cal1,cal2,cal3 --llm ollama ...
"""
from __future__ import annotations

import argparse
import os
import sys


# ---------------------------------------------------------------------------
# Guarda de dispositivo: sin CUDA/ROCm visible, imprime instrucciones MI300X y
# sale 0. NO intenta entrenar (aqui no hay GPU). Se llama antes de cargar pesos.
# ---------------------------------------------------------------------------
def _hay_gpu() -> bool:
    """True si torch ve una GPU (CUDA o ROCm/HIP). False si torch no esta o no
    hay dispositivo. Nunca lanza: la ausencia de torch cuenta como 'sin GPU'."""
    try:
        import torch  # import perezoso: no es dependencia en la maquina de dev
    except Exception:
        return False
    try:
        if torch.cuda.is_available() and torch.cuda.device_count() > 0:
            return True
    except Exception:
        pass
    # ROCm expone su version en torch.version.hip cuando el build es de ROCm.
    try:
        return bool(getattr(torch.version, "hip", None)) and torch.cuda.is_available()
    except Exception:
        return False


_INSTRUCCIONES_MI300X = r"""
================================================================================
[lora_train] No se detecto GPU (CUDA/ROCm) en esta maquina.
Este script NO entrena en CPU a proposito (un 4B en CPU es inviable). Lanza el
entrenamiento en la AMD MI300X (notebooks.amd.com/hackathon), donde:

  # 0) entorno ROCm (una sola vez)
  python -m venv .venv && source .venv/bin/activate
  # torch con ruedas ROCm (ajusta la version de ROCm a la del host):
  pip install --index-url https://download.pytorch.org/whl/rocm6.2 torch
  pip install -r finetune/requirements.txt

  # 1) sanity: torch ve la MI300X
  python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
  # -> True  AMD Instinct MI300X

  # 2) entrena el adapter LoRA (bf16, sin cuantizacion; 192GB HBM sobran para 4B)
  python finetune/lora_train.py \
      --data finetune/data/sft_mutador.jsonl \
      --base google/gemma-3-4b-it \
      --out finetune/out/adapter --epochs 3

  # 3) mergea para servir con vLLM
  python finetune/lora_train.py --merge \
      --base google/gemma-3-4b-it \
      --adapter finetune/out/adapter \
      --merged finetune/out/merged

  # 4) sirve con vLLM (ROCm) y apunta el orquestador via CONJ_* (multi-backend):
  vllm serve finetune/out/merged --port 8000 --dtype bfloat16 --max-model-len 4096
  export CONJ_API_BASE=http://localhost:8000/v1
  export CONJ_MODEL=finetune/out/merged
  export CONJ_API_KEY=EMPTY
  python orquestador/orquestar.py --conjeturas cal1,cal2,cal3 --llm ollama --iters 400

Sugerencia: para VELOCIDAD de desarrollo HOY (sin esperar la MI300X) puedes
harvestear/probar el loop contra Fireworks (cupon $50), pero el premio
"Best AMD-Hosted Gemma" EXIGE que el modelo corra en hardware AMD => el LoRA y el
serving finales van SI o SI en la MI300X. Ver finetune/PLAN.md.
================================================================================
"""


# ---------------------------------------------------------------------------
# Config LoRA (segun el enunciado): r=16, alpha=32, dropout=0.05, target q/k/v/o
# + gate/up/down proj. Estos son los nombres de modulo de la familia Gemma.
# ---------------------------------------------------------------------------
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",       # atencion
    "gate_proj", "up_proj", "down_proj",          # MLP
]


# ---------------------------------------------------------------------------
# Dataset: lee el JSONL de chat y aplica el chat template del tokenizer para
# producir el texto que el SFTTrainer empaqueta (packing). Cada linea es
# {"messages":[{role,content}...]} -> string via apply_chat_template.
# ---------------------------------------------------------------------------
def _cargar_dataset(ruta_jsonl: str, tokenizer):
    """Devuelve un datasets.Dataset con una columna 'text' ya formateada con el
    chat template de Gemma (roles system/user/assistant). El SFTTrainer entrena
    sobre 'text' con packing."""
    from datasets import load_dataset

    ds = load_dataset("json", data_files=ruta_jsonl, split="train")

    def _fmt(ejemplo):
        # add_generation_prompt=False: el turno del assistant YA esta en messages
        # (es el target); no queremos el prompt de generacion colgando al final.
        texto = tokenizer.apply_chat_template(
            ejemplo["messages"], tokenize=False, add_generation_prompt=False)
        return {"text": texto}

    ds = ds.map(_fmt, remove_columns=ds.column_names)
    return ds


# ---------------------------------------------------------------------------
# Entrenamiento LoRA.
# ---------------------------------------------------------------------------
def entrenar(args) -> int:
    import torch  # ya sabemos que hay GPU (paso la guarda)
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    print("[lora_train] base=%s data=%s out=%s epochs=%s"
          % (args.base, args.data, args.out, args.epochs), flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.base, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    modelo = AutoModelForCausalLM.from_pretrained(
        args.base,
        torch_dtype=torch.bfloat16,   # bf16 nativo en MI300X (sin cuantizacion)
        device_map="auto",
        attn_implementation="eager",  # robusto en ROCm; sube a sdpa/flash si aplica
    )
    modelo.config.use_cache = False   # requerido con gradient checkpointing

    lora = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )

    ds = _cargar_dataset(args.data, tokenizer)
    print("[lora_train] ejemplos de entrenamiento: %d" % len(ds), flush=True)

    cfg = SFTConfig(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,                 # 2e-4
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,                             # MI300X
        gradient_checkpointing=True,
        packing=True,                          # empaqueta secuencias (mejor throughput)
        max_seq_length=args.max_seq_len,
        dataset_text_field="text",
        report_to="none",
        optim="adamw_torch",
    )

    trainer = SFTTrainer(
        model=modelo,
        args=cfg,
        train_dataset=ds,
        peft_config=lora,
        processing_class=tokenizer,
    )
    trainer.train()

    os.makedirs(args.out, exist_ok=True)
    trainer.save_model(args.out)               # guarda SOLO el adapter LoRA
    tokenizer.save_pretrained(args.out)
    print("[lora_train] adapter LoRA guardado en %s" % args.out, flush=True)
    print("[lora_train] siguiente: --merge para servir con vLLM (ver PLAN.md).",
          flush=True)
    return 0


# ---------------------------------------------------------------------------
# Merge: base + adapter -> pesos fusionados (para vLLM, que sirve mejor un modelo
# denso que un adapter LoRA en caliente).
# ---------------------------------------------------------------------------
def mergear(args) -> int:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("[lora_train --merge] base=%s adapter=%s -> merged=%s"
          % (args.base, args.adapter, args.merged), flush=True)

    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="auto")
    modelo = PeftModel.from_pretrained(base, args.adapter)
    modelo = modelo.merge_and_unload()          # funde LoRA en los pesos densos

    os.makedirs(args.merged, exist_ok=True)
    modelo.save_pretrained(args.merged, safe_serialization=True)
    tok = AutoTokenizer.from_pretrained(args.base, use_fast=True)
    tok.save_pretrained(args.merged)
    print("[lora_train --merge] modelo fusionado en %s" % args.merged, flush=True)
    print("[lora_train --merge] sirve con: vllm serve %s --dtype bfloat16"
          % args.merged, flush=True)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parsear_args(argv=None):
    ap = argparse.ArgumentParser(
        description="LoRA SFT de gemma-3-4b-it como operador de mutacion "
                    "(MI300X/ROCm, bf16, sin cuantizacion).")
    ap.add_argument("--data",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "data", "sft_mutador.jsonl"),
                    help="JSONL de chat (salida de cosechar.py)")
    ap.add_argument("--base", default="google/gemma-3-4b-it",
                    help="modelo base HF")
    ap.add_argument("--out",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "out", "adapter"),
                    help="destino del adapter LoRA")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch", type=int, default=8,
                    help="batch por dispositivo (la HBM de 192GB permite subirlo)")
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq-len", type=int, default=4096)
    # modo merge
    ap.add_argument("--merge", action="store_true",
                    help="fusiona un adapter existente en el base (para vLLM)")
    ap.add_argument("--adapter",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "out", "adapter"),
                    help="(merge) ruta del adapter LoRA a fusionar")
    ap.add_argument("--merged",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "out", "merged"),
                    help="(merge) destino de los pesos fusionados")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parsear_args(argv)

    # Guarda de dispositivo: sin GPU, instrucciones + exit 0 (flujo esperado en dev).
    if not _hay_gpu():
        print(_INSTRUCCIONES_MI300X)
        print("[lora_train] Sin GPU visible => no se entrena aqui. Exit 0.")
        return 0

    if args.merge:
        return mergear(args)
    return entrenar(args)


if __name__ == "__main__":
    sys.exit(main())

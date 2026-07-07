# finetune/PLAN.md — Especializar gemma-3-4b como operador de mutación espectral

Estrategia del pipeline de **self-improvement + LoRA** para convertir a
`google/gemma-3-4b-it` en un **operador de mutación** (estilo PatternBoost) que
propone deltas de aristas que suben el `gap` de las conjeturas CAL-1/2/3, y
correrlo en la **AMD MI300X** para calificar al premio *Best AMD-Hosted Gemma*.

Contexto que ya funciona (no partimos de cero): el orquestador evolutivo corre
**end-to-end** con la cascada T1→T2(Rust)→T3(certificado exacto). En una corrida
mock determinista de 200 iteraciones, **CAL-1 alcanza gap=+0.2263 y `certificar`
lo confirma** (`metodo=exacto-charpoly`, n=23); CAL-2 muere en dos-estrellas
grandes (gap≈+0.49 medido con el binario Rust). El evaluador usa
`backend_usado="rust"` cuando el binario está presente y cae al oráculo Python
por paridad (contrato de 86 tests, |Δgap|≤1e-9). **El LLM NO es el cuello de
botella de correctitud** — es el generador de movimientos. Por eso el fine-tuning
es una palanca de *hit-rate/velocidad de descubrimiento*, no de validez.

---

## (a) Measure-first: NO entrenar hasta saber que el prompt es el cuello de botella

Antes de gastar una hora de MI300X en LoRA, medir la Gemma **en vivo con buen
prompt + best-of-N**, que es lo que `orquestador/mutador.py` ya hace (few-shot
ranqueado ordinal + `n_llm=4`, fallback a mock):

1. Levantar Gemma (Ollama hoy, o Fireworks/vLLM) y correr el loop con
   `--llm ollama` sobre CAL-1/2/3.
2. Instrumentar el **hit-rate del LLM**: fracción de deltas propuestos que (i)
   parsean, (ii) decodifican a grafo conexo válido, (iii) **suben el gap** del
   padre. `_mutar_ollama` ya registra `detalle="delta:+a/-b"` vs
   `"sin_delta_valido_en_NN"`; basta agregarlo al CSV/meta.
3. Comparar contra el baseline mock (operadores estructurales) a igualdad de
   evaluaciones T2.

**Decisión**: sólo hacer LoRA si el LLM base, incluso con best-of-N y el prompt
bueno, tiene hit-rate bajo (produce prosa, rompe conectividad, ignora el formato
de delta, o no se mueve hacia las familias extremales). Si el prompt bien armado
ya bate al mock, el fine-tuning es opcional (mejora marginal). Si el 4B base no
respeta el formato o no "entiende" las familias, LoRA lo arregla barato: el
dataset cosechado enseña EXACTAMENTE el formato de delta y los movimientos
extremales (RA2).

## (b) Fireworks HOY para velocidad; MI300X OBLIGATORIA para el premio

- **Hoy (dev velocity)**: apuntar el backend a **Fireworks** (cupón \$50,
  `FW-LABLAB-QGUM`) es un cambio de UNA config gracias al soporte multi-backend
  de `mutador.py`:

  ```bat
  set CONJ_API_BASE=https://api.fireworks.ai/inference/v1
  set CONJ_MODEL=accounts/fireworks/models/gemma-3-4b-it
  set CONJ_API_KEY=%FIREWORKS_API_KEY%
  python orquestador\orquestar.py --conjeturas cal1,cal2,cal3 --llm ollama --iters 400
  ```

  Sirve para: (i) tener el loop LLM-real vivo sin esperar cuota de GPU, (ii)
  **cosechar datos reales** (extender `cosechar.py` para volcar los deltas
  ganadores que produzca la Gemma en vivo, no sólo los del mock), (iii) medir
  hit-rate (paso a).

- **Para el premio**: *Best AMD-Hosted Gemma* **exige** que el modelo corra en
  hardware AMD. **Fireworks NO califica** (es su propia infra). Por lo tanto el
  **LoRA final y el serving final van SÍ o SÍ en la MI300X** (ROCm + vLLM).
  Fireworks es andamiaje de desarrollo; el entregable premiado corre en la
  MI300X.

## (c) Pipeline completo: harvest → LoRA (MI300X) → merge → serve (vLLM) → apuntar el orquestador

1. **Harvest** (esta máquina, sin GPU, sólo networkx/numpy):
   ```bat
   python finetune\cosechar.py
   ```
   Genera `finetune/data/sft_mutador.jsonl` (~6.1k ejemplos hoy) en el MISMO
   formato de chat que verá la Gemma en vivo: `system` = texto literal de
   `prompts/system_mutador.md`; `user` = `plantilla_usuario.md` renderizada con
   el grafo PADRE como lista de aristas + card de conjetura + contexto de RANGO
   ORDINAL; `assistant` = el delta aplicado (`add edge (u,v); remove edge (x,y)`,
   el formato exacto que `mutador.py::_parsear_delta` entiende). Dos currículos:
   (A) mutaciones que suben el gap (self-improvement sobre operadores
   estructurales) y (B) **currículo extremal** (RA2): morphing plano→extremal
   (estrella/camino → cometa, DTC, kite, dos-estrellas) que enseña los
   movimientos que rompen estas conjeturas. Cada delta se **verifica** por
   round-trip (`aplicar_delta(padre) == hijo`): todos son movimientos legales.

2. **LoRA SFT** (MI300X, ROCm, bf16, sin cuantización):
   ```bash
   pip install --index-url https://download.pytorch.org/whl/rocm6.2 torch
   pip install -r finetune/requirements.txt
   python finetune/lora_train.py --data finetune/data/sft_mutador.jsonl \
       --base google/gemma-3-4b-it --out finetune/out/adapter --epochs 3
   ```
   Config: `r=16, alpha=32, dropout=0.05`, target `q/k/v/o + gate/up/down proj`,
   `lr=2e-4`, 2-3 épocas, packing, gradient checkpointing, `device_map="auto"`.
   Sin 4-bit/QLoRA: 192 GB de HBM sobran para un 4B en bf16 (bitsandbytes ni es
   de primera clase en ROCm). Guarda el adapter en `finetune/out/adapter/`.

3. **Merge** (para servir denso, mejor con vLLM que un adapter en caliente):
   ```bash
   python finetune/lora_train.py --merge --base google/gemma-3-4b-it \
       --adapter finetune/out/adapter --merged finetune/out/merged
   ```

4. **Serve con vLLM (ROCm)** y **apuntar el orquestador** — un cambio de config,
   sin tocar código (multi-backend):
   ```bash
   vllm serve finetune/out/merged --port 8000 --dtype bfloat16 --max-model-len 4096
   export CONJ_API_BASE=http://<host-mi300x>:8000/v1
   export CONJ_MODEL=finetune/out/merged
   export CONJ_API_KEY=EMPTY
   python orquestador/orquestar.py --conjeturas cal1,cal2,cal3 --llm ollama --iters 400
   ```
   El backend `ollama` de `mutador.py` es genérico: sonda `/v1/models` (con
   Bearer) para Fireworks/vLLM y `/api/tags` para Ollama; si el endpoint cae,
   **fallback a mock** (nunca crashea). Los 86 tests de paridad siguen siendo el
   ORÁCULO: `gap_rust == gap_python` a 1e-9 gobierna la aceptación; el LLM sólo
   propone, la cascada T2/T3 decide.

5. **Iterar (self-improvement real)**: re-cosechar desde las corridas del modelo
   fine-tuneado (los deltas que la Gemma-LoRA sí acierta en vivo), reentrenar,
   re-servir. Cada vuelta sube el hit-rate → más contraejemplos por evaluación.

## (d) Cómo servir gemma-3-4b en la MI300X con vLLM

```bash
# 1) torch ROCm + vLLM (rueda ROCm) en el host MI300X
pip install --index-url https://download.pytorch.org/whl/rocm6.2 torch
pip install vllm            # build ROCm; expone API OpenAI-compatible en /v1
# 2) sanity
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
#   -> True  AMD Instinct MI300X
# 3) servir el modelo fusionado (o el base google/gemma-3-4b-it para el baseline)
vllm serve finetune/out/merged \
     --port 8000 --dtype bfloat16 --max-model-len 4096 \
     --gpu-memory-utilization 0.90
# 4) probar el endpoint (formato OpenAI /v1/chat/completions)
curl http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" \
     -d '{"model":"finetune/out/merged","messages":[{"role":"user","content":"add edge (0,7)?"}]}'
```

Notas MI300X/ROCm:
- bf16 nativo; sin cuantización (HBM de sobra para 4B).
- Una sola MI300X sirve el 4B con holgura; subir `--gpu-memory-utilization` si se
  quiere mayor `--max-num-seqs` para best-of-N con más concurrencia.
- El baseline SIN LoRA (paso a) también se sirve así (`vllm serve
  google/gemma-3-4b-it`): así el A/B (base vs LoRA) corre sobre el MISMO stack.

---

### Resumen de una línea

El loop ya certifica contraejemplos (CAL-1 gap=+0.2263 `exacto-charpoly`); el
LoRA sobre el dataset cosechado (formato de chat idéntico al de producción, con
currículo extremal RA2) sube el hit-rate del operador de mutación, y todo el
entrenamiento/serving finales corren en la MI300X (ROCm + vLLM) — Fireworks es
sólo andamiaje de velocidad para desarrollo, no califica al premio AMD.

# Runbook — lanzar Conjecture Hunters en AMD MI300X (turnkey)

Objetivo: en la próxima sesión de GPU, **un solo comando** arranca el hunt
multi-carril con **Gemma servido en la MI300X** y el ledger durable.

## 0. Qué notebook lanzar (importante)

En `notebooks.amd.com` → "Launch": elige el entorno **genérico
`ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9`** (el del dropdown).

- **NO** uses la tarjeta de ejemplo *"SH Dev Day: RL with vERL Workshop"* — esa es
  una **plantilla tutorial de AMD** (fine-tune de **Qwen3-4B** con GRPO/vERL). No es
  nuestro proyecto. Nosotros usamos **Gemma**, no Qwen.
- Cuota: **4 h por cada 24 h**. No la gastes en setup; el pack/tests son CPU y ya
  pasan verdes en local — la GPU es para **Gemma (vLLM) + LoRA**.

## 1. Gotcha de red (una vez por sesión)

La caja **intercepta el HTTPS con un proxy TLS** (`AMD_ONECLICK_OPENCODE_TLS_PROXY
→ 10.98.140.215:8443`) que presenta un **cert self-signed**. Por eso `git clone`,
`pip` y HuggingFace fallan la verificación de cert.

**Fix seguro (NO desactiva TLS):** añadir el **CA raíz del proxy de AMD** al trust
store → la verificación queda **encendida, contra el CA de AMD**. Es el paso estándar
detrás de un proxy corporativo. Lo hace `run_gpu.sh --trust-amd-proxy`.
(El clasificador bloquea `sslVerify=false` / `--trusted-host` — con razón; no usamos eso.)

## 2. Un comando

Abre una **Terminal** en JupyterLab y pega:

```bash
cd /workspace
# opción A: si ya trae el repo por otro medio, omite el clone con --no-clone
curl -fsSL https://raw.githubusercontent.com/Hawhaz/conjecture-hunters/master/deploy/run_gpu.sh -o run_gpu.sh 2>/dev/null || true
# (si el curl falla por el proxy, primero corre el fix de CA a mano — ver deploy/run_gpu.sh)
bash run_gpu.sh --trust-amd-proxy --serve-gemma --iters 4000
```

Qué hace `run_gpu.sh`:
1. Confía el CA del proxy de AMD (TLS verificado).
2. Clona el repo público + instala deps (networkx, numpy, sympy).
3. Corre el **GATE anti-basura** (`pack_conjeturas.py --gate`) — si sale rojo, **no lanza** (0 basura).
4. Sirve **Gemma** (`google/gemma-3-4b-it`) en **vLLM :8000** y apunta el mutador ahí
   (`CONJ_API_BASE`/`CONJ_MODEL`).
5. Lanza el hunt multi-carril + ledger. Hallazgos → `hallazgos/` (ALERTAS.md, HIT_*.md, shards/).

## 3. Paralelismo (honesto)

No son "miles de instancias/VMs" (el portal da **una sesión por equipo**). El paralelismo
masivo son **miles de workers dentro del nodo**: motor Rust (rayon) evaluando miles de
grafos/seg + muchos carriles concurrentes + **Gemma en la GPU** proponiendo mutaciones +
certificado exacto + ledger. Eso es lo que demostramos y es real.

## 4. LoRA (auto-mejora, opcional)

`python finetune/lora_train.py` (dataset `finetune/data/sft_mutador.jsonl`, 6100 ejemplos).
En la imagen `Unsloth + llama.cpp for Radeon` es aún más directo para el fine-tune.

## 5. Pendiente ANTES del lanzamiento "de verdad" (para no meter basura)

- [ ] **11 carriles nuevos → 20** validados con su gate (task #35; specs en
  `retos/ESPECIFICACIONES_CARRILES.md`).
- [ ] **Cablear el pack al orquestador** Gemma-guiado por-carril (task #37).
- [ ] Verificar el Docker end-to-end (task #34).

Hasta cerrar eso, `run_gpu.sh` corre la **batería validada de 9 carriles + ledger** (sólido,
0 basura); el hunt Gemma-guiado por-carril entra al terminar #35/#37.

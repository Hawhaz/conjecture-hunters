# GPU Session Log — AMD MI300X (transparency record)

This file is a transparent, timestamped record of what was run on AMD hardware for the
**Conjecture Hunters** submission, so the trajectory is fully auditable by the judges.

## Methodology & transparency statement

- This is an **AI hackathon** (AMD Developer Hackathon ACT II — building with Gemma on AMD).
  The system was **built with AI assistance** (Claude), which is the intended spirit of the
  event, not a shortcut around the work.
- **Everything is independently verifiable without trusting us:**
  - The **public repository** (github.com/Hawhaz/conjecture-hunters) has the **full, granular
    commit history** — every step of how the system was built is on the record.
  - Every refutation ships an **exact, machine-checkable certificate** (integer / algebraic-number
    arithmetic, no floating point in the verdict). Anyone can re-run `python retos/*.py` and confirm.
  - The **hit-ledger** (`hallazgos/`) records every candidate with its `graph6` and a reproduction
    snippet, `fsync`-durable, so no discovery is lost or unexplained.
  - The **anti-garbage gate** (`retos/test_pack_conjeturas.py`) blocks miscoded conjectures
    (it already caught the K4 false positive on Bollobás–Nikiforov).
- No result in this repo depends on a hidden manual step. If it isn't reproducible from the repo,
  it isn't claimed.

## Access

- **Portal:** https://notebooks.amd.com — "AMD AI Notebooks" (GPU: AMD ROCm, env: JupyterLab, on-demand).
- **Account:** AMD AI Developer Program (team lead ofidenciotirado@gmail.com / GitHub `Hawhaz`).
- **Auth:** AMD SSO (Dev Program), completed **manually by the team lead**. The assistant never
  handles credentials, passwords, or SSO.
- **Fireworks AI credits:** $50 coupon `FW-LABLAB-QGUM` (for serving Gemma via API when not on GPU).

## Planned run order (no un-validated lanes reach the GPU)

1. Clone the public repo on the notebook; install deps (networkx, numpy, sympy; optional Rust build).
2. Run the **validated 9-lane pack + hit-ledger** (`python retos/pack_conjeturas.py`) and the
   Jia–Song refutation certificate — 100% gate-green, zero garbage. Prove the system runs on ROCm.
3. Add the **11 additional lanes** once each passes its sanity gate locally (→ 20 lanes).
4. Full multi-lane hunt + **Gemma as mutation operator** (Fireworks now / AMD-hosted MI300X for the
   prize) + LoRA self-improvement, with the ledger firing on any certified violation.

## Step log

| timestamp (local) | step | detail |
|---|---|---|
| 2026-07-07 | session start | Opened notebooks.amd.com; reached AMD SSO sign-in (ROCm / JupyterLab / on-demand). Awaiting manual login by team lead. |
| 2026-07-07 | logged in + launched | Team team-3592. Launched the generic **ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9** notebook (NOT the "SH Dev Day / Qwen3-4B / vERL" sample). Opened a terminal (root@/workspace). |
| 2026-07-07 | network gotcha | Outbound HTTPS is MITM-proxied by `AMD_ONECLICK_OPENCODE_TLS_PROXY` (10.98.140.215:8443) with a **self-signed cert** → git/pip/HuggingFace cert verification fails. System clock OK. TLS-weakening (`sslVerify=false`) was correctly blocked; the safe fix (trust the AMD proxy root CA — verification stays ON) is documented in `RUNBOOK_MI300X.md` / `deploy/run_gpu.sh --trust-amd-proxy`. |
| 2026-07-07 | paused (budget) | **Stopped the session** to preserve the 4h/24h quota — the pack/ledger/tests are CPU-only and already pass locally, so no need to burn GPU time on them. Turnkey `deploy/run_gpu.sh` + runbook written. Will relaunch for the **Gemma-on-vLLM + LoRA** run (the only GPU-worthy part) once the 11 new lanes + orchestrator wiring are done. |

_(appended as the session proceeds)_

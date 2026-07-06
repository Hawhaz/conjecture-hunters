# Conjecture Hunters 🔭

**Evolutionary counterexample-hunting engine for spectral graph theory conjectures — LLM mutations (Gemma) on AMD infrastructure.**

Built for the **AMD Developer Hackathon: ACT II** (Track 3 — Unicorn). The system evolves *programs that print graphs*; a frozen evaluator computes spectral invariants and rewards proximity to refuting published mathematical conjectures. An LLM (Gemma via Fireworks AI / AMD Developer Cloud, or local Ollama) acts as the mutation operator inside an OpenEvolve loop.

## Why it matters

Refuting a conjecture requires exhibiting ONE verifiable counterexample — a perfect fit for search + cheap verification. This repo re-discovers, from scratch and in seconds, results that took neural networks 5,000 iterations (Wagner 2021) and the state-of-the-art AMCS algorithm 46 seconds (Vito–Stefanus 2023):

| Result (validated against published ground truth) | Ours |
|---|---|
| CAL-1 (λ₁+μ ≥ √(n−1)+1, AutoGraphiX): counterexample | **0.6 s** (AMCS reference: 46 s) |
| GA multi-start, 20 runs with structural seeds | **20/20** find counterexamples at gen 0 |
| GA pure dynamics (no seeds, no baseline) | **19/20** within 1,000 generations |
| Fixture B — λ₂ > harmonic index (CAL-2) | verified: λ₂−Hc = +0.0795 |
| Fixture C — π + ∂_{⌊2D/3⌋} < 0, n=203 (CAL-3, hardest) | verified: score 0.000285 ≈ published 0.00028 |

Full TDD: **86 tests green** (test vectors with closed forms, exhaustive oracle over all 994 connected graphs n≤7, adversarial sandbox battery, deterministic-mock loop test with checkpoint/resume).

## Quickstart

```bash
# Docker (submission requirement): builds AND runs the test suite, then a GA demo
docker build -t conjecture-hunters .
docker run --rm conjecture-hunters

# Local
pip install -r requirements.txt
python -m pytest                                # 86 passed, 1 skipped (optional fixture)
python calibracion/ga_graphs.py --runs 20       # GA multi-start; CSV log per generation
python calibracion/extraer_fixture_amcs.py      # re-find the λ₁+μ counterexample in <1 s
```

## The evolutionary loop (LLM as mutation operator)

```bash
# 1. Any OpenAI-compatible endpoint works. Pick one in configs/:
#    - mock (deterministic, for CI):    python -m mock_llm.server --port 8000
#    - Ollama local:                    api_base http://localhost:11434/v1, model gemma3:4b
#    - Fireworks AI / AMD MI300X:       set api_base + api_key in configs/calibracion.yaml
openevolve-run calibracion/programa_inicial.py evaluators/agx_l1_mu.py \
    --config configs/calibracion.yaml --iterations 200
```

Swapping mock → Ollama → Fireworks/MI300X is **one line of config** (`api_base`). The evolved programs run in a hardened sandbox (AST allowlist, 30 s timeout, 2 GB RAM cap, 1 MB stdout, structured rejection — the orchestrator never dies).

## Architecture

```
common/invariantes.py      λ₁, μ (fast + reference impls), strict graph validation
evaluators/agx_l1_mu.py    frozen evaluator: gap = √(n−1)+1 − (λ₁+μ); sandbox; gap>0 ⇔ counterexample
evaluators/toy_max_edges.py loop smoke-test evaluator (known optimum = 30)
calibracion/ga_graphs.py   direct GA (no LLM): validates search dynamics; CSV logs
calibracion/amcs_baseline.py faithful Python port of AMCS (arXiv 2306.07956) — SOTA as population seed
mock_llm/server.py         deterministic OpenAI-compatible mock (round-robin canned diffs)
tests/                     the spec, frozen: levels 0–3 + published-counterexample fixtures
configs/                   OpenEvolve configs (mock / Ollama / Fireworks-MI300X)
docs/                      design specs (calibration vertical + conjecture portfolio)
```

## Roadmap (hackathon week)

20+ conjecture lanes in parallel on MI300X (portfolio in `docs/PAQUETE_2`), Gemma-synthesized mutation-operator bank, UCB bandit across lanes, live dashboard, exact-arithmetic certificate verifier.

## Team

**Conjecture Hunters** — AMD Developer Hackathon: ACT II, July 2026.

Referencias: Wagner, *Constructions in combinatorics via neural networks* (2021) · Vito & Stefanus, *Adaptive Monte Carlo search for conjecture refutation in graph theory* (arXiv 2306.07956) · AutoGraphiX / Aouchiche–Hansen conjecture families · OpenEvolve (evolutionary coding harness).

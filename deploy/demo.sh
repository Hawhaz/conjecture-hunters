#!/usr/bin/env sh
# Demo por defecto del contenedor (docker run conjecture-hunters). ~1-2 min, CPU.
set -e
echo "================= Conjecture Hunters — demo ================="
echo "AlphaEvolve-style refutation of open spectral-graph conjectures."
echo
echo "[1/3] STAR RESULT: refuting Jia-Song (2018), exact + primary-source cross-check"
python retos/verificacion_fuente_primaria.py
echo
echo "[2/3] 20-lane anti-garbage GATE (validation lanes re-discover known CEs; open lanes hold)"
python retos/pack_conjeturas.py --gate
python retos/pack_extra.py --gate
echo
echo "[3/3] SWARM: 30s of parallel local hunting over the 20 conjectures (durable ledger)"
python orquestador/enjambre.py --minutos 0.5 --workers 0
python hallazgos/registro.py --resumen || true
echo
echo "Done. Counterexamples (if any) are in hallazgos/ with exact certificates."
echo "Full GPU run (Gemma on AMD MI300X):  bash deploy/run_gpu.sh --trust-amd-proxy --serve-gemma"

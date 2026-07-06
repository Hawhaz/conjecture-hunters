"""Humo del loop REAL contra Ollama local (gemma3:4b): pocas iteraciones de CAL-1.

Valida el camino completo LLM-real → diff SEARCH/REPLACE → sandbox → gap ANTES de
gastar créditos de GPU. Éxito del humo = el loop itera y la BD crece sin crash
(no se exige contraejemplo: gemma3:4b en CPU es el enchufe, no el músculo).
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    from openevolve.config import load_config
    from openevolve.controller import OpenEvolve

    ap = argparse.ArgumentParser()
    ap.add_argument("--iteraciones", type=int, default=8)
    ap.add_argument("--config", default=os.path.join(RAIZ, "configs", "calibracion_ollama.yaml"))
    ap.add_argument("--out", default=os.path.join(RAIZ, "calibracion", "runs", "humo_ollama"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    ctl = OpenEvolve(
        os.path.join(RAIZ, "calibracion", "programa_inicial.py"),
        os.path.join(RAIZ, "evaluators", "agx_l1_mu.py"),
        cfg,
        output_dir=args.out,
    )
    mejor = asyncio.run(ctl.run(iterations=args.iteraciones))
    score = None if mejor is None else mejor.metrics.get("combined_score")
    print(f"HUMO_OK mejor_score={score} programas_en_BD={len(ctl.database.programs)}", flush=True)


if __name__ == "__main__":
    main()

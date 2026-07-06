"""Extrae el Fixture A (§6): contraejemplo de λ₁+μ, corriendo el algoritmo del
repo de AMCS (github.com/valentinovito/Adaptive_MC_Search) con NUESTRO gap como
score (idéntico a su Conj1_score). Al hallar gap > 0 lo guarda en
tests/fixtures/fixture_l1mu.g6 y lo re-verifica con el evaluador congelado.

Uso: python calibracion/extraer_fixture_amcs.py [--semilla 1] [--presupuesto-s 600]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx

from calibracion.amcs_baseline import amcs
from evaluators.agx_l1_mu import gap_grafo

RUTA_FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tests", "fixtures", "fixture_l1mu.g6")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=1)
    ap.add_argument("--presupuesto-s", type=float, default=600.0)
    ap.add_argument("--solo-arboles", action="store_true", default=True,
                    help="el contraejemplo publicado de λ₁+μ es un árbol (AMCS lo halla en árboles)")
    args = ap.parse_args()

    import random

    t0 = time.time()
    semilla = args.semilla
    while time.time() - t0 < args.presupuesto_s:
        rng = random.Random(semilla)
        arbol = nx.random_labeled_tree(5, seed=semilla)
        print(f"[extractor] corrida con semilla {semilla} (árbol inicial de orden 5)", flush=True)
        G = amcs(gap_grafo, grafo_inicial=arbol, max_depth=5, max_level=3,
                 solo_arboles=args.solo_arboles, rng=rng, verboso=True)
        gap = gap_grafo(G)
        if gap > 1e-9:
            g6 = nx.to_graph6_bytes(G, header=False).decode("ascii").strip()
            with open(RUTA_FIXTURE, "w", encoding="ascii", newline="\n") as f:
                f.write(g6 + "\n")
            H = nx.convert_node_labels_to_integers(nx.read_graph6(RUTA_FIXTURE))
            gap_releido = gap_grafo(H)
            print(f"[extractor] CONTRAEJEMPLO: n={G.number_of_nodes()}, gap={gap:.8f}")
            print(f"[extractor] guardado en {RUTA_FIXTURE} (g6={g6!r}); gap releído={gap_releido:.8f}")
            assert gap_releido > 1e-9
            print(f"[extractor] tiempo total: {time.time() - t0:.1f} s")
            return 0
        print(f"[extractor] semilla {semilla} sin contraejemplo (mejor gap={gap:.6f}); sigo", flush=True)
        semilla += 1
    print("[extractor] presupuesto agotado sin contraejemplo", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

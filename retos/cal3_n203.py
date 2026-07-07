#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reto CAL-3 (pi + d_floor(2D/3) > 0): re-descubrir y CERTIFICAR el benchmark
que SOLO AMCS pudo resolver (arXiv 2306.07956), y mapear la FAMILIA completa de
contraejemplos.

Receta de la investigacion (RA2): la familia extremal es el COMETA DE DOBLE COLA
(double-tailed comet) = un hub-estrella con h hojas + dos caminos (colas) colgados
del hub. El contraejemplo publicado n=203 es exactamente el centro de S191 (hub
con 190 hojas) unido a un extremo de P7 (cola de 7) y a un extremo de P5 (cola de
5): n = 1 + 190 + 7 + 5 = 203, diametro D=12, k = floor(2*12/3) = 8, score
gap = -(pi + d_8) ~ +0.000285.

Estrategia: en vez de busqueda ciega (que a AMCS le tomo 16.5 min), sembramos la
familia extremal (lo que el propio SOTA hace: AMCS arranca del esqueleto-cola
P13) y barremos sus parametros con el EVALUADOR RUST en lote paralelo (~10k
ev/s). Eso re-descubre no UN contraejemplo sino la FAMILIA entera, en segundos.
Luego el CERTIFICADO EXACTO (mpmath-80dps + residuo de Weyl) sella el n=203.

Uso:  python retos/cal3_n203.py
"""
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "certificados"))

import networkx as nx

from orquestador.evaluar import Evaluador


def cometa_doble_cola(h: int, t1: int, t2: int) -> nx.Graph:
    """Hub 0 con h hojas + dos colas (caminos) de t1 y t2 vertices colgadas del hub.

    n = 1 + h + t1 + t2. Con h=190, t1=7, t2=5 -> el contraejemplo publicado n=203.
    """
    G = nx.Graph()
    G.add_node(0)
    nxt = 1
    for _ in range(h):  # hojas del hub (la estrella S_{h+1})
        G.add_edge(0, nxt)
        nxt += 1
    for t in (t1, t2):  # cada cola: camino colgado de un extremo al hub
        prev = 0
        for _ in range(t):
            G.add_edge(prev, nxt)
            prev = nxt
            nxt += 1
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


def g6(G: nx.Graph) -> str:
    return nx.to_graph6_bytes(G, header=False).decode("ascii").strip()


def main():
    ev = Evaluador("cal3")

    # --- barrido de la familia cometa-de-doble-cola alrededor de la region CE ---
    familia = {}
    for h in range(180, 201):          # hojas del hub
        for t1 in range(3, 11):        # cola larga
            for t2 in range(3, t1 + 1):  # cola corta (<= larga; evita duplicados de orden)
                G = cometa_doble_cola(h, t1, t2)
                familia[(h, t1, t2)] = g6(G)

    t0 = time.time()
    gaps = ev.evaluar(list(familia.values()))
    dt = time.time() - t0

    pos = [((h, t1, t2), gaps.get(s, float("-inf")))
           for (h, t1, t2), s in familia.items()
           if gaps.get(s, float("-inf")) > 1e-9]
    pos.sort(key=lambda x: -x[1])

    print(f"[reto CAL-3] familia cometa-doble-cola: {len(familia)} grafos evaluados "
          f"en {dt:.2f}s (backend={ev.backend_usado})")
    print(f"[reto CAL-3] CONTRAEJEMPLOS en la familia: {len(pos)} "
          f"(mapea la familia de refutaciones, no solo uno)")
    for (h, t1, t2), gp in pos[:12]:
        n = 1 + h + t1 + t2
        print(f"    h={h} colas=({t1},{t2}) n={n} gap={gp:+.7f}")

    # --- el contraejemplo PUBLICADO: hub 190 hojas + P7 + P5 (n=203) ---
    G203 = cometa_doble_cola(190, 7, 5)
    g203 = g6(G203)
    gap203 = ev.evaluar([g203]).get(g203, float("nan"))
    dist = dict(nx.all_pairs_shortest_path_length(G203))
    diam = max(d for row in dist.values() for d in row.values())
    print(f"\n[reto CAL-3] contraejemplo publicado dc(190,7,5): n={G203.number_of_nodes()}, "
          f"D={diam}, k=floor(2D/3)={2 * diam // 3}, gap={gap203:+.9f}  "
          f"(esperado ~ +0.000285)")

    # --- CERTIFICADO EXACTO (proof-grade) del n=203 ---
    try:
        from verify import certificar
        t0 = time.time()
        cert = certificar(g203, "cal3")
        tc = time.time() - t0
        print(f"[reto CAL-3] CERTIFICADO EXACTO: certificado={cert.get('certificado')} "
              f"metodo={cert.get('metodo')} margen={cert.get('margen')}  ({tc:.1f}s)")
        if cert.get("certificado"):
            print("[reto CAL-3] >>> RE-DESCUBIERTO y DEMOSTRADO: gap>0 EXACTO. "
                  "AMCS lo halla en ~16.5 min (unico algoritmo previo); aqui: familia "
                  "en segundos + prueba exacta.")
    except Exception as e:
        print(f"[reto CAL-3] certificado no disponible ({type(e).__name__}: {e}); "
              "instala sympy+mpmath o corre certificados/verify.py --g6 <g6> --conj cal3")


if __name__ == "__main__":
    main()

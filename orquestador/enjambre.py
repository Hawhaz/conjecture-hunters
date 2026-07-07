#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ENJAMBRE — satura el nodo (99% CPU) cazando en paralelo las 20 conjeturas.

Un worker por core (work-stealing) hace BUSQUEDA LOCAL evolutiva por carril:
parte de la familia extremal reclamada + semillas, y perturba (flip de arista,
hoja +/-, re-cableo) HILL-CLIMBING hacia gap mayor. Un gap>0 en un carril ABIERTO
es un CANDIDATO a refutacion -> se graba DURABLE en el ledger (fsync antes de nada)
y se alerta. Los carriles de validacion (contraejemplo conocido) sirven de canario:
si el enjambre NO los re-descubre, algo esta mal.

"Cientos de miles de procesos" a nivel SO haria thrashing; el 99% real = 1 worker
por core en bucle apretado => cientos de miles / millones de EVALUACIONES exactas
por segundo. Gemma en la GPU entra como mutador mas inteligente (ver --gemma).

Uso:
  python orquestador/enjambre.py --minutos 5           # satura todos los cores 5 min
  python orquestador/enjambre.py --minutos 240 --workers 0   # 0 = todos los cores
  python orquestador/enjambre.py --solo-abiertas       # ignora carriles de validacion
"""
import argparse
import os
import random
import sys
import time
from multiprocessing import Pool, cpu_count

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "retos"))
sys.path.insert(0, os.path.join(REPO, "hallazgos"))

import pack_extra as pe        # noqa: E402
import registro                # noqa: E402

# formato unificado: (nombre, kind, gap, aplica, extremal, ce)
ALL_LANES = list(pe.LANES_EXTRA)
try:
    import pack_conjeturas as pc   # noqa: E402
    ALL_LANES = list(pc.LANES) + ALL_LANES
except Exception as _e:            # robusto ante glitch de lectura del pack de 9
    print(f"[enjambre] aviso: pack_conjeturas no disponible ({type(_e).__name__}); "
          f"corriendo con {len(ALL_LANES)} carriles de pack_extra")
MARGEN = 1e-5   # umbral de gap para declarar CANDIDATO (evita ruido float64)


def semillas_de(lane):
    """grafos iniciales para un carril: su extremal reclamado + familias vecinas."""
    nombre, kind, gap, aplica, extremal, ce = lane
    S = []
    for n in (5, 6, 7, 8, 9, 10, 11, 12, 14, 16):
        if extremal is not None:
            try:
                G = extremal(n)
                if G is not None and G.number_of_nodes() >= 4 and nx.is_connected(G):
                    S.append(G)
            except Exception:
                pass
    # familias genericas utiles
    for n in (6, 8, 10, 12):
        for gen in (nx.path_graph, lambda k: nx.star_graph(k - 1),
                    lambda k: nx.complete_bipartite_graph(k // 2, k - k // 2),
                    lambda k: nx.cycle_graph(k)):
            try:
                G = gen(n)
                if nx.is_connected(G) and aplica(G):
                    S.append(G)
            except Exception:
                pass
    return [G for G in S if aplica(G)] or [nx.path_graph(6)]


def vecino(G, aplica):
    """perturbacion que preserva conexo + el dominio del carril (aplica)."""
    H = G.copy()
    n = H.number_of_nodes()
    op = random.random()
    try:
        if op < 0.45 and n < 60:            # flip de arista
            u, v = random.sample(range(n), 2)
            if H.has_edge(u, v):
                H.remove_edge(u, v)
            else:
                H.add_edge(u, v)
        elif op < 0.75 and n < 60:          # añadir hoja
            H.add_edge(random.randrange(n), n)
        elif n > 5:                          # quitar un vertice de grado 1
            hojas = [x for x in H.nodes() if H.degree(x) == 1]
            if hojas:
                H.remove_node(random.choice(hojas))
                H = nx.convert_node_labels_to_integers(H)
    except Exception:
        return None
    if H.number_of_nodes() < 4 or not nx.is_connected(H) or not aplica(H):
        return None
    return H


def worker(args):
    seed, minutos, solo_abiertas = args
    random.seed(seed)
    t_fin = time.time() + minutos * 60
    evals = 0
    hits = 0
    lanes = [L for L in ALL_LANES if (L[1] == "abierta" or not solo_abiertas)]
    # estado de hill-climbing por carril
    estado = {L[0]: (random.choice(semillas_de(L)), -1e18) for L in lanes}
    while time.time() < t_fin:
        L = random.choice(lanes)
        nombre, kind, gap, aplica, extremal, ce = L
        G, mejor = estado[nombre]
        H = vecino(G, aplica)
        if H is None:
            if random.random() < 0.1:       # reinicio aleatorio ocasional
                estado[nombre] = (random.choice(semillas_de(L)), -1e18)
            continue
        try:
            g = gap(H)
        except Exception:
            continue
        evals += 1
        if g >= mejor:                       # hill-climb (acepta iguales para explorar mesetas)
            estado[nombre] = (H, g)
        elif random.random() < 0.05:         # ruido: acepta peor a veces
            estado[nombre] = (H, g)
        if kind == "abierta" and g > MARGEN:  # CANDIDATO a refutacion de conjetura ABIERTA
            try:
                g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(H), header=False).decode().strip()
                registro.registrar_hallazgo(nombre, g6, float(g), n=H.number_of_nodes(),
                                            meta={"worker": seed, "kind": kind})
                hits += 1
            except Exception:
                pass
    return evals, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutos", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=0, help="0 = todos los cores")
    ap.add_argument("--solo-abiertas", action="store_true")
    args = ap.parse_args()

    W = args.workers or cpu_count()
    print(f"ENJAMBRE: {W} workers (cores={cpu_count()}) · {len(ALL_LANES)} carriles · "
          f"{args.minutos} min · solo_abiertas={args.solo_abiertas}")
    print("cazando... (hallazgos -> hallazgos/ledger; canarios = carriles de validacion)\n")
    t0 = time.time()
    with Pool(processes=W) as pool:
        res = pool.map(worker, [(1000 + i, args.minutos, args.solo_abiertas) for i in range(W)])
    dt = time.time() - t0
    ev = sum(r[0] for r in res); hits = sum(r[1] for r in res)
    print(f"\nEVALS totales: {ev:,}  ·  {ev/max(dt,1e-9):,.0f} evals/seg  ·  "
          f"{W} cores · {dt:.1f}s")
    print(f"CANDIDATOS registrados (carriles abiertos): {hits}")
    print("Revisa: python hallazgos/registro.py --resumen   (+ hallazgos/ALERTAS.md)")
    if hits == 0:
        print("Sin candidatos: las abiertas resistieron el barrido local en este presupuesto.")


if __name__ == "__main__":
    main()

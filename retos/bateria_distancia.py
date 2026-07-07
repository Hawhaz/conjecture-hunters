#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bateria de conjeturas DISTANCIA-ESPECTRALES: barre formas (pi/rho + d_k > 0)
sobre familias extremales y flaggea VIOLACIONES candidatas (posibles
contraejemplos a conjeturas AGX/Aouchiche-Hansen).

Objetivo REAL del proyecto: refutar/mejorar una conjetura. Ya refutamos
pi + d_{floor(2D/3)} > 0 (cometa de doble cola n=203). Aqui probamos sus
HERMANAS (rho + d_{floor(2D/3)}, y otros indices/metricas) por si alguna sigue
abierta y la familia la viola -> candidata a refutacion NUEVA.

Convencion: d_i = i-esimo MAYOR eigenvalor de la matriz de distancias (desc).
Una conjetura de la forma "metrica + d_k > 0" se VIOLA si la suma es <= -tol.
Sanity: pi+d_3 y rho+d_3 (D>=3) estan PROBADAS (no deben violarse);
pi+d_{floor(2D/3)} SI se viola (nuestro resultado conocido).

NO afirma refutacion sin (a) confirmar en literatura que la forma es una
conjetura ABIERTA y (b) certificado exacto. Solo mapea DONDE hay violaciones.

Uso:  python retos/bateria_distancia.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import networkx as nx
import numpy as np


# ---------------------------------------------------- familias extremales
def cometa_doble_cola(h, t1, t2):
    G = nx.Graph()
    G.add_node(0)
    nxt = 1
    for _ in range(h):
        G.add_edge(0, nxt); nxt += 1
    for t in (t1, t2):
        prev = 0
        for _ in range(t):
            G.add_edge(prev, nxt); prev = nxt; nxt += 1
    return G


def broom(h, t):  # estrella h hojas + una cola de largo t
    return cometa_doble_cola(h, t, 0)


def cometa_triple(h, t1, t2, t3):
    G = cometa_doble_cola(h, t1, t2)
    prev = 0
    nxt = max(G.nodes()) + 1
    for _ in range(t3):
        G.add_edge(prev, nxt); prev = nxt; nxt += 1
    return G


def invariantes(G):
    n = G.number_of_nodes()
    nodos = sorted(G.nodes())
    idx = {v: i for i, v in enumerate(nodos)}
    D = np.zeros((n, n))
    diam = 0
    trans = np.zeros(n)
    for s in nodos:
        for t, d in nx.single_source_shortest_path_length(G, s).items():
            D[idx[s], idx[t]] = d
            if d > diam:
                diam = d
        trans[idx[s]] = D[idx[s]].sum()
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]  # ∂_1 >= ∂_2 >= ...
    pi = trans.min() / (n - 1)
    rho = trans.max() / (n - 1)
    return {"n": n, "D": int(diam), "pi": pi, "rho": rho, "ev": ev}


def d_k(ev, k):
    """∂_k (1-based, desc). k<=0 o k>n -> None."""
    if k <= 0 or k > len(ev):
        return None
    return ev[k - 1]


# ---------------------------------------------------- formas conjetura
def indices(D):
    return {
        "3": 3,
        "floor(D/2)": D // 2,
        "floor(2D/3)": (2 * D) // 3,
        "floor(3D/4)": (3 * D) // 4,
        "floor(D/3)": D // 3,
    }


TOL = 1e-6


def main():
    familia = {}
    # cometas de doble cola: barrido amplio de hub y colas
    for h in range(20, 201, 5):
        for t1 in range(2, 12):
            for t2 in range(0, t1 + 1):
                familia[("dc", h, t1, t2)] = cometa_doble_cola(h, t1, t2)
    # cometas triples (tres colas)
    for h in range(30, 160, 10):
        for t in range(2, 8):
            familia[("tc", h, t, t, t)] = cometa_triple(h, t, t, t)

    print(f"[bateria] {len(familia)} grafos de familias extremales")

    # acumula violaciones por forma
    viol = {}  # forma -> lista de (peor_sum, clave, n, D, k)
    for clave, G in familia.items():
        inv = invariantes(G)
        if inv["n"] < 4 or inv["D"] < 2:
            continue
        ks = indices(inv["D"])
        for metrica in ("pi", "rho"):
            for kname, k in ks.items():
                dk = d_k(inv["ev"], k)
                if dk is None:
                    continue
                s = inv[metrica] + dk  # forma "metrica + ∂_k > 0"
                if s <= -TOL:  # VIOLACION de ">0"
                    forma = f"{metrica} + d_{kname}"
                    viol.setdefault(forma, []).append((s, clave, inv["n"], inv["D"], k))

    print("\n[bateria] VIOLACIONES por forma conjetura (metrica + d_k > 0):")
    print(f"{'forma':22} {'#viol':>6}  peor (sum, n, D, k, familia)")
    for forma in sorted(viol, key=lambda f: min(v[0] for v in viol[f])):
        vs = sorted(viol[forma], key=lambda x: x[0])
        peor = vs[0]
        print(f"{forma:22} {len(vs):>6}  sum={peor[0]:+.6f} n={peor[2]} D={peor[3]} "
              f"k={peor[4]} fam={peor[1]}")

    print("\n[bateria] SANITY:")
    for forma in ("pi + d_3", "rho + d_3"):
        nv = len(viol.get(forma, []))
        print(f"  {forma}: {nv} violaciones "
              f"({'ESPERADO 0 si D>=3 (PROBADA)' if nv == 0 else 'REVISAR: prob. D<3 o indexado'})")
    for forma in ("pi + d_floor(2D/3)",):
        nv = len(viol.get(forma, []))
        print(f"  {forma}: {nv} violaciones (ESPERADO >0: refutada por AMCS/nosotros = sanity OK)")

    print("\n[bateria] CANDIDATAS a conjetura ABIERTA violada (confirmar status en "
          "literatura + certificar exacto antes de afirmar refutacion):")
    conocidas = {"pi + d_floor(2D/3)"}  # ya refutada (no es nueva)
    for forma in sorted(viol, key=lambda f: min(v[0] for v in viol[f])):
        if forma in conocidas or forma in ("pi + d_3", "rho + d_3"):
            continue
        vs = sorted(viol[forma], key=lambda x: x[0])
        print(f"  >>> {forma}: {len(vs)} violaciones; peor sum={vs[0][0]:+.6f} "
              f"(n={vs[0][2]}, D={vs[0][3]}, k={vs[0][4]}, {vs[0][1]})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caza sistemática: minimizante/maximizante VERDADERO de cada cota
distancia-espectral AGX sobre el atlas EXHAUSTIVO de grafos conexos n<=7, con
aritmética exacta en el extremal.

Idea (así cayó Jia-Song): una conjetura AGX afirma "métrica + ∂_i >= cota, con
igualdad en [grafo reclamado]". Si el minimizante VERDADERO (calculado exhaustiva
y exactamente para n pequeño) NO es el grafo reclamado, la conjetura es falsa (si
está abierta) o mejorable. Aquí tabulamos el extremal verdadero de cada forma; el
catálogo (agente) dice qué se reclamaba y su estado -> se cruzan.

Estrategia de cómputo: numpy para RANKEAR (rápido) sobre las 994 conexas del
atlas, y sympy EXACTO solo sobre el ganador de cada (forma, n).

Uso:  python retos/bateria_extremal.py
"""
import networkx as nx
import numpy as np
import sympy as sp
from networkx.generators.atlas import graph_atlas_g

x = sp.Symbol("x")


def invs_num(G):
    n = G.number_of_nodes()
    D = nx.floyd_warshall_numpy(G)
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]
    trans = D.sum(axis=1)
    return n, int(D.max()), float(trans.min()) / (n - 1), float(trans.max()) / (n - 1), ev


def dk_num(ev, k):
    if k < 1 or k > len(ev):
        return None
    return float(ev[k - 1])


def exact_val(G, metrica, kfun):
    """Valor exacto (sympy) de 'metrica + ∂_k' (o d1-metrica si metrica negativa)."""
    n = G.number_of_nodes()
    Dnum = np.array(nx.floyd_warshall_numpy(G), dtype=int)
    trans = [int(Dnum[i].sum()) for i in range(n)]
    pi = sp.Rational(min(trans), n - 1)
    rho = sp.Rational(max(trans), n - 1)
    diam = int(Dnum.max())
    roots = sp.real_roots(sp.Matrix(Dnum.tolist()).charpoly(x))  # asc, con mult
    def d(k):
        return roots[-k]  # k-esimo MAYOR
    k = kfun(diam)
    if k < 1 or k > n:
        return None
    if metrica == "pi":
        return sp.nsimplify(pi + d(k))
    if metrica == "rho":
        return sp.nsimplify(rho + d(k))
    if metrica == "d1-pi":
        return sp.nsimplify(d(1) - pi)
    if metrica == "d1-rho":
        return sp.nsimplify(d(1) - rho)
    return None


def desc(G):
    n = G.number_of_nodes()
    degs = sorted(d for _, d in G.degree())
    D = nx.diameter(G)
    g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(G, ordering="sorted"),
                            header=False).decode().strip()
    # heuristica de identificacion
    full = n * (n - 1) // 2
    m = G.number_of_edges()
    ident = "?"
    if m == full:
        ident = "K_n"
    elif m == full - 1:
        ident = "K_n - e"
    elif degs == [1] * (n - 1) + [n - 1]:
        ident = "estrella K_{1,n-1}"
    elif degs == [1, 1] + [2] * (n - 2):
        ident = "camino P_n"
    elif max(degs) == n - 1:
        ident = "tiene vertice universal (join)"
    return f"deg={degs} m={m} D={D} [{ident}] g6={g6}"


# formas: (nombre, metrica, k(diam), direccion)  direccion: 'min' cota inferior >=
FORMAS = [
    ("rho + d_2",         "rho",   lambda D: 2,          "min"),
    ("pi  + d_2",         "pi",    lambda D: 2,          "min"),
    ("rho + d_3",         "rho",   lambda D: 3,          "min"),
    ("pi  + d_3",         "pi",    lambda D: 3,          "min"),
    ("rho + d_floor(D/2)", "rho",  lambda D: D // 2,     "min"),
    ("pi  + d_floor(D/2)", "pi",   lambda D: D // 2,     "min"),
    ("rho + d_floor(2D/3)", "rho", lambda D: (2 * D) // 3, "min"),
    ("pi  + d_floor(2D/3)", "pi",  lambda D: (2 * D) // 3, "min"),
    ("d_1 - rho",         "d1-rho", lambda D: 1,         "min"),
    ("d_1 - pi",          "d1-pi",  lambda D: 1,         "min"),
]


def main():
    atlas = [G for G in graph_atlas_g()
             if G.number_of_nodes() >= 4 and nx.is_connected(G)]
    por_n = {n: [G for G in atlas if G.number_of_nodes() == n] for n in (4, 5, 6, 7)}

    print("Extremal VERDADERO de cada cota distancia-espectral (atlas exhaustivo n<=7,")
    print("excluyendo K_n y K_n-e; valor exacto en el minimizante). Cruzar con el catalogo.\n")

    for nombre, metrica, kfun, direccion in FORMAS:
        print(f"=== {nombre}  (cota inferior; buscar minimizante verdadero) ===")
        for n in (4, 5, 6, 7):
            full = n * (n - 1) // 2
            allowed = [G for G in por_n[n] if G.number_of_edges() < full - 1]  # sin K_n, K_n-e
            cand = []
            for G in allowed:
                ninv, D, pi, rho, ev = invs_num(G)
                if metrica == "pi":
                    v = None if kfun(D) < 1 else (pi + dk_num(ev, kfun(D)) if dk_num(ev, kfun(D)) is not None else None)
                elif metrica == "rho":
                    v = None if kfun(D) < 1 else (rho + dk_num(ev, kfun(D)) if dk_num(ev, kfun(D)) is not None else None)
                elif metrica == "d1-rho":
                    v = dk_num(ev, 1) - rho
                elif metrica == "d1-pi":
                    v = dk_num(ev, 1) - pi
                else:
                    v = None
                if v is not None and np.isfinite(v):
                    cand.append((v, G))
            if not cand:
                print(f"   n={n}: (sin candidatos con ese indice)")
                continue
            vmin, Gmin = min(cand, key=lambda t: t[0])
            ex = exact_val(Gmin, metrica, kfun)
            print(f"   n={n}: min = {float(ex):.6f} = {ex}")
            print(f"          en {desc(Gmin)}")
        print()


if __name__ == "__main__":
    main()

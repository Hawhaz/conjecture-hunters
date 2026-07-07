#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batería EXACTA de extremales para el Laplaciano de distancias (D^L = Tr - D) y
el Laplaciano signless de distancias (D^Q = Tr + D) — el frente nuevo tras Jia-Song.

Misma estrategia que tumbó a Jia-Song (`retos/bateria_extremal.py`): para cada
"forma" métrica+autovalor, calcular el EXTREMAL VERDADERO exhaustivamente y exacto
sobre el atlas de conexas n<=7, y ADEMÁS barrer las familias densas / join
balanceado K1∨(Ka∪Kb) donde cayó Jia-Song, a n mayores. Cuando el catálogo
(agente) diga qué bound con qué extremal se reclama para ρ/π + ∂_i^{L/Q}, se cruza:
si nuestro extremal verdadero difiere del reclamado y la conjetura está abierta,
es candidato a refutación (o mejora).

Notas espectrales:
  * D^L = Tr - D es PSD; ∂_n^L = 0 SIEMPRE (vector all-ones), ∂_1^L = radio
    Laplaciano de distancias. El índice REFUTABLE (2do mayor no trivial) es ∂_2^L.
  * D^Q = Tr + D. ∂_1^Q = radio signless. Índice refutable análogo: ∂_2^Q.
  * Jia-Song 2018 PROBÓ (no conjeturó) cotas de ρ+∂_1^L, ∂_1^L-ρ, 2ρ+∂_1^Q,
    ∂_1^Q-2ρ. Aquí incluimos esas formas al índice 1 para SANITY (reproducir su
    extremal) y al índice 2 para CAZAR.

Uso:  python retos/bateria_laplaciana.py            # atlas exhaustivo n<=7
      python retos/bateria_laplaciana.py --familias # + barrido de familias n<=41
"""
import argparse
import networkx as nx
import numpy as np
import sympy as sp
from networkx.generators.atlas import graph_atlas_g

x = sp.Symbol("x")


# ----------------------------------------------------------------- matrices
def matrices_num(G):
    n = G.number_of_nodes()
    D = nx.floyd_warshall_numpy(G)
    Tr = np.diag(D.sum(axis=1))
    DL = Tr - D
    DQ = Tr + D
    return n, D, DL, DQ


def specs_num(M):
    return np.sort(np.linalg.eigvalsh(M))[::-1]  # descendente


def rho_pi(G):
    n = G.number_of_nodes()
    trans = nx.floyd_warshall_numpy(G).sum(axis=1)
    return float(trans.max()) / (n - 1), float(trans.min()) / (n - 1)


def dk(ev, k):
    return float(ev[k - 1]) if 1 <= k <= len(ev) else None


# ----------------------------------------------------------------- exacto
def exacto(G, matriz, metrica, k, comb):
    """Valor EXACTO de la forma (metrica, ∂_k^{matriz}) via charpoly entero."""
    n = G.number_of_nodes()
    Dn = np.array(nx.floyd_warshall_numpy(G), dtype=int)
    trans = [int(Dn[i].sum()) for i in range(n)]
    if matriz == "L":
        M = sp.diag(*trans) - sp.Matrix(Dn.tolist())
    elif matriz == "Q":
        M = sp.diag(*trans) + sp.Matrix(Dn.tolist())
    else:
        M = sp.Matrix(Dn.tolist())
    roots = sp.real_roots(M.charpoly(x))          # ascendente, con mult.
    dkv = roots[-k]                               # k-ésimo MAYOR
    rho = sp.Rational(max(trans), n - 1)
    pi = sp.Rational(min(trans), n - 1)
    met = {"rho": rho, "pi": pi, "2rho": 2 * rho}[metrica]
    if comb == "+":
        return sp.nsimplify(met + dkv)
    if comb == "-met":   # ∂_k - metrica
        return sp.nsimplify(dkv - met)
    return None


def ident(G):
    n = G.number_of_nodes()
    degs = sorted(d for _, d in G.degree())
    m = G.number_of_edges()
    full = n * (n - 1) // 2
    tag = "?"
    if m == full:
        tag = "K_n"
    elif m == full - 1:
        tag = "K_n-e"
    elif max(degs) == n - 1 and m == full - 2:
        tag = "K_n-2e?"
    elif degs == [1] * (n - 1) + [n - 1]:
        tag = "estrella"
    elif max(degs) == n - 1:
        tag = "join (vértice universal)"
    g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(G, ordering="sorted"),
                            header=False).decode().strip()
    return f"deg={degs} m={m} [{tag}] g6={g6}"


# formas: (nombre, matriz, metrica, k, comb, dirección)
FORMAS = [
    # SANITY (Jia-Song PROBÓ estas al índice 1): extremal conocido -> validan el código
    ("rho + d1^L",  "L", "rho",  1, "+",    "min"),
    ("d1^L - rho",  "L", "rho",  1, "-met", "min"),
    ("2rho + d1^Q", "Q", "2rho", 1, "+",    "min"),
    ("d1^Q - 2rho", "Q", "2rho", 1, "-met", "min"),
    # CAZA (segundo mayor — el patrón refutable, análogo a rho+d2 de Jia-Song)
    ("rho + d2^L",  "L", "rho",  2, "+",    "min"),
    ("pi  + d2^L",  "L", "pi",   2, "+",    "min"),
    ("rho + d2^Q",  "Q", "rho",  2, "+",    "min"),
    ("pi  + d2^Q",  "Q", "pi",   2, "+",    "min"),
    ("d2^L - rho",  "L", "rho",  2, "-met", "min"),
    ("d2^Q - 2rho", "Q", "2rho", 2, "-met", "min"),
]

MATRIZ_DE = {"L": lambda n, D, DL, DQ: DL, "Q": lambda n, D, DL, DQ: DQ,
             "": lambda n, D, DL, DQ: D}


def valor_num(G, forma):
    _, matriz, metrica, k, comb, _ = forma
    n, D, DL, DQ = matrices_num(G)
    ev = specs_num(MATRIZ_DE[matriz](n, D, DL, DQ))
    dkv = dk(ev, k)
    if dkv is None:
        return None
    rho, pi = rho_pi(G)
    met = {"rho": rho, "pi": pi, "2rho": 2 * rho}[metrica]
    return (met + dkv) if comb == "+" else (dkv - met)


def atlas_exhaustivo():
    atlas = [G for G in graph_atlas_g()
             if G.number_of_nodes() >= 4 and nx.is_connected(G)]
    por_n = {n: [G for G in atlas if G.number_of_nodes() == n] for n in (4, 5, 6, 7)}
    print("EXTREMAL VERDADERO (min) de cada forma Laplaciana de distancias — atlas")
    print("exhaustivo n<=7, excluyendo K_n y K_n-e. Valor exacto en el minimizante.\n")
    for forma in FORMAS:
        nombre = forma[0]
        print(f"=== {nombre} ===")
        for n in (4, 5, 6, 7):
            full = n * (n - 1) // 2
            allowed = [G for G in por_n[n] if G.number_of_edges() < full - 1]
            cand = []
            for G in allowed:
                v = valor_num(G, forma)
                if v is not None and np.isfinite(v):
                    cand.append((v, G))
            if not cand:
                print(f"   n={n}: (sin candidatos)")
                continue
            vmin, Gmin = min(cand, key=lambda t: t[0])
            ex = exacto(Gmin, forma[1], forma[2], forma[3], forma[4])
            print(f"   n={n}: min = {float(ex):.6f} = {ex}")
            print(f"          en {ident(Gmin)}")
        print()


# ------------------- familias donde cayó Jia-Song (join balanceado + densas)
def join_dos_cliques(a, b):
    G = nx.Graph()
    A = list(range(1, 1 + a)); B = list(range(1 + a, 1 + a + b))
    for C in (A, B):
        for i in range(len(C)):
            for j in range(i + 1, len(C)):
                G.add_edge(C[i], C[j])
    for v in A + B:
        G.add_edge(0, v)
    if a == 0 and b == 0:
        G.add_node(0)
    return G


def barrer_familias(nmax=41):
    print("BARRIDO de familias (join balanceado K1∨(Ka∪Kb) y sus vecinas) — busca")
    print("la forma más NEGATIVA por n (candidata a violar una cota inferior).\n")
    for forma in FORMAS:
        nombre = forma[0]
        peor = (1e18, None)
        for n in range(5, nmax + 1, 2):        # n impar: a=b balanceado
            r = (n - 1) // 2
            for (a, b) in {(r, r), (r - 1, r + 1), (1, n - 2), (r, r)}:
                if a < 1 or b < 1:
                    continue
                G = join_dos_cliques(a, b)
                if G.number_of_nodes() != n or not nx.is_connected(G):
                    continue
                v = valor_num(G, forma)
                if v is not None and v < peor[0]:
                    peor = (v, (a, b, n))
        print(f"   {nombre:14}  min≈{peor[0]:+.6f}  en (a,b,n)={peor[1]}")
    print("\n(Cuando el catálogo dé la cota+extremal reclamados, se cruza: extremal")
    print(" verdadero distinto del reclamado + estado abierto -> candidato.)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--familias", action="store_true", help="barre familias n<=41")
    args = ap.parse_args()
    atlas_exhaustivo()
    if args.familias:
        barrer_familias()


if __name__ == "__main__":
    main()

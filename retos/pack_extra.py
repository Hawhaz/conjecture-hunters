#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PACK EXTRA — 11 carriles nuevos (5 validacion + 6 abiertas), autocontenido y
BLINDADO con gate anti-basura. Junto con los 9 de pack_conjeturas.py => 20 carriles.

Cada carril: gap(G) > 0  <=>  contraejemplo. Validacion => debe re-descubrir su
contraejemplo CONOCIDO (con su g6/construccion exacta); abierta => debe sostenerse
en el corpus y ser ajustada en su extremal. Specs y fuentes en
retos/ESPECIFICACIONES_CARRILES.md.

Uso:
  python retos/pack_extra.py            # gate + bateria
  python retos/pack_extra.py --gate     # solo el gate
  pytest retos/test_pack_extra.py
"""
import argparse
import math
from functools import partial
from multiprocessing import Pool

import networkx as nx
import numpy as np
from networkx.generators.atlas import graph_atlas_g

TOL = 1e-7


# -------------------------------------------------- invariantes
def adj_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.to_numpy_array(G)))[::-1]

def dist_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.floyd_warshall_numpy(G)))[::-1]

def lap_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.laplacian_matrix(G).toarray().astype(float)))[::-1]

def transmissions(G):
    return nx.floyd_warshall_numpy(G).sum(axis=1)

def remoteness(G):
    n = G.number_of_nodes(); return float(transmissions(G).max()) / (n - 1)

def proximity(G):
    n = G.number_of_nodes(); return float(transmissions(G).min()) / (n - 1)

def omega(G):
    return max((len(c) for c in nx.find_cliques(G)), default=1)

def alpha(G):
    return max((len(c) for c in nx.find_cliques(nx.complement(G))), default=1)

def randic(G):
    d = dict(G.degree())
    return float(sum(1.0 / math.sqrt(d[u] * d[v]) for u, v in G.edges()))

def matching_number(G):
    return len(nx.max_weight_matching(G, maxcardinality=True))

def energy_adj(G):
    return float(np.abs(adj_eigs(G)).sum())

def dist_energy(G):
    return float(np.abs(dist_eigs(G)).sum())

def lap_energy(G):
    n = G.number_of_nodes(); m = G.number_of_edges()
    return float(np.abs(lap_eigs(G) - 2 * m / n).sum())

def Sk_dist(G, k):
    ev = dist_eigs(G); return float(ev[:k].sum())

def es_completo(G):
    n = G.number_of_nodes(); return G.number_of_edges() == n * (n - 1) // 2


# -------------------------------------------------- grafos nombrados
def broom2(b1, b2):
    """conector c unido a dos centros u,w; u con b1 hojas, w con b2 hojas.
    n = 3 + b1 + b2. (Familia T(2,b) de Wagner/AMCS.)"""
    G = nx.Graph(); G.add_edge(0, 1); G.add_edge(0, 2)  # c-u, c-w
    k = 3
    for _ in range(b1):
        G.add_edge(1, k); k += 1
    for _ in range(b2):
        G.add_edge(2, k); k += 1
    return G

def k5_p7():
    """K5 con un P7 colgado de un vertice. n = 12. (CE de lambda1*pi.)"""
    G = nx.complete_graph(5); prev = 0; k = 5
    for _ in range(7):
        G.add_edge(prev, k); prev = k; k += 1
    return G

def line_k5():
    """grafo linea de K5 (triangular T(5)). n=10, 4-regular. (CE de Gutman.)"""
    return nx.convert_node_labels_to_integers(nx.line_graph(nx.complete_graph(5)))

def pineapple(n):
    c = max(2, min(1 + (2 * n) // 3, n))
    G = nx.complete_graph(c)
    for v in range(c, n):
        G.add_edge(0, v)
    return G

def double_comet(k, ell):
    """C(k,ell): camino P_ell con k hojas en CADA extremo. n = ell + 2k."""
    G = nx.path_graph(ell); nxt = ell
    for _ in range(k):
        G.add_edge(0, nxt); nxt += 1
    for _ in range(k):
        G.add_edge(ell - 1, nxt); nxt += 1
    return G

def min_comet_table(n):
    """minimizante-arbol conjeturado del gap espectral (verif. n<=20)."""
    if n <= 3:
        return None
    if n <= 8:
        return nx.path_graph(n)               # C(1,n-2)=P_n
    if n <= 11:
        return double_comet(2, n - 4)
    if n <= 15:
        return double_comet(3, n - 6)
    if n <= 20:
        return double_comet(4, n - 8)
    return None


# -------------------------------------------------- carriles (gap>0 = CE)
def gap_lambda1_pi(G):                 # lambda1*pi <= n-1     (val: K5+P7)
    n = G.number_of_nodes()
    return adj_eigs(G)[0] * proximity(G) - (n - 1)

def gap_lambda1_alpha(G):              # lambda1 - alpha >= sqrt(n-1)-n+1  (val: broom2(7,8))
    n = G.number_of_nodes()
    rhs = math.sqrt(n - 1) - n + 1
    return rhs - (adj_eigs(G)[0] - alpha(G))

def gap_randic_alpha(G):               # R + alpha <= n-1+sqrt(n-1)  (val: broom2(4,4)=T(2,5))
    n = G.number_of_nodes()
    return (randic(G) + alpha(G)) - (n - 1 + math.sqrt(n - 1))

def gap_cal1_lambda_mu(G):             # lambda1 + mu >= sqrt(n-1)+1  (val: broom2(8,8)=Wagner n19)
    n = G.number_of_nodes()
    return (math.sqrt(n - 1) + 1) - (adj_eigs(G)[0] + matching_number(G))

def gap_gutman_energy(G):              # E <= 2n-2            (val: L(K5))
    n = G.number_of_nodes()
    return energy_adj(G) - (2 * n - 2)

def gap_lin_p2(G):                     # S2(D) <= S2(D(Pn))   (abierta; extremal Pn)
    n = G.number_of_nodes()
    return Sk_dist(G, 2) - Sk_dist(nx.path_graph(n), 2)

def gap_lin_p3(G):                     # S2(D) >= 2n-4 bipartito (abierta; extremal K_{r,n-r})
    n = G.number_of_nodes()
    return (2 * n - 4) - Sk_dist(G, 2)

def gap_dist_energy_lb(G):             # E_D >= 4(n-1-m/n)    (abierta)
    n = G.number_of_nodes(); m = G.number_of_edges()
    return 4 * (n - 1 - m / n) - dist_energy(G)

def gap_pineapple_le(G):               # LE <= LE(pineapple)  (abierta; extremal pineapple)
    n = G.number_of_nodes()
    return lap_energy(G) - lap_energy(pineapple(n))

def gap_tree_spectral(G):              # lambda1-lambda2 min por double comet (abierta; arboles)
    n = G.number_of_nodes()
    T = min_comet_table(n)
    if T is None:
        return -9.0
    ev = adj_eigs(G); evT = adj_eigs(T)
    gapT = evT[0] - evT[1]
    gapG = ev[0] - ev[1]
    return gapT - gapG                 # >0 si G (arbol) tiene gap MENOR que el minimizante

def gap_elw_correct(G):                # sum_{i<=min(n+,w)} l_i^2 <= 2(1-1/w)m (abierta)
    m = G.number_of_edges(); ev = adj_eigs(G); w = omega(G)
    ell = min(int((ev > 1e-9).sum()), w)
    return float((ev[:ell] ** 2).sum()) - 2 * (1 - 1 / w) * m


# nombre, kind, gap, aplica, extremal(n)->G|None, ce()->G|None
LANES_EXTRA = [
    ("lam1*pi<=n-1",        "validacion", gap_lambda1_pi,     lambda G: True,               None, k5_p7),
    ("lam1-alpha>=..",      "validacion", gap_lambda1_alpha,  lambda G: True,               None, lambda: broom2(7, 8)),
    ("R+alpha<=..",         "validacion", gap_randic_alpha,   lambda G: True,               None, lambda: broom2(4, 4)),
    ("lam1+mu>=sqrt(n-1)+1","validacion", gap_cal1_lambda_mu, lambda G: True,               None, lambda: broom2(8, 8)),
    ("E<=2n-2 (Gutman)",    "validacion", gap_gutman_energy,  lambda G: True,               None, line_k5),
    ("S2(D)<=S2(Pn)",       "abierta",    gap_lin_p2,         lambda G: True,               nx.path_graph,                 None),
    ("S2(D)>=2n-4 bip",     "abierta",    gap_lin_p3,         lambda G: nx.is_bipartite(G), lambda n: nx.complete_bipartite_graph(n // 2, n - n // 2), None),
    ("E_D>=4(n-1-m/n)",     "abierta",    gap_dist_energy_lb, lambda G: True,               None,                          None),
    ("LE<=LE(pineapple)",   "abierta",    gap_pineapple_le,   lambda G: True,               pineapple,                     None),
    ("l1-l2 min dcomet",    "abierta",    gap_tree_spectral,  lambda G: nx.is_tree(G),      min_comet_table,               None),
    ("ELW min(n+,w)",       "abierta",    gap_elw_correct,    lambda G: not es_completo(G), None,                          None),
]


# -------------------------------------------------- corpus de control
def corpus_control():
    C = []
    for G in graph_atlas_g():
        if G.number_of_nodes() >= 4 and nx.is_connected(G):
            C.append(nx.convert_node_labels_to_integers(G))
    for a in range(2, 9):
        C.append(nx.complete_bipartite_graph(a, a))
        C.append(nx.complete_bipartite_graph(a, a + 1))
    for n in range(4, 18):
        C.append(nx.path_graph(n))
        C.append(nx.star_graph(n - 1))
    for (k, ell) in [(2, 5), (3, 6), (4, 8), (2, 7), (3, 9)]:
        C.append(double_comet(k, ell))
    for (b1, b2) in [(3, 3), (4, 4), (5, 6), (7, 8), (8, 8)]:
        C.append(broom2(b1, b2))
    for r in range(2, 8):
        C.append(nx.complete_multipartite_graph(r, r))
    for k in (5, 6, 7, 9):
        C.append(nx.cycle_graph(k))
    return C


# -------------------------------------------------- GATE
def verificar(verbose=True):
    C = corpus_control()
    problemas = []
    for nombre, kind, gap, aplica, extremal, ce in LANES_EXTRA:
        if kind == "validacion":
            g = gap(ce())
            ok = g > TOL
            if verbose:
                print(f"  [val ] {nombre:22} re-descubre CE: gap={g:+.5f}  {'OK' if ok else 'FALLA'}")
            if not ok:
                problemas.append(f"{nombre}: NO re-descubre su contraejemplo (gap={g:+.5f})")
        else:
            peor = (-1e18, None)
            for G in C:
                if not aplica(G):
                    continue
                g = gap(G)
                if g > peor[0]:
                    peor = (g, G)
            gmax, Gw = peor
            ok = gmax <= 1e-6
            extra = ""
            if extremal is not None:
                for nn in (5, 6, 7, 8, 10, 12):
                    Ge = extremal(nn)
                    if Ge is not None and Ge.number_of_nodes() >= 4 and nx.is_connected(Ge) and aplica(Ge):
                        ge = gap(Ge)
                        extra = f" · extremal n={nn}: gap={ge:+.5f}"
                        if ge > 1e-6:
                            problemas.append(f"{nombre}: extremal n={nn} viola (gap={ge:+.5f})")
                        break
            if verbose:
                nn = Gw.number_of_nodes() if Gw is not None else 0
                print(f"  [open] {nombre:22} se sostiene: gap_max={gmax:+.5f} (n={nn}) {'OK' if ok else 'VIOLA'}{extra}")
            if not ok:
                problemas.append(f"{nombre}: FALSO POSITIVO en corpus (gap={gmax:+.5f}) -> revisar codificacion")
    if problemas:
        raise AssertionError("GATE EXTRA FALLO:\n  - " + "\n  - ".join(problemas))
    if verbose:
        v = sum(1 for L in LANES_EXTRA if L[1] == "validacion")
        a = sum(1 for L in LANES_EXTRA if L[1] == "abierta")
        print(f"\n  GATE EXTRA VERDE: {v} validacion + {a} abiertas. Cero basura.")
    return True


def _corre(i, grafos):
    nombre, kind, gap, aplica, extremal, ce = LANES_EXTRA[i]
    peor = (-1e18, None); nviol = 0
    for G in grafos:
        if not aplica(G):
            continue
        try:
            g = gap(G)
        except Exception:
            continue
        if g > peor[0]:
            peor = (g, G)
        if g > TOL:
            nviol += 1
    gmax, Gw = peor
    g6 = nx.to_graph6_bytes(Gw, header=False).decode().strip() if Gw is not None else ""
    nn = Gw.number_of_nodes() if Gw is not None else 0
    return nombre, kind, nviol, gmax, nn, g6


def bateria():
    grafos = corpus_control()
    print(f"\nBATERIA EXTRA · {len(LANES_EXTRA)} carriles · {len(grafos)} grafos\n")
    with Pool(processes=min(len(LANES_EXTRA), 8)) as pool:
        res = pool.map(partial(_corre, grafos=grafos), range(len(LANES_EXTRA)))
    print(f"{'carril':24}{'tipo':12}{'#viol':>6}{'gap_max':>11}  extremal")
    print("-" * 74)
    for nombre, kind, nviol, gmax, nn, g6 in res:
        print(f"{nombre:24}{kind:12}{nviol:>6}{gmax:>11.5f}  n={nn} {g6}{'  ->CE' if nviol else ''}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()
    print("GATE ANTI-BASURA (pack extra):")
    verificar()
    if not args.gate:
        bateria()


if __name__ == "__main__":
    main()

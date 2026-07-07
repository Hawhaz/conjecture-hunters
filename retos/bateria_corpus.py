#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batería-corpus MULTI-CARRIL: corre VARIAS conjeturas EN PARALELO sobre un corpus
de grafos y reporta, por conjetura, si re-descubre su contraejemplo conocido o si
la abierta se sostiene. Es el MVP honesto de "30-40 conjeturas a full cómputo":

  - carriles con CONTRAEJEMPLO CONOCIDO  -> el motor debe RE-DESCUBRIRLO (demo de
    amplitud + velocidad; valida la tubería antes de confiar en las abiertas).
  - carriles ABIERTOS                    -> caza real; gap>0 = candidato a refutar.

Cada conjetura es una función gap(G): gap>0 significa VIOLACIÓN (contraejemplo).
Paralelo sobre carriles (multiprocessing) = el patrón que en MI300X escala a n grande
+ Gemma proponiendo grafos raros. Aquí, dry-run CPU para probar que el multi-carril
funciona y para fijar el estado esperado de cada carril.

Uso:  python retos/bateria_corpus.py
"""
import math
from functools import partial
from multiprocessing import Pool

import networkx as nx
import numpy as np
from networkx.generators.atlas import graph_atlas_g

TOL = 1e-7


# --------------------------------------------------------- invariantes base
def adj_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.to_numpy_array(G)))[::-1]  # desc


def dist_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.floyd_warshall_numpy(G)))[::-1]


def omega(G):
    return max((len(c) for c in nx.find_cliques(G)), default=1)   # clique number


def alpha(G):
    return max((len(c) for c in nx.find_cliques(nx.complement(G))), default=1)  # independence


def remoteness(G):
    n = G.number_of_nodes()
    return float(nx.floyd_warshall_numpy(G).sum(axis=1).max()) / (n - 1)


# --------------------------------------------------------- carriles (conjeturas)
# cada uno: gap(G) > 0  <=>  contraejemplo.  'estado': known-CE | abierta
def g_jia_song(G):                              # rho + d2 >= B(n)   (YA refutada, ns)
    n = G.number_of_nodes()
    B = n / (n - 1) + (n - 1 - math.sqrt((n - 1) ** 2 + 8)) / 2
    d2 = dist_eigs(G)[1]
    return B - (remoteness(G) + d2)             # >0 en K1v2Kr

def g_lin_p4(G):                                # d2 <= n/2 - 2       (abierta)
    n = G.number_of_nodes()
    return dist_eigs(G)[1] - (n / 2 - 2)

def g_bollobas_nikiforov(G):                    # l1^2+l2^2 <= 2(1-1/w)m  (abierta; EXCLUYE K_n)
    n = G.number_of_nodes(); m = G.number_of_edges()
    if m == n * (n - 1) // 2:                    # grafo completo = caso degenerado excluido
        return -9.0                              # (K_n da (n-1)^2+1 > (n-1)^2; NO es contraejemplo)
    ev = adj_eigs(G); w = omega(G)
    return (ev[0] ** 2 + ev[1] ** 2) - 2 * (1 - 1 / w) * m

def g_efgw(G):                                  # min(s+,s-) >= n-1   (abierta)
    n = G.number_of_nodes(); ev = adj_eigs(G)
    sp = float((ev[ev > 0] ** 2).sum()); sm = float((ev[ev < 0] ** 2).sum())
    return (n - 1) - min(sp, sm)

def g_graffiti_energy(G):                       # sum_{l>0} l >= n - alpha  (abierta)
    n = G.number_of_nodes(); ev = adj_eigs(G)
    return (n - alpha(G)) - float(ev[ev > 0].sum())

def g_powers3(G):                               # l3 <= floor(n/3)   (abierta; i=4 ya refutada)
    n = G.number_of_nodes(); ev = adj_eigs(G)
    return (ev[2] if len(ev) >= 3 else -9) - math.floor(n / 3)

def g_elphick_np(G):                            # sum_{i<=n+} l_i^2 <= 2(1-1/w)m  (variante ell=n+: FALSA, CE=C7)
    m = G.number_of_edges(); ev = adj_eigs(G); w = omega(G)
    npos = int((ev > 1e-9).sum())
    return float((ev[:npos] ** 2).sum()) - 2 * (1 - 1 / w) * m

CARRILES = [
    ("jia_song  rho+d2>=B(n)",        "known-CE (nuestra)", g_jia_song),
    ("elphick   sum_{n+} l^2<=..",    "known-CE (C7)",      g_elphick_np),
    ("powers    l3<=floor(n/3)",      "abierta (i=3)",      g_powers3),
    ("lin_p4    d2<=n/2-2",           "abierta",            g_lin_p4),
    ("bollobas  l1^2+l2^2<=..",       "abierta",            g_bollobas_nikiforov),
    ("efgw      min(s+,s-)>=n-1",     "abierta",            g_efgw),
    ("graffiti  E>=2(n-alpha)",       "abierta",            g_graffiti_energy),
]


# --------------------------------------------------------- corpus (compartido)
def join_2Kr(r):
    G = nx.Graph(); a = list(range(1, 1 + r)); b = list(range(1 + r, 1 + 2 * r))
    for c in (a, b):
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                G.add_edge(c[i], c[j])
    for v in a + b:
        G.add_edge(0, v)
    return G

def corpus():
    C = []
    for G in graph_atlas_g():                    # exhaustivo n<=7
        if G.number_of_nodes() >= 4 and nx.is_connected(G):
            C.append(nx.convert_node_labels_to_integers(G))
    for a in range(2, 9):                          # bipartitos completos
        C.append(nx.complete_bipartite_graph(a, a))
        C.append(nx.complete_bipartite_graph(a, a + 1))
    for r in range(2, 9):                           # K1 v 2Kr  (CE de jia_song)
        C.append(join_2Kr(r))
    for k in (5, 6, 7, 8, 9, 10, 11):               # ciclos (C7 = CE de elphick_np)
        C.append(nx.cycle_graph(k))
    for (p, q) in [(3, 3), (4, 4), (5, 5), (3, 5)]:
        C.append(nx.complete_multipartite_graph(p, q))
    for n in (8, 10, 12, 14):
        C.append(nx.path_graph(n))
    return C


def correr_carril(carril, grafos):
    nombre, estado, fn = carril
    peor = (-1e18, None); nviol = 0; nok = 0
    for i, G in enumerate(grafos):
        try:
            g = fn(G)
        except Exception:
            continue
        nok += 1
        if g > peor[0]:
            peor = (g, i)
        if g > TOL:
            nviol += 1
    gmax, idx = peor
    g6 = ""
    if idx is not None:
        g6 = nx.to_graph6_bytes(grafos[idx], header=False).decode().strip()
    return nombre, estado, nok, nviol, gmax, grafos[idx].number_of_nodes() if idx is not None else 0, g6


def main():
    grafos = corpus()
    print(f"BATERÍA-CORPUS MULTI-CARRIL  ·  {len(CARRILES)} conjeturas  ·  {len(grafos)} grafos")
    print("gap>0 = contraejemplo.  Paralelo sobre carriles (multiprocessing).\n")
    with Pool(processes=min(len(CARRILES), 8)) as pool:
        res = pool.map(partial(correr_carril, grafos=grafos), CARRILES)

    print(f"{'carril':32}{'tipo':20}{'#viol':>6}{'gap_max':>11}  extremal")
    print("-" * 92)
    for nombre, estado, nok, nviol, gmax, nnode, g6 in res:
        hit = "  ->CE" if nviol > 0 else ""
        print(f"{nombre:32}{estado:20}{nviol:>6}{gmax:>11.5f}  n={nnode} {g6}{hit}")

    known = [r for r in res if "known" in r[1]]
    redisc = sum(1 for r in known if r[3] > 0)
    abiertas = [r for r in res if "abierta" in r[1]]
    viol_open = [r for r in abiertas if r[3] > 0]
    print("\nRESUMEN:")
    print(f"  known-CE re-descubiertos: {redisc}/{len(known)}  (tubería {'OK' if redisc==len(known) else 'REVISAR'})")
    print(f"  abiertas violadas (candidatas a refutación #2): {len(viol_open)}/{len(abiertas)}")
    if not viol_open:
        print("  -> las abiertas se sostienen en el corpus CPU (esperado: son difíciles).")
        print("     El valor de la GPU = Gemma explorando grafos raros + escala, no fuerza bruta.")
    else:
        for r in viol_open:
            print(f"  >>> {r[0]} viola: gap={r[4]:+.5f} en n={r[5]} {r[6]} — CONFIRMAR EXACTO + estado.")


if __name__ == "__main__":
    main()

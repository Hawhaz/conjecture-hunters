#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ataque DIRIGIDO a la conjetura de Brouwer (2008), abierta y verificada
exhaustivamente SOLO hasta n=11 (Cooper 2021). Un contraejemplo seria famoso.

Brouwer:  S_k(G) = sum_{i=1}^{k} mu_i  <=  e(G) + C(k+1,2)   para todo k=1..n,
donde mu_1>=...>=mu_n son los autovalores del Laplaciano y e=aristas.
gap = max_k ( S_k - e - k(k+1)/2 ).  gap>0 => CONTRAEJEMPLO.

Barremos n>=12 en las familias donde Brouwer NO esta probada / menos testeada
(la conjetura ya esta probada para arboles, unicíclicos, bicíclicos, threshold,
split, regulares, multipartitos completos y a.a.s. aleatorios — asi que casteamos
una red amplia de grafos ESTRUCTURADOS raros + densos y medimos cuan cerca llega).

Honesto: Brouwer resiste desde 2008; lo mas probable es 0 contraejemplos. El valor
es el stress-test riguroso mas alla de la frontera exhaustiva n=11 + cuan cerca
del cero llega (max gap). Cualquier gap>0 se re-verifica exacto antes de gritar.

Uso:  python retos/hunt_brouwer.py
"""
import itertools
import random

import networkx as nx
import numpy as np


def brouwer_gap(G):
    n = G.number_of_nodes(); m = G.number_of_edges()
    mu = np.sort(np.linalg.eigvalsh(nx.laplacian_matrix(G).toarray().astype(float)))[::-1]
    acc = 0.0; peor = -1e18
    for k in range(1, n + 1):
        acc += mu[k - 1]
        peor = max(peor, acc - (m + k * (k + 1) / 2.0))
    return peor


def familias(nmax=44):
    """genera (nombre, G) de grafos estructurados n>=12 (fuera de clases probadas)."""
    yield_count = 0
    def ok(G):
        return G.number_of_nodes() >= 12 and nx.is_connected(G)

    # split incompletos: K_a + b independientes con densidad de cruce variable
    for a in range(4, 20):
        for b in range(4, 20):
            n = a + b
            if n > nmax:
                continue
            for p in (0.3, 0.5, 0.7):
                G = nx.Graph()
                G.add_edges_from((i, j) for i in range(a) for j in range(i + 1, a))
                rng = random.Random(a * 1000 + b * 10 + int(p * 10))
                for i in range(a):
                    for j in range(a, n):
                        if rng.random() < p:
                            G.add_edge(i, j)
                if ok(G):
                    yield (f"split_{a}_{b}_p{p}", G)
    # kite / lollipop / doble-kite (clique + cola + clique)
    for a in range(5, 18):
        for t in range(1, 12):
            G = nx.lollipop_graph(a, t)
            if ok(G):
                yield (f"lollipop_{a}_{t}", G)
    for a in range(5, 14):
        G = nx.complete_graph(a); off = a; prev = 0
        for _ in range(3):
            G.add_edge(prev, off); prev = off; off += 1
        for i in range(a):        # segundo clique
            for j in range(i + 1, a):
                G.add_edge(off + i, off + j)
        G.add_edge(prev, off)
        if ok(G):
            yield (f"dumbbell_{a}", G)
    # multipartitos completos DESBALANCEADOS + menos una arista
    for parts in [(2, 2, n) for n in range(8, 30)] + [(1, 3, n) for n in range(8, 30)] + \
                 [(2, 5, 5, n) for n in range(6, 20)]:
        if sum(parts) > nmax:
            continue
        G = nx.complete_multipartite_graph(*parts)
        G = nx.convert_node_labels_to_integers(G)
        if ok(G):
            yield (f"Kmult_{parts}", G)
            e = list(G.edges())[0]; H = G.copy(); H.remove_edge(*e)
            if ok(H):
                yield (f"Kmult_{parts}_minus_e", H)
    # complete-split join(K_a, empty_b) mas aristas extra en la parte independiente
    for a in range(4, 16):
        for b in range(4, 20):
            n = a + b
            if n > nmax:
                continue
            G = nx.complete_graph(a)
            for j in range(a, n):
                for i in range(a):
                    G.add_edge(i, j)
            # unas pocas aristas dentro del conjunto "independiente" (rompe threshold)
            rng = random.Random(a + b)
            extra = list(itertools.combinations(range(a, n), 2))
            for (u, v) in rng.sample(extra, min(len(extra), b)):
                G.add_edge(u, v)
            if ok(G):
                yield (f"csplit_extra_{a}_{b}", G)
    # densos aleatorios (a.a.s. probado, pero casos finitos sin certificar)
    for n in range(12, nmax, 3):
        for p in (0.5, 0.7, 0.85):
            for s in range(3):
                G = nx.gnp_random_graph(n, p, seed=n * 100 + int(p * 10) + s)
                if ok(G):
                    yield (f"gnp_{n}_{p}_{s}", G)


def main():
    print("ATAQUE DIRIGIDO A BROUWER (abierta; exhaustiva solo n<=11).")
    print("gap = max_k(S_k - e - C(k+1,2));  gap>0 => CONTRAEJEMPLO.\n")
    peor = (-1e18, None); total = 0; viol = []
    for nombre, G in familias():
        total += 1
        g = brouwer_gap(G)
        if g > peor[0]:
            peor = (g, (nombre, G.number_of_nodes()))
        if g > 1e-6:
            g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(G), header=False).decode().strip()
            viol.append((g, nombre, G.number_of_nodes(), g6))
    print(f"grafos estructurados probados (n>=12): {total}")
    print(f"gap MAXIMO (mas cerca de violar): {peor[0]:+.6f}  en {peor[1]}")
    if not viol:
        print("\n0 contraejemplos: Brouwer RESISTIO todo el barrido estructurado n>=12.")
        print("Stress-test superado; evidencia mas alla de la frontera exhaustiva n=11.")
    else:
        print(f"\n>>> {len(viol)} CANDIDATO(S) a contraejemplo de BROUWER (!!!) — re-verificar EXACTO:")
        for g, nombre, n, g6 in sorted(viol, reverse=True)[:5]:
            print(f"    gap={g:+.6f}  {nombre}  n={n}  g6={g6}")


if __name__ == "__main__":
    main()

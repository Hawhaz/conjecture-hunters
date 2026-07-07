#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blanco #1 del pack GPU — Problema 4 de Lin (2018/2019), hermano DIRECTO de la
Jia-Song que ya refutamos, y con la MISMA maquinaria exacta de ∂₂.

Conjetura (ABIERTA): para todo grafo conexo G de orden n,
        ∂₂(G) = λ₂(D(G)) ≤ n/2 − 2,
con igualdad si y sólo si G ≅ K_{n/2, n/2} (bipartito completo balanceado, n par).
Fuente: H. Lin, "On the sum of the k-th largest distance eigenvalues of graphs",
Problem 4, arXiv:1805.09661 = Discrete Appl. Math. 259 (2019) 153-159.
Estado: sólo probado el caso diámetro 2 (Lin: λ₂ ≤ n(d−1)/2 − d, que en d=2 da
n/2−2). Para diámetro ≥3 está SIN estudiar -> ahí cazamos.

Buscamos G con  gap = ∂₂(G) − (n/2 − 2) > 0  (violación). Un ∂₂ numérico por
encima es CANDIDATO; se confirma EXACTO (sympy) antes de afirmar nada.

Uso:  python retos/lin_problem4.py
"""
import itertools
import networkx as nx
import numpy as np
import sympy as sp

x = sp.Symbol("x")
TOL = 1e-9


def d2_num(G):
    D = nx.floyd_warshall_numpy(G)
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]
    return float(ev[1]) if len(ev) >= 2 else None


def d2_exact(G):
    n = G.number_of_nodes()
    Dn = np.array(nx.floyd_warshall_numpy(G), dtype=int)
    roots = sp.real_roots(sp.Matrix(Dn.tolist()).charpoly(x))
    return sp.nsimplify(roots[-2])


def bound(n):
    return sp.Rational(n, 2) - 2


# --------------------------------------------------- familias (diámetro >= 3 sobre todo)
def gen_familias(nmax=64):
    out = []  # (nombre, G)
    def add(name, G):
        if G is not None and G.number_of_nodes() >= 4 and nx.is_connected(G):
            out.append((name, G))

    for a in range(2, nmax // 2 + 1):            # bipartito completo balanceado (extremal)
        add(f"K_{{{a},{a}}}", nx.complete_bipartite_graph(a, a))
    for a in range(2, 20):                        # bipartito completo desbalanceado
        for b in range(a, min(a + 6, nmax - a)):
            add(f"K_{{{a},{b}}}", nx.complete_bipartite_graph(a, b))
    for a in range(2, 22):                         # crown = K_{a,a} menos matching perfecto (diam 3)
        G = nx.complete_bipartite_graph(a, a)
        M = [(i, a + i) for i in range(a)]
        G.remove_edges_from(M); add(f"crown_{a}", G)
    for a in range(2, 16):                          # cocktail party K_{a x 2} (diam 2, control)
        add(f"cocktail_{a}", nx.complete_multipartite_graph(*([2] * a)))
    for parts in [(a, a, a) for a in range(2, 12)] + [(a, a, a, a) for a in range(2, 8)]:
        add("Kmult_" + "x".join(map(str, parts)), nx.complete_multipartite_graph(*parts))
    for a in range(2, 16):                          # dumbbell de dos K_{a,a} unidos por arista/puente
        G1 = nx.complete_bipartite_graph(a, a)
        G = nx.disjoint_union(G1, nx.complete_bipartite_graph(a, a))
        G.add_edge(0, 2 * a); add(f"bibell_{a}", G)
    for a in range(2, 16):                          # dos K_{a,a} unidos por camino P3 (diam mayor)
        G1 = nx.complete_bipartite_graph(a, a); G2 = nx.complete_bipartite_graph(a, a)
        G = nx.disjoint_union(G1, G2); mid = G.number_of_nodes()
        G.add_node(mid); G.add_edge(0, mid); G.add_edge(mid, 2 * a); add(f"bibell_path_{a}", G)
    for a in range(2, 22):                           # K_{a,a} + un pendiente (fuerza diámetro 3)
        G = nx.complete_bipartite_graph(a, a); G.add_edge(0, G.number_of_nodes()); add(f"Kaa_pend_{a}", G)
    for a in range(2, 20):                            # K_{a,a} + camino colgante P2
        G = nx.complete_bipartite_graph(a, a); m = G.number_of_nodes()
        G.add_edge(0, m); G.add_edge(m, m + 1); add(f"Kaa_tail2_{a}", G)
    for (p, q) in [(s, s) for s in range(2, 14)] + [(s, s + 1) for s in range(2, 14)]:
        add(f"doublebroom_{p}_{q}", double_broom(p, q))     # árbol diámetro 3
    for n in range(4, nmax):                          # caminos y ciclos (control diámetro grande)
        add(f"P_{n}", nx.path_graph(n)); add(f"C_{n}", nx.cycle_graph(n))
    for r in range(2, 16):                            # K1 ∨ 2Kr (la familia de la refutación previa)
        add(f"K1v2K{r}", join_2Kr(r))
    for d in (3, 4, 5):                               # hipercubos (bipartitos, diámetro d)
        add(f"Q_{d}", nx.hypercube_graph(d))
    return out


def double_broom(p, q):
    G = nx.Graph(); G.add_edge(0, 1)          # dos centros
    k = 2
    for _ in range(p):
        G.add_edge(0, k); k += 1
    for _ in range(q):
        G.add_edge(1, k); k += 1
    return G


def join_2Kr(r):
    G = nx.Graph(); a = list(range(1, 1 + r)); b = list(range(1 + r, 1 + 2 * r))
    for c in (a, b):
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                G.add_edge(c[i], c[j])
    for v in a + b:
        G.add_edge(0, v)
    return G


def escanear_atlas():
    from networkx.generators.atlas import graph_atlas_g
    peor = (-1e9, None)
    viol = []
    for G in graph_atlas_g():
        n = G.number_of_nodes()
        if n < 4 or not nx.is_connected(G):
            continue
        gap = d2_num(G) - (n / 2 - 2)
        if gap > peor[0]:
            peor = (gap, (n, nx.diameter(G),
                          nx.to_graph6_bytes(nx.convert_node_labels_to_integers(G), header=False).decode().strip()))
        if gap > TOL:
            viol.append((gap, G))
    return peor, viol


def main():
    print("PROBLEMA 4 DE LIN:  ∂₂(G) ≤ n/2 − 2  (igualdad iff K_{n/2,n/2}).  ABIERTA.")
    print("Buscamos  gap = ∂₂ − (n/2 − 2) > 0  (violación).  d≥3 = sin estudiar.\n")

    print("[1] Atlas EXHAUSTIVO n≤7 ...")
    peor, viol = escanear_atlas()
    print(f"    gap MÁXIMO = {peor[0]:+.6f}  en n={peor[1][0]} d={peor[1][1]} g6={peor[1][2]}")
    print(f"    violaciones (gap>0): {len(viol)}")

    print("\n[2] Familias estructuradas (foco diámetro ≥3) ...")
    fam = gen_familias()
    resultados = []
    for name, G in fam:
        n = G.number_of_nodes()
        gap = d2_num(G) - (n / 2 - 2)
        resultados.append((gap, name, n, nx.diameter(G)))
    resultados.sort(reverse=True)
    print(f"    familias evaluadas: {len(resultados)}")
    print("    top-8 por gap (más cerca de violar):")
    for gap, name, n, d in resultados[:8]:
        flag = "  <<< VIOLA" if gap > TOL else ""
        print(f"      gap={gap:+.6f}  {name:20} n={n} d={d}{flag}")

    cands = [(g, n, nm) for (g, nm, n, d) in resultados if g > TOL]
    todo_viol = viol + []  # atlas violators (grafos)
    print(f"\n[3] Candidatos a violación (numérico): atlas={len(viol)}  familias={len(cands)}")
    if not viol and not cands:
        print("    NINGUNA violación numérica. Fuerte evidencia de que la conjetura de Lin")
        print("    SÍ vale en todo lo barrido (incluido diámetro ≥3): el extremal balanceado")
        print("    K_{n/2,n/2} parece genuino. -> Lane validada; sin refutación en CPU.")
    else:
        print("    >>> CANDIDATO(S). Confirmando EXACTO (sympy) el de mayor gap del atlas...")
        for gap, G in sorted(viol, reverse=True)[:3]:
            n = G.number_of_nodes()
            ex = d2_exact(G); b = bound(n)
            print(f"      n={n}: ∂₂={ex} ≈{float(ex):.6f}  vs n/2−2={b}  ->",
                  "VIOLA (exacto)" if sp.simplify(ex - b) > 0 else "no (float ruido)")


if __name__ == "__main__":
    main()

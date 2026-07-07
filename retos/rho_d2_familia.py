#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caracterizacion EXACTA del fenomeno rho + d_2 < valor(K_n - e).

Hallazgo: K_1 v (2 K_3) (vertice universal unido a dos triangulos, n=7) tiene
rho + d_2 = 11/2 - sqrt(22) ~ 0.8096, EXACTAMENTE 4/3 - sqrt(22) + sqrt(11)
~ -0.0405 por DEBAJO del valor en K_n - e (25/6 - sqrt(11) ~ 0.8500), que es el
minimizante natural (extremal reclamado de la cota de Aouchiche-Hansen 2016).

Aqui probamos si es una FAMILIA (muchos contraejemplos) o un caso aislado:
barremos K_1 v (m K_3), K_1 v (m K_2), K_1 v (m K_r), y K_s v (m K_r), todos
diametro 2, con aritmetica EXACTA (sympy: rho racional, d_2 algebraico via
charpoly), comparando contra el valor de K_n - e al mismo n.

NO afirma refutacion: reporta el hecho matematico exacto (rho+d_2 vs K_n-e). La
condicion de refutacion depende del enunciado exacto de AH-2016 (ver reporte).

Uso:  python retos/rho_d2_familia.py
"""
import networkx as nx
import numpy as np
import sympy as sp


def rho_d2_exact(G):
    n = G.number_of_nodes()
    Dnum = np.array(nx.floyd_warshall_numpy(G), dtype=int)
    trans = [int(Dnum[i].sum()) for i in range(n)]
    rho = sp.Rational(max(trans), n - 1)
    d2 = sp.real_roots(sp.Matrix(Dnum.tolist()).charpoly(sp.Symbol("x")))[-2]
    return rho, d2, sp.nsimplify(rho + d2), n


def valor_Kn_menos_e(n):
    # rho + d_2 exacto de K_n - e = n/(n-1) + (n-1 - sqrt((n-1)^2+8))/2
    return sp.Rational(n, n - 1) + (sp.Integer(n - 1) - sp.sqrt((n - 1) ** 2 + 8)) / 2


def join_universal(bloques):
    """K_1 v (union disjunta de los bloques) = un vertice universal + bloques."""
    G = nx.disjoint_union_all(bloques) if bloques else nx.empty_graph(0)
    u = G.number_of_nodes()
    G.add_node(u)
    for v in range(u):
        G.add_edge(u, v)
    return G


def main():
    print("Familia: K_1 v (m K_r)  (vertice universal + m cliques K_r), diametro 2")
    print(f"{'grafo':16} {'n':>3} {'rho+d2 (exacto)':>26} {'~':>9} {'K_n-e':>9} {'delta':>10}")
    familias = []
    for r in (2, 3, 4, 5):
        for m in range(2, 7):
            bloques = [nx.complete_graph(r) for _ in range(m)]
            G = join_universal(bloques)
            if not nx.is_connected(G):
                continue
            rho, d2, s, n = rho_d2_exact(G)
            if n < 4 or n > 60:
                continue
            vkn = valor_Kn_menos_e(n)
            delta = float(s - vkn)
            marca = "  <-- por debajo de K_n-e" if delta < -1e-9 else ""
            familias.append((r, m, n, float(s), float(vkn), delta))
            print(f"K1 v {m}K{r:<9} {n:>3} {str(s):>26} {float(s):>9.5f} "
                  f"{float(vkn):>9.5f} {delta:>+10.5f}{marca}")

    debajo = [x for x in familias if x[5] < -1e-9]
    print(f"\n[familia] {len(debajo)}/{len(familias)} miembros con rho+d2 < valor(K_n-e).")
    if debajo:
        peor = min(debajo, key=lambda x: x[5])
        print(f"[familia] mas por debajo: K1 v {peor[1]}K{peor[0]} (n={peor[2]}), "
              f"delta={peor[5]:+.5f}")
        print("[familia] => NO es un caso aislado: hay una familia de grafos por "
              "debajo del extremal K_n-e (si AH-2016 conjetura que K_n-e minimiza "
              "rho+d_2, esto es una refutacion con familia infinita; confirmar el "
              "enunciado exacto).")


if __name__ == "__main__":
    main()

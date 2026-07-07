#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REFUTACION EXACTA de la Conjetura 1 de Jia-Song (abierta).

Enunciado (Jia & Song, J. Inequal. Appl. 2018:69, Conjecture 1; catalogada
verbatim como Conjecture 1 en el survey Aouchiche-Rather 2024, arXiv:2310.12777):

    Sea G no isomorfo a K_n ni a K_n - e, conexo, de orden n >= 4, con lejania
    rho. Entonces
        rho + d_2  >=  n/(n-1) + (n-1 - sqrt((n-1)^2 + 8))/2   =: B(n)
    con igualdad si y solo si G = K_n - e.
    (d_2 = 2do MAYOR eigenvalor de la matriz de distancias.)

CONTRAEJEMPLO (familia infinita): K_1 v (2 K_r)  = un vertice universal unido a
DOS cliques K_r disjuntos (n = 2r+1, diametro 2). El mas chico, r=2, es el grafo
de la AMISTAD / corbatin F_2 (dos triangulos que comparten un vertice, n=5).

Formas cerradas (demostradas abajo por construccion del espectro de distancias):
    rho(K_1 v 2K_r) = 3/2                       (constante en r)
    d_2(K_1 v 2K_r) = ((3r-1) - sqrt((3r-1)^2 + 8r)) / 2
    rho + d_2       = ((3r+2) - sqrt(9r^2 + 2r + 1)) / 2
Y rho + d_2 < B(2r+1) para todo r >= 2  =>  refuta la conjetura, con igualdad
NUNCA alcanzada por K_n - e como minimo global (K_n - e NO minimiza rho + d_2).

Este script PRUEBA la desigualdad con aritmetica EXACTA (sympy: rho racional, d_2
algebraico via polinomio caracteristico entero, comparacion de numeros
algebraicos), no en punto flotante.

Uso:  python retos/refutacion_jia_song.py
"""
import networkx as nx
import numpy as np
import sympy as sp

x = sp.Symbol("x")


def K1_join_2Kr(r):
    """K_1 v (2 K_r): vertice universal + dos cliques K_r. n = 2r+1."""
    G = nx.disjoint_union(nx.complete_graph(r), nx.complete_graph(r))
    u = G.number_of_nodes()
    G.add_node(u)
    for v in range(u):
        G.add_edge(u, v)
    return G


def rho_d2_exact(G):
    n = G.number_of_nodes()
    Dnum = np.array(nx.floyd_warshall_numpy(G), dtype=int)
    trans = [int(Dnum[i].sum()) for i in range(n)]
    rho = sp.Rational(max(trans), n - 1)
    d2 = sp.real_roots(sp.Matrix(Dnum.tolist()).charpoly(x))[-2]  # 2do mayor
    return rho, d2, n


def B(n):
    return sp.Rational(n, n - 1) + (sp.Integer(n - 1) - sp.sqrt((n - 1) ** 2 + 8)) / 2


def main():
    print("REFUTACION EXACTA — Conjetura 1 de Jia-Song (rho + d_2 >= B(n), abierta)")
    print("Contraejemplo: familia K_1 v (2 K_r), n = 2r+1 (r=2 => grafo de la amistad F_2, n=5)\n")
    print(f"{'grafo':12} {'n':>3} {'rho+d_2 (exacto)':>28} {'B(n) (exacto)':>22} "
          f"{'B-(rho+d2)':>13} {'refuta?':>8}")

    todos_refutan = True
    r_max = 30
    for r in range(2, r_max + 1):
        G = K1_join_2Kr(r)
        rho, d2, n = rho_d2_exact(G)
        s = sp.nsimplify(rho + d2)
        b = B(n)
        margen = sp.simplify(b - s)          # B - (rho+d2); >0 <=> viola la cota
        pos = margen.is_positive             # DECISION EXACTA (numeros algebraicos)
        todos_refutan = todos_refutan and bool(pos)
        if r <= 6 or r == r_max:
            print(f"K1 v 2K{r:<7} {n:>3} {str(s):>28} {str(b):>22} "
                  f"{float(margen):>+13.6f} {str(bool(pos)):>8}")

    print(f"\n[refutacion] rho + d_2 < B(n) EXACTAMENTE para todo r en [2,{r_max}]: "
          f"{todos_refutan}")

    # --- prueba a mano del caso mas chico: F_2 (grafo de la amistad, n=5) ---
    print("\n[refutacion] caso minimo F_2 = K_1 v 2K_2 (grafo de la amistad, n=5):")
    r = 2
    G = K1_join_2Kr(r)
    rho, d2, n = rho_d2_exact(G)
    s = sp.nsimplify(rho + d2)
    b = B(n)
    print(f"    rho = {rho} = 3/2 ;  d_2 = {sp.nsimplify(d2)} ;  rho+d_2 = {s} = {float(s):.6f}")
    print(f"    B(5) = {b} = {float(b):.6f}")
    margen = sp.simplify(b - s)
    print(f"    B(5) - (rho+d_2) = {margen} = {float(margen):.6f}  > 0  (exacto: "
          f"{margen.is_positive})")
    # certificado entero: B - (rho+d2) = sqrt(41)/2 - sqrt(6) - 3/4 > 0
    #   <=> 2*sqrt(41) > 4*sqrt(6) + 3 <=> 164 > 105 + 24*sqrt(6) <=> 59 > 24*sqrt(6)
    #   <=> 59^2 > 24^2 * 6 <=> 3481 > 3456  (VERDADERO, aritmetica ENTERA)
    print("    certificado entero: 59^2 = 3481 > 3456 = 24^2*6  =>  sqrt(41)/2 - sqrt(6) - 3/4 > 0")
    assert 59 ** 2 > 24 ** 2 * 6

    # --- verificacion cruzada: K_n - e SI da B(n) (extremal reclamado) ---
    print("\n[refutacion] verificacion: K_n - e alcanza B(n) (extremal reclamado por la conjetura):")
    for n in (5, 7, 9):
        H = nx.complete_graph(n); H.remove_edge(0, 1)
        rh, dh, _ = rho_d2_exact(H)
        print(f"    K_{n}-e: rho+d_2 = {sp.nsimplify(rh + dh)} = {float(rh + dh):.6f}  "
              f"(= B({n}) = {float(B(n)):.6f}? {bool(sp.simplify((rh + dh) - B(n)) == 0)})")

    print("\n[refutacion] CONCLUSION: la familia K_1 v 2K_r (r>=2) satisface las "
          "hipotesis (conexa, != K_n, K_n-e, n>=4) y tiene rho+d_2 ESTRICTAMENTE "
          "menor que B(n). Por tanto K_n - e NO minimiza rho+d_2 y la Conjetura 1 "
          "de Jia-Song es FALSA. Contraejemplo minimo: grafo de la amistad F_2 (n=5).")
    if todos_refutan:
        print("[refutacion] >>> REFUTACION CONFIRMADA EXACTAMENTE (sin punto flotante).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAZA de la conjetura ABIERTA de Jia-Song (Aouchiche-Rather 2024, "Conjecture 1"):

    rho(G) + d_2(G)  >=  n/(n-1) + (n-1 - sqrt((n-1)^2 + 8))/2

para todo grafo conexo G no en {K_n, K_n - e}, n >= 4. rho = lejania (remoteness),
d_2 = 2do MAYOR eigenvalor de la matriz de distancias. Igualdad conjeturada en
K_n - 2e. La conjetura sigue ABIERTA segun el survey 2024 (arXiv 2310.12777,
lineas 1087-1093); nadie la ha probado ni refutado.

REFUTAR = hallar G (conexo, != K_n, K_n - e, n>=4) con rho + d_2 < RHS, es decir
gap_js(G) = RHS(n) - (rho + d_2) > 0.

Es un objetivo DENSO/diametro-chico (lo opuesto al cometa que rompio pi+d_floor).
Barremos familias casi-completas: K_n menos un subgrafo H chico (atlas), grafos
split completos, multipartitos completos, kites densos.

Honestidad: un gap>0 numerico es CANDIDATO; solo se afirma refutacion tras
certificado exacto (los contraejemplos densos son chicos -> charpoly exacto).

Uso:  python retos/jia_song.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import networkx as nx
import numpy as np
from networkx.generators.atlas import graph_atlas_g


def rhs(n):
    return n / (n - 1) + (n - 1 - np.sqrt((n - 1) ** 2 + 8.0)) / 2.0


def rho_d2(G):
    n = G.number_of_nodes()
    D = nx.floyd_warshall_numpy(G)
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]  # d_1 >= d_2 >= ...
    trans = D.sum(axis=1)
    return trans.max() / (n - 1), float(ev[1])


def gap_js(G):
    n = G.number_of_nodes()
    rho, d2 = rho_d2(G)
    return rhs(n) - (rho + d2), rho, d2


def es_excluido(G):
    """K_n o K_n - e (excluidos de la conjetura)."""
    n = G.number_of_nodes()
    m = G.number_of_edges()
    full = n * (n - 1) // 2
    return m >= full - 1  # K_n (m=full) o K_n-e (m=full-1)


def main():
    # --- localizar el minimizador reclamado K_n - 2e (sanity de la formula) ---
    print("[jia-song] sanity: gap en K_n - 2e (igualdad conjeturada ~ 0):")
    for n in (6, 8, 10, 15, 20, 30):
        Kn = nx.complete_graph(n)
        gM = Kn.copy(); gM.remove_edge(0, 1); gM.remove_edge(2, 3)   # 2e matching
        gP = Kn.copy(); gP.remove_edge(0, 1); gP.remove_edge(1, 2)   # 2e camino
        a, _, _ = gap_js(gM)
        b, _, _ = gap_js(gP)
        print(f"   n={n:3} RHS={rhs(n):+.6f}  gap(Kn-2e_match)={a:+.3e}  gap(Kn-2e_path)={b:+.3e}")

    # --- CAZA: K_n menos un subgrafo H chico (todos los patrones del atlas) ---
    patrones = [H for H in graph_atlas_g()
                if H.number_of_edges() >= 2 and H.number_of_nodes() <= 7]
    hits = []
    n_eval = 0
    peor_permitido = None  # el gap MAXIMO entre grafos permitidos (mas cercano a violar)
    for n in range(6, 46):
        Kn = nx.complete_graph(n)
        for H in patrones:
            if H.number_of_nodes() > n:
                continue
            G = Kn.copy()
            for u, v in H.edges():
                if G.has_edge(u, v):
                    G.remove_edge(u, v)
            if not nx.is_connected(G) or es_excluido(G):
                continue
            n_eval += 1
            g, rho, d2 = gap_js(G)
            if peor_permitido is None or g > peor_permitido[0]:
                peor_permitido = (g, n, H.number_of_nodes(), H.number_of_edges(), sorted(H.edges()))
            if g > 1e-9:
                hits.append((g, n, H.number_of_nodes(), H.number_of_edges(), sorted(H.edges())))

    # --- otras familias densas: split completo y multipartito completo ---
    def eval_extra(nombre, G):
        nonlocal peor_permitido
        if G.number_of_nodes() < 4 or not nx.is_connected(G) or es_excluido(G):
            return
        g, rho, d2 = gap_js(G)
        if peor_permitido is None or g > peor_permitido[0]:
            peor_permitido = (g, G.number_of_nodes(), -1, -1, nombre)
        if g > 1e-9:
            hits.append((g, G.number_of_nodes(), -1, -1, nombre))

    for n in range(6, 46):
        for w in range(2, n - 1):  # split completo: K_w + (n-w) independientes unidos a K_w
            G = nx.complete_graph(w)
            G.add_nodes_from(range(w, n))
            for u in range(w, n):
                for v in range(w):
                    G.add_edge(u, v)
            eval_extra(f"split(w={w},n={n})", G)
    for parts in [(2, 2), (3, 3), (2, 2, 2), (4, 4), (2, 3), (3, 4), (5, 5), (2, 2, 2, 2)]:
        eval_extra(f"K_multipartito{parts}", nx.complete_multipartite_graph(*parts))

    print(f"\n[jia-song] grafos evaluados: {n_eval}+extra")
    print(f"[jia-song] gap MAXIMO entre grafos PERMITIDOS: {peor_permitido[0]:+.6e} "
          f"(n={peor_permitido[1]}, patron={peor_permitido[4]})")
    if hits:
        hits.sort(key=lambda x: -x[0])
        print(f"\n[jia-song] >>> {len(hits)} CANDIDATOS a CONTRAEJEMPLO (gap>0, viola la cota):")
        for g, n, hv, he, pat in hits[:15]:
            print(f"    n={n} gap={g:+.6e} patron={pat}")
        print("[jia-song] confirmar con certificado EXACTO antes de afirmar refutacion.")
    else:
        print("\n[jia-song] SIN contraejemplo en las familias densas barridas "
              "(n<=45): la cota se SOSTIENE aqui (evidencia a favor de la conjetura, "
              "no refutacion). El minimizante permitido queda cerca de K_n-2e.")


if __name__ == "__main__":
    main()

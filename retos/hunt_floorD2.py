#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caza del objetivo #5: pi + d_{floor(D/2)} > 0 (y rho + d_{floor(D/2)} > 0) para
grafos conexos GENERALES.

Aouchiche-Hansen lo probaron SOLO para ARBOLES (survey Prop 4.19/4.14); el caso
general conexo quedo SIN reclamar -> tipico "hay contraejemplo sospechado". La
version de PROXIMIDAD es la refutable (pi NO cumple pi>=D/2, a diferencia de rho,
que si -> la version rho es casi seguro cierta general).

Buscamos NO-arboles de diametro grande donde pi (o rho) + d_{floor(D/2)} <= 0.
Familias: hub-clique con dos colas (cometa de clique), lollipop, dumbbell,
unicyclic (ciclo + cola). n hasta ~90.

Honestidad: un <=0 numerico es CANDIDATO; se confirma exacto + estado antes de
afirmar nada. rho-version: si NO baja de 0, es evidencia de que es cierta general.

Uso:  python retos/hunt_floorD2.py
"""
import networkx as nx
import numpy as np


def clique_comet(r, t1, t2):
    """K_r (hub) + dos caminos de largo t1, t2 desde un vertice del clique."""
    G = nx.complete_graph(r)
    nxt = r
    for t in (t1, t2):
        prev = 0
        for _ in range(t):
            G.add_edge(prev, nxt); prev = nxt; nxt += 1
    return G


def lollipop(r, t):
    return nx.lollipop_graph(r, t) if r >= 2 and t >= 0 else None


def dumbbell(r, t):
    """Dos K_r unidos por un camino de largo t."""
    G = nx.complete_graph(r)
    nxt = r
    prev = 0
    for _ in range(t):
        G.add_edge(prev, nxt); prev = nxt; nxt += 1
    # segundo clique pegado al final del camino
    base = prev
    off = nxt
    for i in range(r):
        G.add_node(off + i)
    for i in range(r):
        for j in range(i + 1, r):
            G.add_edge(off + i, off + j)
    G.add_edge(base, off)
    return G


def ciclo_cola(m, t):
    G = nx.cycle_graph(m)
    prev = 0
    nxt = m
    for _ in range(t):
        G.add_edge(prev, nxt); prev = nxt; nxt += 1
    return G


def metrics(G):
    n = G.number_of_nodes()
    D = nx.floyd_warshall_numpy(G)
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]
    trans = D.sum(axis=1)
    diam = int(D.max())
    return n, diam, float(trans.min()) / (n - 1), float(trans.max()) / (n - 1), ev


def dk(ev, k):
    return ev[k - 1] if 1 <= k <= len(ev) else None


def barrer(nombre, generador, params):
    peor_pi = (1e9, None)   # (pi+d_{floor(D/2)}, info)  buscamos el MINIMO
    peor_rho = (1e9, None)
    cont_pi = cont_rho = 0
    total = 0
    for p in params:
        G = generador(*p)
        if G is None or G.number_of_nodes() < 4 or not nx.is_connected(G):
            continue
        n, diam, pi, rho, ev = metrics(G)
        if diam < 4:  # floor(D/2) < 2 -> trivial
            continue
        k = diam // 2
        d = dk(ev, k)
        if d is None:
            continue
        total += 1
        spi, srho = pi + d, rho + d
        if spi < peor_pi[0]:
            peor_pi = (spi, (p, n, diam, k))
        if srho < peor_rho[0]:
            peor_rho = (srho, (p, n, diam, k))
        if spi <= 1e-9:
            cont_pi += 1
        if srho <= 1e-9:
            cont_rho += 1
    print(f"[{nombre}] evaluados={total}")
    print(f"   pi + d_floor(D/2):  MIN={peor_pi[0]:+.6f}  en {peor_pi[1]}   (<=0: {cont_pi})")
    print(f"   rho+ d_floor(D/2):  MIN={peor_rho[0]:+.6f}  en {peor_rho[1]}   (<=0: {cont_rho})")
    return cont_pi, cont_rho


def main():
    print("Objetivo #5: pi/rho + d_{floor(D/2)} > 0 para grafos conexos GENERALES")
    print("(probado solo para arboles; buscamos contraejemplo NO-arbol de D grande)\n")
    tot_pi = tot_rho = 0

    # cometa de clique: hub K_r + dos colas
    params = [(r, t1, t2) for r in range(2, 9) for t1 in range(1, 40) for t2 in range(1, t1 + 1)]
    a, b = barrer("clique-cometa K_r + 2 colas", clique_comet, params)
    tot_pi += a; tot_rho += b

    # lollipop K_r + cola
    params = [(r, t) for r in range(2, 12) for t in range(1, 80)]
    a, b = barrer("lollipop K_r + cola", lollipop, params)
    tot_pi += a; tot_rho += b

    # dumbbell: dos K_r + camino
    params = [(r, t) for r in range(2, 9) for t in range(1, 50)]
    a, b = barrer("dumbbell 2xK_r + camino", dumbbell, params)
    tot_pi += a; tot_rho += b

    # unicyclic: ciclo + cola
    params = [(m, t) for m in range(3, 12) for t in range(1, 60)]
    a, b = barrer("unicyclic C_m + cola", ciclo_cola, params)
    tot_pi += a; tot_rho += b

    print(f"\n[resumen] candidatos pi<=0: {tot_pi}   rho<=0: {tot_rho}")
    if tot_pi == 0 and tot_rho == 0:
        print("[resumen] NINGUN contraejemplo en las familias barridas: fuerte evidencia de que")
        print("          pi/rho + d_floor(D/2) > 0 tambien vale para grafos generales (no solo arboles).")
    else:
        print("[resumen] >>> CANDIDATO(S): confirmar exacto + estado abierto antes de afirmar.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reto CAL-3 como BUSQUEDA (no enumeracion): hallar el contraejemplo de
pi + d_floor(2D/3) > 0 partiendo de un arbol GENERICO y usando SOLO movimientos
locales de arbol, guiados por un fitness con SHAPING de diametro.

Diferencia con retos/cal3_n203.py: alli sembramos la familia exacta
(cometa-de-doble-cola) y barrimos parametros. Aqui NO se codifica la familia: se
arranca de P13 (un camino generico) y la busqueda DESCUBRE por si sola la
estructura hub+colas creciendo el arbol.

Receta (Roucairol-Cazenave, arXiv 2409.18626 / ECAI-2025): el score real
-(pi + d_{floor(2D/3)}) tiene un PLATEAU porque el flooring hace que crecer el
diametro no mueva el indice del eigenvalor rastreado. Fix: evaluar d en el indice
FRACCIONARIO 2D/3 por interpolacion lineal del espectro de distancias -> gradiente
suave que premia crecer D. Cuando el gap REAL (con floor) cruza 0, es contraejemplo
y se certifica exacto aparte.

Movimientos (arboles-only, como AMCS): agregar hoja (a un vertice) y subdividir
arista. Macro-move opcional: agregar k hojas al vertice de mayor grado (el hub
emergente) para alcanzar n grande en pocos pasos — sigue siendo un operador local
legitimo, no codifica la familia.

Uso:  python retos/cal3_busqueda.py
"""
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "certificados"))

import networkx as nx
import numpy as np


def dist_eigs_desc(T):
    """Espectro de la matriz de distancias en orden DESCENDENTE + (D, pi, n)."""
    n = T.number_of_nodes()
    nodos = sorted(T.nodes())
    idx = {v: i for i, v in enumerate(nodos)}
    D = np.zeros((n, n), dtype=np.float64)
    diam = 0
    trans_min = None
    for s in nodos:
        dd = nx.single_source_shortest_path_length(T, s)
        fila = 0.0
        i = idx[s]
        for t, d in dd.items():
            D[i, idx[t]] = d
            if d > diam:
                diam = d
            fila += d
        if trans_min is None or fila < trans_min:
            trans_min = fila
    ev = np.sort(np.linalg.eigvalsh(D))[::-1]  # descendente
    pi = trans_min / (n - 1)
    return ev, diam, pi, n


def true_gap(ev, diam, pi):
    """gap real de CAL-3 con floor: -(pi + d_{floor(2D/3)}) (convencion neg-index)."""
    k = (2 * diam) // 3
    idx = (len(ev) - 1) if k == 0 else (k - 1)
    return -(pi + ev[idx])


def shaped_gap(ev, diam, pi):
    """Score con SHAPING: d evaluado en indice fraccionario 2D/3 (interpolado)
    + un pequeno bono de diametro (la direccion productiva de CAL-3).

    Suaviza el plateau del flooring -> crecer D siempre mueve el score.
    """
    n = len(ev)
    x = 2.0 * diam / 3.0
    lo = int(np.floor(x))
    hi = int(np.ceil(x))
    frac = x - lo
    # indices 1-based -> 0-based; clamp a rango valido
    def at(j):
        j = min(max(j, 1), n)  # j en [1, n]
        return ev[j - 1]
    d_interp = at(lo) * (1.0 - frac) + at(hi) * frac
    return -(pi + d_interp) + 0.02 * diam


def hub(T):
    """Vertice de mayor grado (el hub emergente)."""
    return max(T.nodes(), key=lambda v: T.degree(v))


def agregar_hojas(T, v, k):
    H = T.copy()
    nxt = max(H.nodes()) + 1
    for _ in range(k):
        H.add_edge(v, nxt)
        nxt += 1
    return H


def subdividir(T, u, v):
    H = T.copy()
    w = max(H.nodes()) + 1
    H.remove_edge(u, v)
    H.add_edge(u, w)
    H.add_edge(w, v)
    return H


def extremos_diametro(T):
    """Par de vertices que realizan el diametro (para alargar colas)."""
    ecc = nx.eccentricity(T)
    a = max(ecc, key=ecc.get)
    dist = nx.single_source_shortest_path_length(T, a)
    b = max(dist, key=dist.get)
    return a, b


def candidatos(T, rng):
    """Genera movimientos-candidato (arboles-only). Mezcla: crecer hub, alargar
    colas (subdividir cerca de los extremos del diametro) y ruido generico."""
    cands = []
    h = hub(T)
    # hub emergente: pocas hojas por paso (sin macro que colapse a estrella pura).
    cands.append(("hub+1", agregar_hojas(T, h, 1)))
    cands.append(("hub+2", agregar_hojas(T, h, 2)))
    cands.append(("hub+3", agregar_hojas(T, h, 3)))
    # alargar el diametro: subdividir aristas en el camino entre los extremos.
    try:
        a, b = extremos_diametro(T)
        cam = nx.shortest_path(T, a, b)
        for pos in (0, len(cam) // 2, len(cam) - 2):
            if 0 <= pos < len(cam) - 1:
                cands.append(("subdiv@%d" % pos, subdividir(T, cam[pos], cam[pos + 1])))
    except Exception:
        pass
    # ruido generico
    vs = list(T.nodes())
    cands.append(("hoja_rand", agregar_hojas(T, vs[rng.randrange(len(vs))], 1)))
    es = list(T.edges())
    u, v = es[rng.randrange(len(es))]
    cands.append(("subdiv_rand", subdividir(T, u, v)))
    return cands


def g6(T):
    H = nx.convert_node_labels_to_integers(T, ordering="sorted")
    return nx.to_graph6_bytes(H, header=False).decode("ascii").strip()


def main():
    import random
    rng = random.Random(20260706)

    T = nx.path_graph(13)  # SEMILLA GENERICA (no la familia): un camino P13
    ev, diam, pi, n = dist_eigs_desc(T)
    best_shaped = shaped_gap(ev, diam, pi)

    t0 = time.time()
    presupuesto_s = 150.0
    max_n = 216
    paso = 0
    D_actual = diam
    stall = 0
    print(f"[busqueda CAL-3] semilla P13: n={n} D={diam} gap_real={true_gap(ev,diam,pi):+.6f}")

    while time.time() - t0 < presupuesto_s:
        paso += 1
        evals = []
        for nombre, H in candidatos(T, rng):
            if H.number_of_nodes() > max_n:
                continue
            evh, dh, pih, nh = dist_eigs_desc(H)
            evals.append((shaped_gap(evh, dh, pih), dh, nombre, H, evh, pih, nh))
        if not evals:
            break
        # anti-colapso: si el diametro se estanca (>=6 pasos sin crecer), forzar el
        # candidato de mayor D; si no, el de mayor score con shaping.
        if stall >= 6:
            elegido = max(evals, key=lambda e: (e[1], e[0]))
            stall = 0
        else:
            elegido = max(evals, key=lambda e: e[0])
        mejor_s, dh, nombre, T, evh, pih, nh = elegido
        best_shaped = mejor_s
        if dh > D_actual:
            D_actual = dh
            stall = 0
        else:
            stall += 1
        tg = true_gap(evh, dh, pih)
        if paso % 20 == 0 or tg > 1e-9:
            print(f"  paso {paso}: mov={nombre} n={nh} D={dh} k={(2*dh)//3} "
                  f"shaped={mejor_s:+.5f} gap_real={tg:+.7f}")
        if tg > 1e-9:
            gs = g6(T)
            print(f"\n[busqueda CAL-3] >>> CONTRAEJEMPLO HALLADO POR BUSQUEDA: "
                  f"n={nh} D={dh} gap_real={tg:+.9f}")
            print(f"    g6={gs[:60]}... ({len(gs)} chars)")
            try:
                from verify import certificar
                cert = certificar(gs, "cal3")
                print(f"[busqueda CAL-3] CERTIFICADO EXACTO: "
                      f"certificado={cert.get('certificado')} metodo={cert.get('metodo')} "
                      f"margen={cert.get('margen')}")
            except Exception as e:
                print(f"[busqueda CAL-3] certificado no disponible: {e}")
            print(f"[busqueda CAL-3] pasos={paso} tiempo={time.time()-t0:.1f}s "
                  f"(AMCS: 16.5 min; sembrado de familia: <1s)")
            return

    ev, diam, pi, n = dist_eigs_desc(T)
    print(f"\n[busqueda CAL-3] sin cruzar 0 en {time.time()-t0:.0f}s / {paso} pasos: "
          f"mejor n={n} D={diam} gap_real={true_gap(ev,diam,pi):+.6f} shaped={best_shaped:+.5f}")
    print("[busqueda CAL-3] (el shaping subio D y el hub; con mas presupuesto o beam/AMCS "
          "deberia cruzar; la familia exacta ya esta certificada en retos/cal3_n203.py)")


if __name__ == "__main__":
    main()

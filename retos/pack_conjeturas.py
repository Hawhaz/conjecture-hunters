#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PACK DE CONJETURAS — carriles perfeccionados y BLINDADOS con gate anti-basura.

Cada carril = un evaluador EXACTO de una conjetura, con:
  - gap(G): float; gap > 0  <=>  contraejemplo (viola la conjetura).
  - kind: 'validacion' (contraejemplo CONOCIDO -> el motor DEBE re-descubrirlo) o
          'abierta'    (sin resolver -> caza real; debe sostenerse en lo conocido).
  - aplica(G): dominio (p.ej. sólo árboles, o excluir grafos completos).
  - extremal(n): grafo de igualdad reclamado (para verificar que la cota es AJUSTADA).
  - ce(): grafo con contraejemplo conocido (para los de validación).

`verificar()` es el GATE (lo corre pytest): las de validación DEBEN dar gap>0 en su
contraejemplo; las abiertas DEBEN sostenerse (gap<=0) en TODO el corpus de control y
dar gap≈0 en su extremal. Si algo falla = basura (mala mates o mal código) -> no sale
a la GPU. Esto es lo que mató el falso positivo de K4 en Bollobás.

Uso:
  python retos/pack_conjeturas.py            # gate + batería en paralelo
  python retos/pack_conjeturas.py --gate     # sólo el gate (rápido)
  pytest retos/test_pack_conjeturas.py       # el gate como test
"""
import argparse
import math
from functools import partial
from multiprocessing import Pool

import networkx as nx
import numpy as np
from networkx.generators.atlas import graph_atlas_g

TOL = 1e-7


# ------------------------------------------------------------- invariantes
def adj_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.to_numpy_array(G)))[::-1]

def lap_eigs(G):
    L = nx.laplacian_matrix(G).toarray().astype(float)
    return np.sort(np.linalg.eigvalsh(L))[::-1]

def dist_eigs(G):
    return np.sort(np.linalg.eigvalsh(nx.floyd_warshall_numpy(G)))[::-1]

def omega(G):
    return max((len(c) for c in nx.find_cliques(G)), default=1)

def alpha(G):
    return max((len(c) for c in nx.find_cliques(nx.complement(G))), default=1)

def remoteness(G):
    n = G.number_of_nodes()
    return float(nx.floyd_warshall_numpy(G).sum(axis=1).max()) / (n - 1)

def lap_energy(G):
    n = G.number_of_nodes(); m = G.number_of_edges()
    mu = lap_eigs(G)
    return float(np.abs(mu - 2 * m / n).sum())

def es_completo(G):
    n = G.number_of_nodes()
    return G.number_of_edges() == n * (n - 1) // 2


# ------------------------------------------------------------- grafos nombrados
def friendship(r):                    # K1 v 2Kr ; r=2 -> F2 (grafo de la amistad)
    G = nx.Graph(); a = list(range(1, 1 + r)); b = list(range(1 + r, 1 + 2 * r))
    for c in (a, b):
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                G.add_edge(c[i], c[j])
    for v in a + b:
        G.add_edge(0, v)
    return G

def pineapple(n):                     # clique K_c + (n-c) pendientes en un vértice del clique
    c = 1 + (2 * n) // 3
    c = max(2, min(c, n))
    G = nx.complete_graph(c)
    for v in range(c, n):
        G.add_edge(0, v)
    return G


# ------------------------------------------------------------- carriles
def gap_jia_song(G):                  # rho + d2 >= B(n)     (validación: CE = F2)
    n = G.number_of_nodes()
    B = n / (n - 1) + (n - 1 - math.sqrt((n - 1) ** 2 + 8)) / 2
    return B - (remoteness(G) + dist_eigs(G)[1])

def gap_elphick_np(G):                # sum_{i<=n+} l_i^2 <= 2(1-1/w)m  (variante ell=n+: FALSA, CE=C7)
    m = G.number_of_edges(); ev = adj_eigs(G); w = omega(G)
    npos = int((ev > 1e-9).sum())
    return float((ev[:npos] ** 2).sum()) - 2 * (1 - 1 / w) * m

def gap_lin_p4(G):                    # d2 <= n/2 - 2         (abierta; extremal K_{n/2,n/2})
    n = G.number_of_nodes()
    return dist_eigs(G)[1] - (n / 2 - 2)

def gap_bollobas(G):                  # l1^2+l2^2 <= 2(1-1/w)m (abierta; EXCLUYE completos)
    m = G.number_of_edges(); ev = adj_eigs(G); w = omega(G)
    return (ev[0] ** 2 + ev[1] ** 2) - 2 * (1 - 1 / w) * m

def gap_efgw(G):                      # min(s+,s-) >= n-1     (abierta; conexo)
    n = G.number_of_nodes(); ev = adj_eigs(G)
    sp = float((ev[ev > 0] ** 2).sum()); sm = float((ev[ev < 0] ** 2).sum())
    return (n - 1) - min(sp, sm)

def gap_graffiti(G):                  # sum_{l>0} l >= n - alpha  (abierta; extremal K_n)
    n = G.number_of_nodes(); ev = adj_eigs(G)
    return (n - alpha(G)) - float(ev[ev > 0].sum())

def gap_powers3(G):                   # l3 <= floor(n/3)      (abierta; i=4 ya refutada por Linz)
    ev = adj_eigs(G)
    return (ev[2] if len(ev) >= 3 else -9.0) - math.floor(G.number_of_nodes() / 3)

def gap_brouwer(G):                   # sum_{i<=k} mu_i <= m + k(k+1)/2  para todo k  (abierta; verif. n<=11)
    n = G.number_of_nodes(); m = G.number_of_edges()
    mu = lap_eigs(G); acc = 0.0; peor = -1e18
    for k in range(1, n + 1):
        acc += mu[k - 1]
        peor = max(peor, acc - (m + k * (k + 1) / 2))
    return peor

def gap_le_tree_min(G):               # LE(P_n) <= LE(T)  para árboles  (abierta; extremal P_n)
    n = G.number_of_nodes()
    return lap_energy(nx.path_graph(n)) - lap_energy(G)


LANES = [
    # nombre, kind, gap, aplica, extremal(n)->G|None, ce()->G|None
    ("jia_song  rho+d2>=B(n)",   "validacion", gap_jia_song,  lambda G: True,                 None,                          lambda: friendship(2)),
    ("elphick   sum_{n+}l^2<=..", "validacion", gap_elphick_np, lambda G: True,                None,                          lambda: nx.cycle_graph(7)),
    ("lin_p4    d2<=n/2-2",       "abierta",    gap_lin_p4,    lambda G: True,                 lambda n: nx.complete_bipartite_graph(n // 2, n // 2) if n % 2 == 0 else None, None),
    ("bollobas  l1^2+l2^2<=..",   "abierta",    gap_bollobas,  lambda G: not es_completo(G),   None,                          None),
    ("efgw      min(s+,s-)>=n-1", "abierta",    gap_efgw,      lambda G: True,                 None,                          None),
    ("graffiti  E>=2(n-alpha)",   "abierta",    gap_graffiti,  lambda G: True,                 lambda n: nx.complete_graph(n), None),
    ("powers    l3<=floor(n/3)",  "abierta",    gap_powers3,   lambda G: True,                 None,                          None),
    ("brouwer   sum mu_i<=..",    "abierta",    gap_brouwer,   lambda G: True,                 None,                          None),
    ("le_tree   LE(Pn)<=LE(T)",   "abierta",    gap_le_tree_min, lambda G: nx.is_tree(G),      lambda n: nx.path_graph(n),    None),
]


# ------------------------------------------------------------- corpus de control
def corpus_control():
    C = []
    for G in graph_atlas_g():                       # exhaustivo conexo n<=7
        if G.number_of_nodes() >= 4 and nx.is_connected(G):
            C.append(nx.convert_node_labels_to_integers(G))
    for a in range(2, 9):
        C.append(nx.complete_bipartite_graph(a, a))
        C.append(nx.complete_bipartite_graph(a, a + 1))
    for r in range(2, 9):
        C.append(friendship(r))
    for k in (5, 6, 7, 8, 9, 10, 11):
        C.append(nx.cycle_graph(k))
    for (p, q) in [(3, 3), (4, 4), (5, 5), (3, 5)]:
        C.append(nx.complete_multipartite_graph(p, q))
    for n in (8, 10, 12, 14):
        C.append(nx.path_graph(n))
        C.append(nx.star_graph(n - 1))
        C.append(nx.wheel_graph(n))
    return C


# ------------------------------------------------------------- GATE (lo corre pytest)
def verificar(verbose=True):
    """Gate anti-basura. Lanza AssertionError si algo huele a basura."""
    C = corpus_control()
    problemas = []
    for nombre, kind, gap, aplica, extremal, ce in LANES:
        if kind == "validacion":
            g = gap(ce())
            ok = g > TOL
            if verbose:
                print(f"  [validacion] {nombre:26} re-descubre CE: gap={g:+.5f}  {'OK' if ok else 'FALLA'}")
            if not ok:
                problemas.append(f"{nombre}: NO re-descubre su contraejemplo (gap={g:+.5f})")
        else:  # abierta -> debe sostenerse en TODO el corpus aplicable
            peor = (-1e18, None)
            for G in C:
                if not aplica(G):
                    continue
                g = gap(G)
                if g > peor[0]:
                    peor = (g, G)
            gmax, Gw = peor
            ok = gmax <= TOL
            extra = ""
            if extremal is not None:                # la cota debe ser AJUSTADA en el extremal
                for nn in (4, 6, 8, 10, 12):
                    Ge = extremal(nn)
                    if Ge is not None and aplica(Ge):
                        ge = gap(Ge)
                        if abs(ge) > 1e-6:
                            problemas.append(f"{nombre}: extremal n={nn} no da igualdad (gap={ge:+.6f})")
                        else:
                            extra = f" · extremal n={nn}: gap≈0 OK"
                        break
            if verbose:
                nn = Gw.number_of_nodes() if Gw is not None else 0
                print(f"  [abierta]    {nombre:26} se sostiene: gap_max={gmax:+.5f} (n={nn})  {'OK' if ok else 'VIOLA'}{extra}")
            if not ok:
                problemas.append(f"{nombre}: FALSO POSITIVO en corpus de control (gap={gmax:+.5f}) -> revisar codificación")
    if problemas:
        raise AssertionError("GATE ANTI-BASURA FALLÓ:\n  - " + "\n  - ".join(problemas))
    if verbose:
        val = sum(1 for L in LANES if L[1] == "validacion")
        ab = sum(1 for L in LANES if L[1] == "abierta")
        print(f"\n  GATE VERDE: {val} carriles de validación re-descubren su CE · "
              f"{ab} abiertas se sostienen y sus extremales son ajustados. Cero basura.")
    return True


def _corre_carril(i, grafos):
    nombre, kind, gap, aplica, extremal, ce = LANES[i]
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


def batería(grafos=None):
    grafos = grafos or corpus_control()
    print(f"\nBATERÍA MULTI-CARRIL · {len(LANES)} conjeturas · {len(grafos)} grafos (paralelo)\n")
    with Pool(processes=min(len(LANES), 8)) as pool:
        res = pool.map(partial(_corre_carril, grafos=grafos), range(len(LANES)))
    print(f"{'carril':28}{'tipo':12}{'#viol':>6}{'gap_max':>11}  extremal")
    print("-" * 78)
    for nombre, kind, nviol, gmax, nn, g6 in res:
        hit = "  ->CE" if nviol > 0 else ""
        print(f"{nombre:28}{kind:12}{nviol:>6}{gmax:>11.5f}  n={nn} {g6}{hit}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true", help="sólo el gate anti-basura")
    args = ap.parse_args()
    print("GATE ANTI-BASURA (pytest lo corre en cada commit):")
    verificar()
    if not args.gate:
        batería()


if __name__ == "__main__":
    main()

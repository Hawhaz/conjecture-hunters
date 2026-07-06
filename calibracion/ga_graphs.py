#!/usr/bin/env python3
"""GA directo sobre grafos (§9) — valida la DINÁMICA DE BÚSQUEDA de CAL-1, sin LLM.

Población 200 · torneo k=3 · elitismo 10 · operadores estructurales · cruza con
reparación de conexidad · baseline AMCS (port fiel del repo público) inyectado en
la población inicial · seeds en las familias donde históricamente caen estas
conjeturas (Wagner 2021 → NMCS/NRPA 2022 → AMCS 2023) · n ∈ [10, 40].

Multi-arranque: N corridas con semillas distintas. Log CSV por generación:
(corrida, gen, best_gap, best_g6, n, evento, epoch). Criterio de éxito (§9):
alguna corrida cruza gap > 0 en minutos/horas de CPU, no días.

Uso:  python calibracion/ga_graphs.py --runs 20 --gens 1000 --out calibracion/runs/ga_log.csv
      (modo estrés de dinámica, sin familias estructurales:  --sin-seeds)
"""
import argparse
import csv
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx

from calibracion.amcs_baseline import amcs
from evaluators.agx_l1_mu import gap_grafo

N_MIN, N_MAX = 10, 40
MUY_MALO = -1e9
TOL_POSITIVO = 1e-9  # las estrellas dan gap=0 EXACTO (§4): sin umbral, el ruido de eigvalsh (~1e-15) da falsos contraejemplos


def norm(G):
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


def fitness(G):
    n = G.number_of_nodes()
    if n < N_MIN or n > N_MAX or not nx.is_connected(G):
        return MUY_MALO
    return gap_grafo(G)


def g6(G):
    return nx.to_graph6_bytes(norm(G), header=False).decode("ascii").strip()


# ------------------------- seeds estructurales (§9): aquí mueren estas conjeturas
def _estrella(rng, n):
    return nx.star_graph(n - 1)

def _camino(rng, n):
    return nx.path_graph(n)

def _cometa(rng, n):                      # estrella + cola
    t = rng.randint(2, n - 4)
    G = nx.star_graph(n - t - 1)
    prev = 0
    for k in range(t):
        G.add_edge(prev, n - t + k)
        prev = n - t + k
    return G

def _dtc(rng, n):                         # cometa de doble cola DTC(n,p,q)
    p = rng.randint(1, max(1, (n - 6) // 2))
    q = rng.randint(1, max(1, n - 6 - p))
    centro = 0
    G = nx.star_graph(n - p - q - 1)
    sig = n - p - q
    prev = centro
    for _ in range(p):
        G.add_edge(prev, sig); prev = sig; sig += 1
    prev = centro
    for _ in range(q):
        G.add_edge(prev, sig); prev = sig; sig += 1
    return G

def _lollipop(rng, n):                    # K_g + camino
    g = rng.randint(3, max(3, n // 2))
    return nx.lollipop_graph(g, n - g)

def _turnip(rng, n):                      # ciclo impar g + hojas colgadas de un vértice
    g = rng.choice([x for x in range(3, min(n, 12), 2)])
    G = nx.cycle_graph(g)
    for k in range(n - g):
        G.add_edge(0, g + k)
    return G

def _kite(rng, n):                        # K_ω + camino pendiente
    w = rng.randint(3, min(8, n - 2))
    G = nx.complete_graph(w)
    prev = 0
    for k in range(n - w):
        G.add_edge(prev, w + k); prev = w + k
    return G

def _dos_estrellas(rng, n):               # T(2,b): centros de dos estrellas a un vértice nuevo
    a = rng.randint(3, n - 5)
    b = n - 1 - a
    G = nx.star_graph(a - 1)
    off = a
    G.add_edges_from((off, off + k) for k in range(1, b))
    nuevo = n - 1
    G.add_edge(0, nuevo); G.add_edge(off, nuevo)
    return G

def _peine1(rng, n):                      # espina P_k con una hoja por vértice
    k = n // 2
    G = nx.path_graph(k)
    for v in range(k):
        if G.number_of_nodes() < n:
            G.add_edge(v, k + v)
    return G

def _peine2(rng, n):                      # espina P_k con pata de largo 2 por vértice
    k = max(2, n // 3)
    G = nx.path_graph(k)
    sig = k
    for v in range(k):
        if sig + 1 < n:
            G.add_edge(v, sig); G.add_edge(sig, sig + 1); sig += 2
    return G

FAMILIAS = [_estrella, _camino, _cometa, _dtc, _lollipop, _turnip, _kite,
            _dos_estrellas, _peine1, _peine2]


def semilla_estructural(rng):
    n = rng.randint(N_MIN, N_MAX)
    G = norm(rng.choice(FAMILIAS)(rng, n))
    return G if nx.is_connected(G) else nx.path_graph(n)


# ------------------------- operadores de mutación (§9)
def op_add_edge(G, rng):
    no_aristas = list(nx.non_edges(G))
    if no_aristas:
        G.add_edge(*rng.choice(no_aristas))

def op_remove_edge_conexo(G, rng):
    aristas = list(G.edges())
    rng.shuffle(aristas)
    for e in aristas[:8]:
        G.remove_edge(*e)
        if nx.is_connected(G):
            return
        G.add_edge(*e)

def op_rewire(G, rng):
    op_remove_edge_conexo(G, rng)
    op_add_edge(G, rng)

def op_graft_camino(G, rng):
    largo = rng.randint(1, 4)
    base = rng.choice(list(G.nodes()))
    for _ in range(min(largo, N_MAX - G.number_of_nodes())):
        nuevo = G.number_of_nodes()
        G.add_edge(base, nuevo)
        base = nuevo

def op_hoja(G, rng):
    if G.number_of_nodes() < N_MAX:
        G.add_edge(rng.choice(list(G.nodes())), G.number_of_nodes())

def op_subdividir(G, rng):
    if G.number_of_nodes() < N_MAX:
        u, v = rng.choice(list(G.edges()))
        n = G.number_of_nodes()
        G.remove_edge(u, v); G.add_edge(u, n); G.add_edge(n, v)

def op_podar_hoja(G, rng):
    hojas = [v for v in G.nodes() if G.degree(v) == 1]
    if hojas and G.number_of_nodes() > N_MIN:
        G.remove_node(rng.choice(hojas))

OPERADORES = [op_add_edge, op_remove_edge_conexo, op_rewire, op_graft_camino,
              op_hoja, op_subdividir, op_podar_hoja]


def mutar(G, rng):
    H = G.copy()
    rng.choice(OPERADORES)(H, rng)
    H = norm(H)
    return H if H.number_of_nodes() >= 3 and nx.is_connected(H) else G.copy()


def cruza_de_padres(p1, p2, rng):
    """Unión parcial de listas de aristas + reparación de conexidad (§9)."""
    n = max(p1.number_of_nodes(), p2.number_of_nodes())
    H = nx.Graph()
    H.add_nodes_from(range(n))
    H.add_edges_from(p1.edges())
    H.add_edges_from(e for e in p2.edges() if rng.random() < 0.5)
    comps = [list(c) for c in nx.connected_components(H)]
    while len(comps) > 1:  # reparación: coser componentes
        a, b = rng.sample(range(len(comps)), 2)
        H.add_edge(rng.choice(comps[a]), rng.choice(comps[b]))
        comps = [list(c) for c in nx.connected_components(H)]
    return norm(H)


def torneo(pob, fits, rng, k=3):
    idx = max(rng.sample(range(len(pob)), k), key=lambda i: fits[i])
    return pob[idx]


def corrida(id_corrida, semilla, gens, tam_pob, elite, escritor, archivo_csv, presupuesto_amcs,
            sin_seeds=False):
    rng = random.Random(semilla)
    if sin_seeds:  # modo estrés de dinámica: solo árboles aleatorios, sin familias del §9
        pob = [norm(nx.random_labeled_tree(rng.randint(N_MIN, N_MAX),
                                           seed=rng.randint(0, 10**9)))
               for _ in range(tam_pob - 1)]
    else:
        pob = [semilla_estructural(rng) for _ in range(tam_pob - 1)]
    # organismo baseline OBLIGATORIO (§9): búsqueda local estilo AMCS acotada a n<=40
    base = amcs(gap_grafo, grafo_inicial=nx.random_labeled_tree(5, seed=semilla),
                max_depth=presupuesto_amcs[0], max_level=presupuesto_amcs[1],
                solo_arboles=True, rng=rng, max_n=N_MAX)
    pob.append(norm(base))
    fits = [fitness(G) for G in pob]

    for gen in range(gens):
        orden = sorted(range(len(pob)), key=lambda i: fits[i], reverse=True)
        mejor, mejor_fit = pob[orden[0]], fits[orden[0]]
        evento = "contraejemplo" if mejor_fit > TOL_POSITIVO else "gen"
        escritor.writerow([id_corrida, gen, f"{mejor_fit:.10f}", g6(mejor),
                           mejor.number_of_nodes(), evento, int(time.time())])
        archivo_csv.flush()
        if mejor_fit > TOL_POSITIVO:
            print(f"[corrida {id_corrida}] CONTRAEJEMPLO en gen {gen}: gap={mejor_fit:.8f} "
                  f"n={mejor.number_of_nodes()} g6={g6(mejor)}", flush=True)
            return True
        nueva = [pob[i].copy() for i in orden[:elite]]
        while len(nueva) < tam_pob:
            if rng.random() < 0.3:
                hijo = cruza_de_padres(torneo(pob, fits, rng), torneo(pob, fits, rng), rng)
            else:
                hijo = mutar(torneo(pob, fits, rng), rng)
            nueva.append(hijo)
        pob = nueva
        fits = [fitness(G) for G in pob]
    print(f"[corrida {id_corrida}] sin contraejemplo tras {gens} gens "
          f"(mejor gap={max(fits):.6f})", flush=True)
    return False


def main():
    ap = argparse.ArgumentParser(description="GA de calibración CAL-1 (§9)")
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--gens", type=int, default=1000)
    ap.add_argument("--pop", type=int, default=200)
    ap.add_argument("--elite", type=int, default=10)
    ap.add_argument("--semilla-base", type=int, default=20260705)
    ap.add_argument("--amcs-depth", type=int, default=3)
    ap.add_argument("--amcs-level", type=int, default=2)
    ap.add_argument("--sin-seeds", action="store_true",
                    help="población inicial de árboles aleatorios (estrés de dinámica, §10.3)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "runs", "ga_log.csv"))
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    nuevo = not os.path.exists(args.out)
    exitos = 0
    with open(args.out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["corrida", "gen", "best_gap", "best_g6", "n", "evento", "epoch"])
        t0 = time.time()
        for r in range(args.runs):
            print(f"=== corrida {r + 1}/{args.runs} (semilla {args.semilla_base + r}) ===", flush=True)
            if corrida(r, args.semilla_base + r, args.gens, args.pop, args.elite, w, f,
                       (args.amcs_depth, args.amcs_level), sin_seeds=args.sin_seeds):
                exitos += 1
        print(f"[fin] {exitos}/{args.runs} corridas con gap>0 en {time.time() - t0:.0f} s; "
              f"log: {args.out}", flush=True)


if __name__ == "__main__":
    main()

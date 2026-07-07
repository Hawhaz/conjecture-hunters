#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ENJAMBRE — satura el nodo (99% CPU/GPU) cazando en paralelo las 20 conjeturas,
con GEMMA como operador de mutacion (arquitectura AlphaEvolve).

Un worker por core hace busqueda evolutiva por carril: parte de la familia extremal
reclamada y propone una EDICION del grafo. El proponente es:
  * GEMMA (LLM en AMD via vLLM, o local via Ollama, o Fireworks) si --gemma y hay
    endpoint (env CONJ_API_BASE/CONJ_MODEL/CONJ_API_KEY) — el "cerebro".
  * busqueda local rapida (flip/hoja) como fallback y para saturar cores.
El fitness es el evaluador EXACTO; un gap>0 en un carril ABIERTO = CANDIDATO ->
ledger durable (fsync) + certificado + alerta. AlphaEvolve-style: el LLM propone,
la aritmetica exacta juzga (no-jugable).

Honesto: no "resuelve TODAS" las conjeturas — la mayoria abiertas son ciertas. El
sistema las ATACA masivamente y REFUTA las falsas (como Jia-Song), con certificado.

Uso:
  python orquestador/enjambre.py --minutos 5                    # local, satura cores
  CONJ_API_BASE=http://localhost:8000/v1 CONJ_MODEL=google/gemma-3-4b-it \
    python orquestador/enjambre.py --minutos 240 --gemma        # Gemma en el loop
  python orquestador/enjambre.py --minutos 5 --gemma            # sin endpoint -> fallback local
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
from multiprocessing import Pool, cpu_count

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "retos"))
sys.path.insert(0, os.path.join(REPO, "hallazgos"))

import pack_extra as pe        # noqa: E402
import registro                # noqa: E402

ALL_LANES = list(pe.LANES_EXTRA)
try:
    import pack_conjeturas as pc   # noqa: E402
    ALL_LANES = list(pc.LANES) + ALL_LANES
except Exception as _e:
    print(f"[enjambre] aviso: pack_conjeturas no disponible ({type(_e).__name__}); "
          f"corriendo con {len(ALL_LANES)} carriles de pack_extra")

MARGEN = 1e-5


# ------------------------------------------------------- Gemma (mutador LLM)
def _apply_edit(G, txt):
    """parsea 'ADD u v' / 'DEL u v' que propone Gemma y lo aplica. Testeable."""
    m = re.search(r'(ADD|DEL)\s+(\d+)\s+(\d+)', str(txt).upper())
    if not m:
        return None
    op, u, v = m.group(1), int(m.group(2)), int(m.group(3))
    n = G.number_of_nodes()
    if u == v or u >= n or v >= n:
        return None
    H = G.copy()
    if op == "ADD":
        H.add_edge(u, v)
    elif H.has_edge(u, v):
        H.remove_edge(u, v)
    else:
        return None
    return H


def _gemma_edit(G, nombre, g):
    """pide a Gemma UNA edicion de arista para subir el gap. None si no hay endpoint."""
    base = os.environ.get("CONJ_API_BASE")
    if not base:
        return None
    model = os.environ.get("CONJ_MODEL", "gemma3:4b")
    key = os.environ.get("CONJ_API_KEY", "sk-none")
    n = G.number_of_nodes()
    prompt = (f"Undirected graph, vertices 0..{n-1}, edges={list(G.edges())}. "
              f"Conjecture lane '{nombre}', current score gap={g:.4f} "
              f"(gap>0 means we found a counterexample; maximize it). "
              f"Propose exactly ONE edit. Reply with ONLY 'ADD u v' or 'DEL u v'.")
    body = json.dumps({"model": model, "temperature": 0.9, "max_tokens": 12,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return _apply_edit(G, r["choices"][0]["message"]["content"])
    except Exception:
        return None


# ------------------------------------------------------- semillas + mutacion local
def semillas_de(lane):
    nombre, kind, gap, aplica, extremal, ce = lane
    S = []
    for n in (5, 6, 7, 8, 9, 10, 11, 12, 14, 16):
        if extremal is not None:
            try:
                G = extremal(n)
                if G is not None and G.number_of_nodes() >= 4 and nx.is_connected(G):
                    S.append(G)
            except Exception:
                pass
    for n in (6, 8, 10, 12):
        for gen in (nx.path_graph, lambda k: nx.star_graph(k - 1),
                    lambda k: nx.complete_bipartite_graph(k // 2, k - k // 2),
                    lambda k: nx.cycle_graph(k)):
            try:
                G = gen(n)
                if nx.is_connected(G) and aplica(G):
                    S.append(G)
            except Exception:
                pass
    return [G for G in S if aplica(G)] or [nx.path_graph(6)]


def vecino_local(G, aplica):
    H = G.copy(); n = H.number_of_nodes(); op = random.random()
    try:
        if op < 0.45 and n < 60:
            u, v = random.sample(range(n), 2)
            H.remove_edge(u, v) if H.has_edge(u, v) else H.add_edge(u, v)
        elif op < 0.75 and n < 60:
            H.add_edge(random.randrange(n), n)
        elif n > 5:
            hojas = [x for x in H.nodes() if H.degree(x) == 1]
            if hojas:
                H.remove_node(random.choice(hojas)); H = nx.convert_node_labels_to_integers(H)
    except Exception:
        return None
    if H.number_of_nodes() < 4 or not nx.is_connected(H) or not aplica(H):
        return None
    return H


def vecino(G, lane, g, use_gemma):
    nombre, kind, gap, aplica, extremal, ce = lane
    if use_gemma and random.random() < 0.5:
        H = _gemma_edit(G, nombre, g)
        if H is not None and H.number_of_nodes() >= 4 and nx.is_connected(H) and aplica(H):
            return H  # Gemma propuso algo valido
    return vecino_local(G, aplica)


# ------------------------------------------------------- worker
def worker(args):
    seed, minutos, solo_abiertas, use_gemma = args
    random.seed(seed)
    t_fin = time.time() + minutos * 60
    evals = hits = 0
    lanes = [L for L in ALL_LANES if (L[1] == "abierta" or not solo_abiertas)]
    estado = {L[0]: (random.choice(semillas_de(L)), -1e18) for L in lanes}
    while time.time() < t_fin:
        L = random.choice(lanes)
        nombre, kind, gap, aplica, extremal, ce = L
        G, mejor = estado[nombre]
        H = vecino(G, L, mejor, use_gemma)
        if H is None:
            if random.random() < 0.1:
                estado[nombre] = (random.choice(semillas_de(L)), -1e18)
            continue
        try:
            g = gap(H)
        except Exception:
            continue
        evals += 1
        if g >= mejor or random.random() < 0.05:
            estado[nombre] = (H, g)
        if kind == "abierta" and g > MARGEN:
            try:
                g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(H), header=False).decode().strip()
                registro.registrar_hallazgo(nombre, g6, float(g), n=H.number_of_nodes(),
                                            meta={"worker": seed, "gemma": use_gemma})
                hits += 1
            except Exception:
                pass
    return evals, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutos", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--solo-abiertas", action="store_true")
    ap.add_argument("--gemma", action="store_true", help="Gemma como mutador (env CONJ_API_BASE)")
    args = ap.parse_args()

    W = args.workers or cpu_count()
    endpoint = os.environ.get("CONJ_API_BASE", "(ninguno -> fallback local)")
    print(f"ENJAMBRE: {W} workers (cores={cpu_count()}) · {len(ALL_LANES)} carriles · "
          f"{args.minutos} min · gemma={args.gemma} · endpoint={endpoint}")
    t0 = time.time()
    with Pool(processes=W) as pool:
        res = pool.map(worker, [(1000 + i, args.minutos, args.solo_abiertas, args.gemma)
                                for i in range(W)])
    dt = time.time() - t0
    ev = sum(r[0] for r in res); hits = sum(r[1] for r in res)
    print(f"\nEVALS: {ev:,}  ·  {ev/max(dt,1e-9):,.0f} evals/seg  ·  {W} cores · {dt:.1f}s")
    print(f"CANDIDATOS (carriles abiertos): {hits}  ->  python hallazgos/registro.py --resumen")
    if hits == 0:
        print("Sin candidatos: las abiertas resistieron el barrido en este presupuesto.")


if __name__ == "__main__":
    main()

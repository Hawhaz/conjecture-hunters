#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cosechar.py — Cosecha un dataset SFT (contexto -> delta de aristas que sube el
gap) para especializar gemma-3-4b como OPERADOR DE MUTACION espectral (estilo
PatternBoost / self-improvement) que correra en la MI300X via vLLM.

Idea (self-improvement loop): el orquestador YA funciona end-to-end con el
backend `mock` DETERMINISTA (los operadores estructurales + el evaluador de
paridad Python). Cada mutacion en la que el hijo MEJORA el gap del padre por un
margen es, exactamente, una demostracion supervisada de "dado este grafo y esta
conjetura, este es el movimiento que acerca al contraejemplo". Empaquetamos esas
demostraciones en el MISMO formato de chat que vera la Gemma en vivo:

    system   := texto literal de prompts/system_mutador.md
    user     := plantilla_usuario.md renderizada (via prompts/ollama_cliente.py)
                con el grafo PADRE como LISTA DE ARISTAS en {programa_actual},
                la card de la conjetura en {conjetura}, gap/n reales, y el
                CONTEXTO DE RANGO ORDINAL en {historial_operadores}.
    assistant:= el delta aplicado, en el formato EXACTO que mutador.py::_parsear_delta
                entiende: "add edge (u,v); remove edge (x,y)".

Fuentes de ejemplos (dos curriculos complementarios):
  A. HARVEST evolutivo: corre los operadores estructurales (la ruta mock, sin
     red) sobre semillas de cal1/cal2/cal3 con varias semillas RNG; emite un
     ejemplo por cada mutacion con child_gap > parent_gap + MARGEN.
  B. CURRICULO EXTREMAL (RA2): para cada familia extremal (estrella, cometa,
     cometa-doble-cola, kite, dos-estrellas) a varios n, parte de un grafo mas
     PLANO del mismo n (una estrella o un camino) y emite (contexto -> delta
     hacia el miembro extremal). Le ensena EXPLICITAMENTE los movimientos que
     rompen estas conjeturas, aunque el gap intermedio aun no cruce 0.

El delta se calcula como la diferencia simetrica de conjuntos de aristas
(child.edges triangulo parent.edges) y se VERIFICA reconstruyendo el hijo con
grafos.aplicar_delta sobre el padre: solo se conservan los pares fieles (delta
que, aplicado al padre, reproduce exactamente el hijo normalizado). Asi cada
target es un movimiento legal y ejecutable, no ruido.

Corre SOLO con lo ya instalado (networkx/numpy + el orquestador): NO importa
torch/transformers/peft. Escribe finetune/data/sft_mutador.jsonl, deduplica,
imprime el conteo y un par de lineas de muestra.

Uso:
    python finetune/cosechar.py                 # corpus por defecto (>=1000)
    python finetune/cosechar.py --semillas 0,1,2,3,4,5,6,7 --iters 90
    python finetune/cosechar.py --out finetune/data/sft_mutador.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from typing import Dict, List, Optional, Tuple

# --- raiz del repo al sys.path (para correr como script suelto) --------------
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx  # noqa: E402

from orquestador import grafos as G  # noqa: E402
from orquestador.evaluar import Evaluador  # noqa: E402
from prompts import ollama_cliente as OC  # noqa: E402


# ---------------------------------------------------------------------------
# Cards de conjetura (texto que va en {conjetura}). Resumen de banco_conjeturas.md
# en el mismo estilo que ollama_cliente inserta por carril. Fuente ejecutable:
# evaluators/ (via parity/refs.py). Aqui solo describe la desigualdad + gap +
# pista de familia para condicionar al modelo.
# ---------------------------------------------------------------------------
CARDS: Dict[str, str] = {
    "cal1": (
        "CAL-1 (AutoGraphiX / Aouchiche-Hansen): for every connected graph with "
        "n>=3, lambda_1(G) + mu(G) >= sqrt(n-1) + 1, where lambda_1 is the largest "
        "adjacency eigenvalue and mu is the maximum matching size.\n"
        "gap(G) = (sqrt(n-1) + 1) - (lambda_1 + mu); gap > 0 means counterexample.\n"
        "Extremal family: pure STAR or COMET (star + short tail). In a star "
        "lambda_1 = sqrt(n-1) grows as fast as the bound while mu stays at 1; a "
        "short tail or an unbalanced second branch can push the gap positive. "
        "Good moves: add_leaf (grow the star's leaves), grow a double-tailed comet. "
        "Avoid leaf-to-leaf edges: they raise mu and worsen the gap."
    ),
    "cal2": (
        "CAL-2 (Favaron-Maheo-Sacle / Graffiti II): for every graph, "
        "lambda_2(G) <= Hc(G), where lambda_2 is the second largest adjacency "
        "eigenvalue and Hc(G) = sum over edges uv of 2/(d_u + d_v) is the harmonic "
        "index.\n"
        "gap(G) = lambda_2(G) - Hc(G); gap > 0 means counterexample.\n"
        "Extremal family: TWO STARS joined (the centers of two large stars linked "
        "through a new vertex). Two high-degree hubs create a large positive second "
        "eigenvalue while Hc stays low (most edges are hub-to-leaf, very unequal "
        "degrees). Good move: two_stars_join, then add_leaf to unbalance the two "
        "star sizes."
    ),
    "cal3": (
        "CAL-3 (Aouchiche-Hansen 2016): for every connected graph with n>=4, "
        "pi(G) + partial_{floor(2D/3)}(G) > 0, where pi = min_v t(v)/(n-1) is the "
        "minimum normalized transmission and partial_i is the i-th largest "
        "eigenvalue of the distance matrix (D also denotes the diameter).\n"
        "k = floor(2*diam(G)/3); gap(G) = -(pi(G) + partial_k(G)); gap>0 means "
        "counterexample.\n"
        "Extremal family: a GIANT STAR with two SHORT ASYMMETRIC pendant paths "
        "(the published counterexample is S191 + a P7 tail and a P5 tail, n=203). "
        "The giant star minimizes pi; the two unequal tails move the diameter and "
        "the distance eigenvalue partial_k until the sum turns positive by a tiny "
        "margin. Good move: giant star + graft_pendant_path twice with DIFFERENT "
        "lengths (never two equal tails)."
    ),
}


# ---------------------------------------------------------------------------
# Delta de aristas (formato EXACTO de mutador.py) a partir de padre/hijo.
# ---------------------------------------------------------------------------
def _delta_edges(parent: nx.Graph, child: nx.Graph
                 ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """(agregar, quitar) = diferencia simetrica de aristas child vs parent.

    Trabaja sobre las etiquetas NORMALIZADAS (0..n-1 'sorted') de cada grafo, la
    misma convencion que usa todo el stack. Las aristas se ordenan (u<=v) para
    una representacion estable.
    """
    def eset(g: nx.Graph):
        return {(min(u, v), max(u, v)) for u, v in G.norm(g).edges()}

    pe, ce = eset(parent), eset(child)
    agregar = sorted(ce - pe)   # aristas nuevas en el hijo
    quitar = sorted(pe - ce)    # aristas del padre que el hijo ya no tiene
    return agregar, quitar


def _fmt_delta(agregar: List[Tuple[int, int]], quitar: List[Tuple[int, int]]) -> str:
    """Serializa el delta al formato que mutador.py::_parsear_delta entiende.

    'add edge (u,v); add edge (u,w); remove edge (x,y)'. Primero los add, luego
    los remove (el parser es orden-agnostico, pero mantenemos un orden estable).
    """
    partes = ["add edge (%d,%d)" % (u, v) for (u, v) in agregar]
    partes += ["remove edge (%d,%d)" % (u, v) for (u, v) in quitar]
    return "; ".join(partes)


def _delta_fiel(parent: nx.Graph, child: nx.Graph
                ) -> Optional[Tuple[str, int, int]]:
    """Devuelve (texto_delta, n_add, n_del) SOLO si el delta reconstruye al hijo.

    Verifica el round-trip: aplica el delta al padre con grafos.aplicar_delta y
    comprueba que el g6 normalizado del resultado coincide con el g6 del hijo.
    Devuelve None si el delta esta vacio (grafos iguales) o si NO reconstruye el
    hijo (p. ej. por relabeling tras un prune que desplaza indices). Asi el
    target SFT es siempre un movimiento legal y ejecutable por mutador.py.
    """
    agregar, quitar = _delta_edges(parent, child)
    if not agregar and not quitar:
        return None
    try:
        recon = G.aplicar_delta(G.norm(parent), agregar=agregar, quitar=quitar)
    except Exception:
        return None
    if G.g6_of(recon) != G.g6_of(child):
        return None
    return _fmt_delta(agregar, quitar), len(agregar), len(quitar)


# ---------------------------------------------------------------------------
# Render del ejemplo de chat (system/user/assistant) en el formato del contrato.
# ---------------------------------------------------------------------------
_SYSTEM_TXT = OC.cargar_system()  # texto literal de system_mutador.md (una vez)


def _lista_aristas_programa(g: nx.Graph) -> str:
    """El grafo PADRE como bloque de lista de aristas (una por linea 'u v').

    Va en el slot {programa_actual}. Refleja el 'programa que imprime las
    aristas' del contrato del mutador, pero congelado a este grafo concreto, y
    coincide con la representacion edge-list que el mutador live ya usa.
    """
    lineas = ["# parent graph: edge list (one edge per line: u v), n=%d"
              % g.number_of_nodes()]
    for u, v in sorted(G.norm(g).edges()):
        lineas.append("%d %d" % (u, v))
    return "\n".join(lineas)


def _contexto_rango(rank_idx: int, rank_tot: int, gap: float, mejor_gap: float
                    ) -> str:
    """Contexto de RANGO ORDINAL para {historial_operadores} (no floats crudos).

    Le decimos al modelo en que posicion ordinal esta el grafo padre dentro del
    pool de elites (peor..mejor) y que aun hay margen: mismo principio que el
    few-shot ranqueado del mutador live (un 4B razona sobre rango, no sobre
    floats). Incluimos el signo del gap (aun negativo => no es contraejemplo).
    """
    signo = "positive (already a counterexample)" if gap > 0 else "negative (not yet)"
    return (
        "Ordinal rank of this parent in the current elite pool: %d of %d "
        "(1 = worst, %d = best/closest to a counterexample). Its gap sign is %s. "
        "Propose the single small move that most raises the rank."
        % (rank_idx, rank_tot, rank_tot, signo)
    )


def construir_ejemplo(conj: str, parent: nx.Graph, child: nx.Graph,
                      gap_padre: float, mejor_gap: float,
                      rank_idx: int, rank_tot: int) -> Optional[dict]:
    """Un ejemplo SFT {"messages":[system,user,assistant]} o None si no es fiel."""
    fiel = _delta_fiel(parent, child)
    if fiel is None:
        return None
    texto_delta, _na, _nd = fiel
    user_txt = OC.render_usuario(
        programa=_lista_aristas_programa(parent),
        conjetura=CARDS[conj],
        gap=gap_padre,
        n=parent.number_of_nodes(),
        historial_operadores=_contexto_rango(rank_idx, rank_tot, gap_padre, mejor_gap),
    )
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM_TXT},
            {"role": "user", "content": user_txt},
            {"role": "assistant", "content": texto_delta},
        ]
    }


# ---------------------------------------------------------------------------
# Fuente A: harvest evolutivo (operadores estructurales / ruta mock).
# ---------------------------------------------------------------------------
def cosechar_harvest(conjeturas: List[str], semillas_rng: List[int],
                     iters: int, margen: float, verbose: bool) -> List[dict]:
    """Corre operadores estructurales sobre semillas y cosecha mutaciones que
    suben el gap por `margen`. Emula el ciclo del orquestador (mock) pero
    guardando el par (padre, hijo) de cada mejora como demostracion SFT.
    """
    ejemplos: List[dict] = []
    for conj in conjeturas:
        ev = Evaluador(conj, forzar_python=True)  # paridad, determinista, sin Rust
        ops = G.operadores(trees_only=False)
        for sem in semillas_rng:
            rng = random.Random(1000 + sem)
            # pool de semillas de esta conjetura (incluye la familia extremal)
            sems = G.semillas(conj, rng, cantidad=8)
            g6s = list(dict.fromkeys(G.g6_of(s) for s in sems))
            gaps = ev.evaluar(g6s)
            # poblacion viva: lista de (g6, gap), ordenable por gap para el rango
            poblacion: List[Tuple[str, float]] = [
                (s, gaps[s]) for s in g6s if s in gaps]
            if not poblacion:
                continue
            mejor = max(g for _, g in poblacion)
            for _ in range(iters):
                if not poblacion:
                    break
                # elige un padre al azar sesgado a los mejores (novelty-lite)
                poblacion.sort(key=lambda t: t[1])
                rank_tot = len(poblacion)
                # sesga: 60% del mejor tercio, 40% uniforme
                if rng.random() < 0.6 and rank_tot >= 3:
                    idx = rng.randrange(max(1, rank_tot - rank_tot // 3), rank_tot)
                else:
                    idx = rng.randrange(rank_tot)
                padre_g6, gap_padre = poblacion[idx]
                parent = G.from_g6(padre_g6)
                op = ops[rng.randrange(len(ops))]
                child = G.aplicar_operador(op, parent, rng)
                if child is None or not G.valido(child, requiere_conexo=True):
                    continue
                child_g6 = G.g6_of(child)
                gap_hijo = ev.gap(child_g6)
                if gap_hijo == float("-inf"):
                    continue
                # criterio de cosecha: mejora estricta por margen
                if gap_hijo > gap_padre + margen:
                    ej = construir_ejemplo(
                        conj, parent, child, gap_padre, mejor,
                        rank_idx=idx + 1, rank_tot=rank_tot)
                    if ej is not None:
                        ejemplos.append(ej)
                    # inserta el hijo en la poblacion (self-improvement)
                    if all(child_g6 != g for g, _ in poblacion):
                        poblacion.append((child_g6, gap_hijo))
                        mejor = max(mejor, gap_hijo)
        if verbose:
            print("[harvest] %s: acumulado %d ejemplos" % (conj, len(ejemplos)),
                  flush=True)
    return ejemplos


# ---------------------------------------------------------------------------
# Fuente B: curriculo extremal (grafo plano -> miembro de la familia extremal).
# ---------------------------------------------------------------------------
# (familia, constructor n->grafo). Firmas replicadas de grafos.py.
_FAMILIAS_CURRIC = [
    ("star", G._estrella),
    ("comet", G._cometa),
    ("double_tailed_comet", G._dtc),
    ("kite", G._kite),
    ("two_stars", G._dos_estrellas),
]


def _paso_hacia(parent: nx.Graph, target: nx.Graph, rng) -> Optional[nx.Graph]:
    """Un PASO pequeno del padre hacia el target: aplica el subconjunto de aristas
    del delta que empuja hacia el target sin romper conectividad ni salir de banda.

    Estrategia: prioriza AGREGAR una arista que el target tiene y el padre no (si
    ambos tienen el mismo n); si no hay, subdivide/agrega hoja generico. Devuelve
    un hijo mas cercano al target, o None. Genera pasos INTERMEDIOS del camino
    plano->extremal (cada paso es un ejemplo de "movimiento hacia la familia").
    """
    pn, tn = parent.number_of_nodes(), target.number_of_nodes()
    if pn != tn:
        return None
    agregar, quitar = _delta_edges(parent, target)
    rng.shuffle(agregar)
    rng.shuffle(quitar)
    # intenta una sola arista a agregar del delta (movimiento minimo hacia target)
    for (u, v) in agregar:
        try:
            hijo = G.aplicar_delta(G.norm(parent), agregar=[(u, v)], quitar=[])
        except Exception:
            continue
        if G.valido(hijo, requiere_conexo=True) and G.g6_of(hijo) != G.g6_of(parent):
            return hijo
    # si no hubo add util, intenta quitar una del padre que el target no tiene,
    # solo si mantiene conectividad (evita desconectar)
    for (u, v) in quitar:
        try:
            hijo = G.aplicar_delta(G.norm(parent), agregar=[], quitar=[(u, v)])
        except Exception:
            continue
        if G.valido(hijo, requiere_conexo=True) and G.g6_of(hijo) != G.g6_of(parent):
            return hijo
    return None


def cosechar_curriculo(conjeturas: List[str], ns: List[int],
                       verbose: bool) -> List[dict]:
    """Camino plano->extremal por familia y n: cada paso minimo es un ejemplo.

    Para cada conjetura y cada n, arranca de un grafo PLANO (estrella o camino)
    y avanza paso a paso hacia el miembro extremal de cada familia, emitiendo el
    delta de cada paso. El gap del padre se calcula para condicionar el prompt
    (aunque el objetivo es ENSENAR el movimiento estructural, no cruzar 0).
    """
    ejemplos: List[dict] = []
    for conj in conjeturas:
        ev = Evaluador(conj, forzar_python=True)
        rng = random.Random(4242)
        for n in ns:
            # arranques planos: estrella y camino del mismo n
            arranques = []
            try:
                arranques.append(G.norm(G._estrella(n)))
            except Exception:
                pass
            try:
                arranques.append(G.norm(G._camino(n)))
            except Exception:
                pass
            for fam_nombre, ctor in _FAMILIAS_CURRIC:
                try:
                    target = G.norm(ctor(n))
                except Exception:
                    continue
                if not G.valido(target, requiere_conexo=True):
                    continue
                for arranque in arranques:
                    if G.g6_of(arranque) == G.g6_of(target):
                        continue
                    parent = arranque
                    # avanza hasta ~n pasos hacia el target (camino de morphing)
                    for _paso in range(n + 2):
                        child = _paso_hacia(parent, target, rng)
                        if child is None:
                            break
                        gap_padre = ev.gap(G.g6_of(parent))
                        if gap_padre == float("-inf"):
                            gap_padre = -9.9
                        ej = construir_ejemplo(
                            conj, parent, child, gap_padre, mejor_gap=gap_padre,
                            rank_idx=1, rank_tot=1)
                        if ej is not None:
                            ejemplos.append(ej)
                        if G.g6_of(child) == G.g6_of(target):
                            break
                        parent = child
        if verbose:
            print("[curriculo] %s: acumulado %d ejemplos" % (conj, len(ejemplos)),
                  flush=True)
    return ejemplos


# ---------------------------------------------------------------------------
# Dedupe + escritura.
# ---------------------------------------------------------------------------
def _clave(ej: dict) -> str:
    """Clave de dedupe: (user, assistant). Dos ejemplos con el mismo contexto y
    el mismo target son redundantes (mismo par grafo->delta)."""
    msgs = ej["messages"]
    return msgs[1]["content"] + "\x00" + msgs[2]["content"]


def deduplicar(ejemplos: List[dict]) -> List[dict]:
    vistos = set()
    out = []
    for ej in ejemplos:
        k = _clave(ej)
        if k in vistos:
            continue
        vistos.add(k)
        out.append(ej)
    return out


def escribir_jsonl(ejemplos: List[dict], ruta: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        for ej in ejemplos:
            f.write(json.dumps(ej, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parsear_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Cosecha SFT (contexto->delta que sube el gap) para gemma-3-4b "
                    "como operador de mutacion (PatternBoost / self-improvement).")
    ap.add_argument("--conjeturas", default="cal1,cal2,cal3",
                    help="lista separada por comas")
    ap.add_argument("--semillas", default="0,1,2,3,4,5,6,7,8,9,10,11",
                    help="semillas RNG del harvest (mas semillas = mas datos)")
    ap.add_argument("--iters", type=int, default=120,
                    help="iteraciones de mutacion por (conjetura,semilla)")
    ap.add_argument("--margen", type=float, default=1e-6,
                    help="mejora minima child_gap-parent_gap para cosechar")
    ap.add_argument("--ns-curriculo", default="12,16,20,24,28,32,36,40",
                    help="tamanos n del curriculo extremal")
    ap.add_argument("--sin-curriculo", action="store_true",
                    help="omite la fuente B (curriculo extremal)")
    ap.add_argument("--sin-harvest", action="store_true",
                    help="omite la fuente A (harvest evolutivo)")
    ap.add_argument("--out", default=None,
                    help="ruta JSONL (default finetune/data/sft_mutador.jsonl)")
    ap.add_argument("--silencioso", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parsear_args(argv)
    verbose = not args.silencioso
    conjeturas = [c.strip() for c in args.conjeturas.split(",")
                  if c.strip() in CARDS]
    semillas_rng = [int(x) for x in args.semillas.split(",") if x.strip()]
    ns = [int(x) for x in args.ns_curriculo.split(",") if x.strip()]
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "data", "sft_mutador.jsonl")

    ejemplos: List[dict] = []
    if not args.sin_harvest:
        ejemplos += cosechar_harvest(
            conjeturas, semillas_rng, args.iters, args.margen, verbose)
    if not args.sin_curriculo:
        ejemplos += cosechar_curriculo(conjeturas, ns, verbose)

    antes = len(ejemplos)
    ejemplos = deduplicar(ejemplos)
    escribir_jsonl(ejemplos, out)

    print("=" * 66)
    print("[cosechar] ejemplos crudos: %d  ->  tras dedupe: %d"
          % (antes, len(ejemplos)))
    print("[cosechar] escrito: %s" % out)
    if len(ejemplos) < 1000:
        print("[cosechar] AVISO: <1000 ejemplos; sube --semillas/--iters o "
              "amplia --ns-curriculo para mas cobertura.")
    # muestra un par de lineas (recortadas) para inspeccion rapida
    print("-" * 66)
    for ej in ejemplos[:2]:
        u = ej["messages"][1]["content"]
        a = ej["messages"][2]["content"]
        u_corto = (u[:220] + " ...[truncado]") if len(u) > 220 else u
        print("SAMPLE assistant(delta): %s" % a)
        print("SAMPLE user(inicio)    : %s" % u_corto.replace("\n", "\\n"))
        print("-" * 66)
    return 0


if __name__ == "__main__":
    sys.exit(main())

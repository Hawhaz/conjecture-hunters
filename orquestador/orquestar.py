#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orquestador evolutivo caza-contraejemplos — el bucle principal.

Junta la cascada de evaluacion (T1 validez barata -> T2 Rust gap continuo en
LOTE -> T3 certificado exacto SOLO sobre gap>1e-9), islas + archivo MAP-Elites
con hard-reset periodico, bandit Thompson descontado sobre (conjetura x
operador), muestreo de padres ponderado por novedad + rechazo de duplicados
(WL-hash), y la capa de mutacion (mock determinista / ollama opt-in).

Cada componente mapea a un hallazgo de investigacion; ver DISENO.md. El gap
CONTINUO ordena todo; el CONTRAEJEMPLO solo se declara cuando T3 lo certifica.

Log CSV (mismo esquema que calibracion/ga_graphs.py para reusar el dashboard):
    corrida,gen,best_gap,best_g6,n,evento,epoch

Uso:
    python orquestador/orquestar.py --conjeturas cal1,cal2,cal3 --iters 400 \
        --llm mock --islas 5 [--trees-only] --semilla 7 \
        --out calibracion/runs/orq_log.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# raiz del repo al sys.path (para correr como script suelto: python orquestar.py)
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx  # noqa: E402

from orquestador import grafos as G  # noqa: E402
from orquestador.archivo import Archipielago, Elite, Isla  # noqa: E402
from orquestador.bandit import Bandit  # noqa: E402
from orquestador.evaluar import TOL_POSITIVO, Evaluador  # noqa: E402
from orquestador.mutador import Mutador  # noqa: E402

try:
    from orquestador.certificar import certificar
except Exception:  # certificar depende de sympy/mpmath; nunca debe romper import
    certificar = None  # type: ignore


CSV_HEADER = ["corrida", "gen", "best_gap", "best_g6", "n", "evento", "epoch"]


# ---------------------------------------------------------------------------
# Shaping secundario de CAL-3 (decision 9): SOLO desempate, jamas reemplaza el
# gap real ni la clasificacion T3. Premia diametro D acercandose a la banda
# donde k=floor(2D/3) sube (el flooring aplana el gradiente del gap).
# ---------------------------------------------------------------------------
def shaping_cal3(g6: str) -> float:
    """Termino de forma minusculo (escala 1e-6): cercania de 2D a un multiplo

    de 3. Cuando 2D cruza un multiplo de 3, k=floor(2D/3) incrementa y el gap de
    CAL-3 puede dar un salto. Este termino es un gradiente suave hacia esos
    cruces; solo rompe empates entre elites de igual gap real.
    """
    try:
        graf = G.from_g6(g6)
        if not nx.is_connected(graf):
            return 0.0
        D = nx.diameter(graf)
        resto = (2 * D) % 3
        cercania = (3 - resto) % 3  # 0 si resto==0, si no cuanto falta al cruce
        return 1.0 / (1.0 + cercania) * 1e-6
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Muestreo de padres ponderado por novedad (decision 6, ShinkaEvolve):
#   w_i = sigmoid(lambda*(gap_i - median_gap)) * 1/(1 + n_offspring_i)
# ---------------------------------------------------------------------------
def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def muestrear_padre(isla: Isla, rng, lam: float = 4.0) -> Optional[Elite]:
    """Elige un elite como padre con peso novelty (gap alto + poco explotado)."""
    elites = isla.elites()
    if not elites:
        return None
    gaps = sorted(e.gap for e in elites)
    m = len(gaps)
    mediana = gaps[m // 2] if m % 2 == 1 else 0.5 * (gaps[m // 2 - 1] + gaps[m // 2])
    pesos = []
    for e in elites:
        w = _sigmoid(lam * (e.gap - mediana)) / (1.0 + e.n_offspring)
        pesos.append(max(w, 1e-9))
    total = sum(pesos)
    r = rng.random() * total
    acc = 0.0
    for e, w in zip(elites, pesos):
        acc += w
        if r <= acc:
            return e
    return elites[-1]


# ---------------------------------------------------------------------------
# Resultado de una corrida (para tests y reporte).
# ---------------------------------------------------------------------------
@dataclass
class Resultado:
    conj: str
    best_gap: float
    best_g6: Optional[str]
    best_n: Optional[int]
    certificado: bool
    margen_cert: Optional[str]
    metodo_cert: Optional[str]
    total_celdas: int
    historia_best: List[float]  # best_gap tras cada generacion (no-decreciente)
    n_certificados: int
    bandit_S: Dict
    bandit_F: Dict


# ---------------------------------------------------------------------------
# Bucle principal por conjetura.
# ---------------------------------------------------------------------------
def orquestar(conjeturas: List[str],
              iters: int,
              llm: str = "mock",
              islas: int = 5,
              trees_only: bool = False,
              semilla: int = 7,
              reset_cada: int = 40,
              semillas_por_isla: int = 6,
              out: Optional[str] = None,
              forzar_python_eval: bool = False,
              cert_al_vuelo: bool = True,
              verbose: bool = True) -> Dict[str, "Resultado"]:
    """Corre el orquestador para cada conjetura. Devuelve {conj: Resultado}.

    Parametros clave (CLI):
      iters : iteraciones (mutaciones) TOTALES por conjetura.
      llm   : 'mock' (CI, determinista) | 'ollama' (opt-in, con fallback).
      islas : numero de islas del archipielago.
      trees_only : restringe a operadores de arbol (decision 5).
      semilla : semilla RNG global (reproducibilidad).
      forzar_python_eval : usa el oraculo Python en vez del binario Rust (CI /
        plataformas sin el .exe). En Windows con el binario, dejar en False.
      cert_al_vuelo : corre T3 sobre candidatos gap>tol durante la corrida.
    """
    rng = random.Random(semilla)
    resultados: Dict[str, Resultado] = {}

    escritor = None
    fout = None
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        nuevo = not os.path.exists(out) or os.path.getsize(out) == 0
        fout = open(out, "a", newline="", encoding="utf-8")
        escritor = csv.writer(fout)
        if nuevo:
            escritor.writerow(CSV_HEADER)

    ops = G.operadores(trees_only)

    try:
        for ci, conj in enumerate(conjeturas):
            res = _corrida_conjetura(
                conj=conj, ci=ci, iters=iters, llm=llm, islas=islas,
                ops=ops, trees_only=trees_only, rng=rng, reset_cada=reset_cada,
                semillas_por_isla=semillas_por_isla, escritor=escritor,
                forzar_python_eval=forzar_python_eval,
                cert_al_vuelo=cert_al_vuelo, verbose=verbose)
            resultados[conj] = res
            if fout:
                fout.flush()
    finally:
        if fout:
            fout.close()
    return resultados


def _corrida_conjetura(conj, ci, iters, llm, islas, ops, trees_only, rng,
                       reset_cada, semillas_por_isla, escritor,
                       forzar_python_eval, cert_al_vuelo, verbose) -> "Resultado":
    conj = conj.lower().strip()
    evaluador = Evaluador(conj, forzar_python=forzar_python_eval)
    mutador = Mutador(backend=llm, trees_only=trees_only)
    bandit = Bandit([conj], ops, gamma=0.99)
    arc = Archipielago(n_islas=islas, reset_cada=reset_cada)

    # --- semillas: evalua en LOTE y siembra el archipielago -----------------
    todas: List[nx.Graph] = []
    for _ in range(islas):
        todas.extend(G.semillas(conj, rng, semillas_por_isla))
    g6_semillas = list(dict.fromkeys(G.g6_of(s) for s in todas))  # unicos, orden
    gaps0 = evaluador.evaluar(g6_semillas)
    pares0 = [(s, gaps0.get(s, float("-inf"))) for s in g6_semillas
              if s in gaps0]
    arc.sembrar(pares0)

    historia: List[float] = []
    best_g6: Optional[str] = None
    best_gap = float("-inf")
    best_n: Optional[int] = None
    # estado de certificacion (dict para que la closure lo mute)
    cstate = {"certificado": False, "margen": None, "metodo": None, "n": 0}

    def registrar(gen: int, evento: str):
        if escritor is not None:
            escritor.writerow([ci, gen, "%.10f" % best_gap,
                               best_g6 if best_g6 else "",
                               best_n if best_n else 0, evento,
                               int(time.time())])

    def intentar_certificar(g6: str, gap: float) -> bool:
        """T3 sobre un candidato (gap>tol). Actualiza cstate; True si certifico.

        Se llama sobre el best inicial de semillas Y sobre cada nuevo best del
        bucle: un contraejemplo ya presente en las semillas NO debe pasar
        desapercibido (p. ej. --trees-only puede no superar la semilla y aun
        asi la semilla ES un contraejemplo).
        """
        if not (cert_al_vuelo and certificar is not None
                and evaluador.es_candidato(gap)):
            return False
        cert = certificar(g6, conj)
        if cert.get("certificado"):
            cstate["certificado"] = True
            cstate["n"] += 1
            cstate["margen"] = str(cert.get("margen"))
            cstate["metodo"] = str(cert.get("metodo"))
            if verbose:
                print("  [CERTIFICADO] %s gap=%.8f g6=%s margen=%s metodo=%s"
                      % (conj, gap, g6, cstate["margen"], cstate["metodo"]),
                      flush=True)
            return True
        return False

    # inicializa best desde las semillas y CERTIFICA si ya es contraejemplo
    mg = arc.mejor_global()
    evento0 = "seed"
    if mg is not None:
        best_gap, best_g6, best_n = mg.gap, mg.g6, mg.n
        if intentar_certificar(best_g6, best_gap):
            evento0 = "contraejemplo"
    historia.append(best_gap)
    registrar(0, evento0)

    # --- bucle evolutivo ----------------------------------------------------
    for it in range(1, iters + 1):
        # elige isla (round-robin) y padre (novelty-weighted)
        isla = arc.islas[it % len(arc.islas)]
        padre = muestrear_padre(isla, rng)
        if padre is None:
            # isla vacia (tras reset degenerado): resiembra minima
            s = G.g6_of(G.semillas(conj, rng, 1)[0])
            gs = evaluador.evaluar([s])
            isla.insertar(s, gs.get(s, float("-inf")))
            historia.append(best_gap)
            continue

        # bandit elige operador; mutamos (mock) o pedimos delta (ollama)
        arm = bandit.seleccionar(rng, conj=conj)
        isla.marcar_padre(padre.g6)
        hijo_g6, _meta = mutador.mutar(padre.g6, arm, isla, rng)

        evento_gen = "gen"
        recompensa = 0
        if hijo_g6 is not None and G.valido(G.from_g6(hijo_g6),
                                            requiere_conexo=True):
            # T2: gap continuo (lote de 1; el batching real se aprovecha en las
            # semillas y podria ampliarse a colas de candidatos por generacion).
            gap_hijo = evaluador.gap(hijo_g6)
            if gap_hijo > float("-inf"):
                shp = shaping_cal3(hijo_g6) if conj == "cal3" else 0.0
                evento_frontera = isla.insertar(hijo_g6, gap_hijo, shaping=shp)
                if evento_frontera in ("nueva_celda", "mejora_celda"):
                    recompensa = 1  # avanzo la frontera de la isla (decision 4)
                # actualiza best global (por gap REAL) y certifica (T3) si el
                # nuevo best es candidato (gap>tol).
                if gap_hijo > best_gap:
                    best_gap, best_g6, best_n = gap_hijo, hijo_g6, \
                        G.from_g6(hijo_g6).number_of_nodes()
                    if intentar_certificar(hijo_g6, gap_hijo):
                        evento_gen = "contraejemplo"
        bandit.actualizar(arm, recompensa)

        # hard-reset periodico de la peor mitad (decision 3)
        if arc.reset_cada > 0 and it % arc.reset_cada == 0:
            arc.reset_peor_mitad(rng)

        historia.append(best_gap)
        registrar(it, evento_gen)

    if verbose:
        estado = "CERTIFICADO" if cstate["certificado"] else "sin certificar"
        print("[%s] fin: best_gap=%.8f n=%s celdas=%d (%s)"
              % (conj, best_gap, best_n, arc.total_celdas(), estado), flush=True)

    return Resultado(
        conj=conj, best_gap=best_gap, best_g6=best_g6, best_n=best_n,
        certificado=cstate["certificado"], margen_cert=cstate["margen"],
        metodo_cert=cstate["metodo"], total_celdas=arc.total_celdas(),
        historia_best=historia, n_certificados=cstate["n"],
        bandit_S=dict(bandit.S), bandit_F=dict(bandit.F))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parsear_args(argv=None):
    ap = argparse.ArgumentParser(
        description="Orquestador evolutivo caza-contraejemplos (FunSearch/"
                    "AlphaEvolve/ShinkaEvolve + MAP-Elites + Thompson).")
    ap.add_argument("--conjeturas", default="cal1",
                    help="lista separada por comas: cal1,cal2,cal3")
    ap.add_argument("--iters", type=int, default=400,
                    help="iteraciones (mutaciones) por conjetura")
    ap.add_argument("--llm", default="mock", choices=["mock", "ollama"],
                    help="backend de mutacion (mock=CI determinista)")
    ap.add_argument("--islas", type=int, default=5)
    ap.add_argument("--trees-only", action="store_true",
                    help="restringe a operadores de arbol (decision 5)")
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--reset-cada", type=int, default=40,
                    help="cada cuantas iters se reinicia la peor mitad de islas")
    ap.add_argument("--semillas-por-isla", type=int, default=6)
    ap.add_argument("--out", default=None,
                    help="CSV de log (esquema ga_graphs.py para el dashboard)")
    ap.add_argument("--forzar-python-eval", action="store_true",
                    help="usa el oraculo Python en vez del binario Rust")
    ap.add_argument("--sin-certificado", action="store_true",
                    help="no correr T3 al vuelo (solo busqueda / benchmark)")
    ap.add_argument("--silencioso", action="store_true")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parsear_args(argv)
    conjeturas = [c.strip() for c in args.conjeturas.split(",") if c.strip()]
    t0 = time.time()
    res = orquestar(
        conjeturas=conjeturas, iters=args.iters, llm=args.llm,
        islas=args.islas, trees_only=args.trees_only, semilla=args.semilla,
        reset_cada=args.reset_cada, semillas_por_isla=args.semillas_por_isla,
        out=args.out, forzar_python_eval=args.forzar_python_eval,
        cert_al_vuelo=not args.sin_certificado, verbose=not args.silencioso)
    dt = time.time() - t0
    print("=" * 60)
    for conj, r in res.items():
        marca = "OK-CERT" if r.certificado else "--"
        print("[%s] best_gap=%.8f n=%s celdas=%d cert=%s %s"
              % (conj, r.best_gap, r.best_n, r.total_celdas,
                 r.certificado, marca))
        if r.certificado:
            print("     g6=%s\n     margen=%s  metodo=%s"
                  % (r.best_g6, r.margen_cert, r.metodo_cert))
    print("[fin] %d conjetura(s) en %.1fs; log=%s"
          % (len(res), dt, args.out or "(sin CSV)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

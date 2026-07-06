#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Humo determinista del orquestador (backend MOCK, sin red).

Corre con: python -m pytest orquestador/tests/test_orquestador.py -q
(desde la raiz del repo). Estos tests NO dependen del binario Rust: usan
`forzar_python=True` para el evaluador (mismo gap por contrato de paridad), asi
son reproducibles en cualquier plataforma, incluyendo CI Linux y el Windows
objetivo. No usan Ollama (backend mock).

Cobertura pedida:
  (a) el archivo crece
  (b) el best gap por conjetura es no-decreciente
  (c) con semillas CAL-1 encuentra gap>0 Y `certificar` lo certifica True
  (d) el bandit actualiza S/F
  (e) el rechazo por novedad descarta un duplicado
  (f) misma semilla -> mismo best_g6 (reproducible)
"""
import os
import random
import sys

import networkx as nx
import pytest

# raiz del repo al sys.path (por si pytest se lanza desde otra ruta)
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from orquestador import grafos as G
from orquestador.archivo import Archipielago, Isla
from orquestador.bandit import Bandit
from orquestador.certificar import certificar
from orquestador.evaluar import Evaluador
from orquestador.mutador import Mutador
from orquestador.orquestar import muestrear_padre, orquestar

# g6 conocido de un contraejemplo CAL-1 (n=18, gap≈0.02181) — fixture del repo.
CE_CAL1 = "QKpCC@?_A?O?O?O?O?A??_?A???"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _corrida_mock_cal1(iters=200, semilla=7):
    return orquestar(
        conjeturas=["cal1"], iters=iters, llm="mock", islas=5,
        trees_only=False, semilla=semilla, forzar_python_eval=True,
        cert_al_vuelo=True, out=None, verbose=False,
    )["cal1"]


# ---------------------------------------------------------------------------
# (a) el archivo crece
# ---------------------------------------------------------------------------
def test_archivo_crece():
    rng = random.Random(1)
    arc = Archipielago(n_islas=3, reset_cada=0)
    antes = arc.total_celdas()
    assert antes == 0
    # inserta grafos estructuralmente distintos -> ocupan celdas
    for n in (10, 12, 15, 20, 25):
        g = G.g6_of(nx.path_graph(n))
        arc.islas[0].insertar(g, -0.1 * n)
    assert arc.total_celdas() > antes
    # y una corrida real deja el archivo poblado
    res = _corrida_mock_cal1(iters=120)
    assert res.total_celdas >= 5


# ---------------------------------------------------------------------------
# (b) best gap por conjetura no-decreciente
# ---------------------------------------------------------------------------
def test_best_gap_no_decrece():
    res = _corrida_mock_cal1(iters=200)
    h = res.historia_best
    assert len(h) >= 2
    for i in range(len(h) - 1):
        assert h[i] <= h[i + 1] + 1e-12, "best_gap decrecio en el paso %d" % i


# ---------------------------------------------------------------------------
# (c) con semillas CAL-1 halla gap>0 y certificar lo certifica True
# ---------------------------------------------------------------------------
def test_cal1_encuentra_y_certifica():
    res = _corrida_mock_cal1(iters=300, semilla=7)
    assert res.best_gap > 1e-9, "no se hallo candidato gap>0"
    assert res.certificado is True, "T3 no certifico el mejor candidato"
    assert res.best_g6 is not None
    # re-certificar de forma independiente el best_g6 confirma el veredicto
    cert = certificar(res.best_g6, "cal1")
    assert cert["certificado"] is True
    assert cert["metodo"] in ("exacto-charpoly",) or "mpmath" in cert["metodo"]


def test_certificar_rechaza_no_contraejemplo():
    # la estrella K_{1,9} da gap=0 EXACTO -> NO es contraejemplo
    star = G.g6_of(nx.star_graph(9))
    assert certificar(star, "cal1")["certificado"] is False
    # el CE conocido si certifica
    assert certificar(CE_CAL1, "cal1")["certificado"] is True


# ---------------------------------------------------------------------------
# (d) el bandit actualiza S/F
# ---------------------------------------------------------------------------
def test_bandit_actualiza_sf():
    rng = random.Random(0)
    b = Bandit(["cal1"], G.operadores(trees_only=True), gamma=0.99)
    arm = b.seleccionar(rng, conj="cal1")
    s0, f0 = b.S[arm], b.F[arm]
    b.actualizar(arm, 1)
    assert b.S[arm] == pytest.approx(s0 + 1.0)
    b.actualizar(arm, 0)
    assert b.F[arm] == pytest.approx(f0 + 1.0)
    # el descuento reduce la evidencia acumulada en el siguiente muestreo
    antes = b.S[arm]
    b.seleccionar(rng, conj="cal1")  # aplica _descontar internamente
    assert b.S[arm] < antes + 1e-12


def test_corrida_actualiza_bandit():
    res = _corrida_mock_cal1(iters=150)
    total = sum(res.bandit_S.values()) + sum(res.bandit_F.values())
    assert total > 0, "el bandit no registro ningun resultado en la corrida"


# ---------------------------------------------------------------------------
# (e) rechazo por novedad descarta un duplicado
# ---------------------------------------------------------------------------
def test_novedad_rechaza_duplicado():
    isla = Isla(0)
    g = G.g6_of(nx.path_graph(15))
    ev1 = isla.insertar(g, -0.3)
    assert ev1 == "nueva_celda"
    # mismo grafo (mismo WL-hash) -> rechazado
    ev2 = isla.insertar(g, -0.1)
    assert ev2 == "duplicado"
    # un grafo ISOMORFO (relabelado) tambien comparte hash -> duplicado
    H = nx.relabel_nodes(nx.path_graph(15),
                         {i: (14 - i) for i in range(15)})
    ev3 = isla.insertar(G.g6_of(H), 0.0)
    assert ev3 == "duplicado"


# ---------------------------------------------------------------------------
# (f) misma semilla -> mismo best_g6 (reproducible)
# ---------------------------------------------------------------------------
def test_reproducible_misma_semilla():
    r1 = _corrida_mock_cal1(iters=180, semilla=7)
    r2 = _corrida_mock_cal1(iters=180, semilla=7)
    assert r1.best_g6 == r2.best_g6
    assert r1.best_gap == pytest.approx(r2.best_gap)
    # semilla distinta puede (no debe) diferir; al menos no crashea
    r3 = _corrida_mock_cal1(iters=180, semilla=123)
    assert r3.best_g6 is not None


# ---------------------------------------------------------------------------
# extra: la cascada de evaluacion clasifica bien (T2) y el mutador cae a mock
# ---------------------------------------------------------------------------
def test_evaluador_python_paridad():
    ev = Evaluador("cal1", forzar_python=True)
    star = G.g6_of(nx.star_graph(9))
    d = ev.evaluar([star, CE_CAL1])
    assert d[star] == pytest.approx(0.0, abs=1e-9)
    assert d[CE_CAL1] == pytest.approx(0.021810091691572886, abs=1e-9)
    assert ev.es_candidato(d[CE_CAL1]) is True
    assert ev.es_candidato(d[star]) is False


def test_mutador_mock_conserva_conectividad():
    rng = random.Random(5)
    mut = Mutador(backend="mock", trees_only=True)
    isla = Isla(0)
    isla.insertar(CE_CAL1, 0.02181)
    for op in G.operadores(trees_only=True):
        child, meta = mut.mutar(CE_CAL1, ("cal1", op), isla, rng)
        if child is not None:
            H = G.from_g6(child)
            assert nx.is_connected(H)
            assert G.N_MIN <= H.number_of_nodes() <= G.N_MAX


def test_ollama_backend_cae_a_mock_sin_servidor():
    # sin servidor Ollama arriba, el backend ollama NO debe crashear: fallback.
    rng = random.Random(9)
    mut = Mutador(backend="ollama", trees_only=True,
                  api_base="http://127.0.0.1:1/v1")  # puerto imposible
    isla = Isla(0)
    isla.insertar(CE_CAL1, 0.02181)
    child, meta = mut.mutar(CE_CAL1, ("cal1", "add_leaf"), isla, rng)
    assert child is not None  # cayo a mock
    assert "mock" in meta["backend"] or "fallback" in meta["detalle"]

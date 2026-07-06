"""Nivel 0 — vectores de prueba contra formas cerradas (§4 del spec).

CONTRATO TDD: estos tests SON la especificación. Prohibido modificarlos para que
pasen; se modifica la implementación (common/invariantes.py, evaluators/).
"""
import math
import random

import networkx as nx
import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from common.invariantes import A_de_grafo, lam1_fast, lam1_ref, mu_brute, mu_fast, validar
from evaluators.agx_l1_mu import cota, gap_grafo

PHI = (1.0 + math.sqrt(5.0)) / 2.0
TOL = 1e-9

# (nombre, grafo, lambda1 exacto, mu exacto) — tabla del §4
CASOS = [
    ("K3", nx.complete_graph(3), 2.0, 1),
    ("K10", nx.complete_graph(10), 9.0, 5),
    ("K1_4", nx.star_graph(4), 2.0, 1),          # estrella K_{1,4}, n=5
    ("K1_9", nx.star_graph(9), 3.0, 1),          # estrella K_{1,9}, n=10
    ("P4", nx.path_graph(4), PHI, 2),            # 2cos(pi/5) = (1+sqrt5)/2
    ("C5", nx.cycle_graph(5), 2.0, 2),
    ("C6", nx.cycle_graph(6), 2.0, 3),
    ("K2_3", nx.complete_bipartite_graph(2, 3), math.sqrt(6.0), 2),
    ("K3_3", nx.complete_bipartite_graph(3, 3), 3.0, 3),
    ("Petersen", nx.petersen_graph(), 3.0, 5),
]

# Literales impresos en la tabla del §4 (redondeados a 8 decimales).
# P4 se verifica SOLO contra su forma cerrada sqrt(3)+1-((1+sqrt5)/2+2) =
# -0.8859831811...: el literal impreso -0.88602540 tiene una errata de redondeo
# (~4e-5); la propia tabla manda con su columna de formas cerradas.
GAPS_LITERALES = {
    "K3": -0.58578644,
    "K10": -10.0,
    "K1_4": 0.0,
    "K1_9": 0.0,
    "C5": -1.0,
    "C6": -1.76393202,
    "K2_3": -1.44948975,
    "K3_3": -2.76393202,
    "Petersen": -4.0,
}


@pytest.mark.parametrize("nombre,G,lam_exacto,mu_exacto", CASOS, ids=[c[0] for c in CASOS])
def test_lambda1_forma_cerrada(nombre, G, lam_exacto, mu_exacto):
    assert abs(lam1_fast(A_de_grafo(G)) - lam_exacto) <= TOL


@pytest.mark.parametrize("nombre,G,lam_exacto,mu_exacto", CASOS, ids=[c[0] for c in CASOS])
def test_mu_forma_cerrada(nombre, G, lam_exacto, mu_exacto):
    assert mu_fast(G) == mu_exacto


@pytest.mark.parametrize("nombre,G,lam_exacto,mu_exacto", CASOS, ids=[c[0] for c in CASOS])
def test_gap_forma_cerrada(nombre, G, lam_exacto, mu_exacto):
    n = G.number_of_nodes()
    esperado = cota(n) - (lam_exacto + mu_exacto)
    gap = gap_grafo(G)
    assert abs(gap - esperado) <= TOL
    if nombre in GAPS_LITERALES:
        assert abs(gap - GAPS_LITERALES[nombre]) <= 1e-7


def test_igualdad_exacta_estrellas_detector_de_signos():
    """Los dos casos de IGUALDAD exacta (§4): detectores de errores de signo/cota."""
    for k in (4, 9):
        assert abs(gap_grafo(nx.star_graph(k))) <= TOL


# ---------------------------------------------------------------- property tests (§4)

def _grafos_conexos(cantidad, n_min, n_max, semilla):
    rng = random.Random(semilla)
    out = []
    while len(out) < cantidad:
        n = rng.randint(n_min, n_max)
        p = rng.uniform(0.05, 0.7)
        G = nx.gnp_random_graph(n, p, seed=rng.randint(0, 10**9))
        if G.number_of_nodes() >= 3 and nx.is_connected(G):
            out.append(G)
    return out


@pytest.fixture(scope="module")
def grafos_1000():
    return _grafos_conexos(1000, 3, 60, semilla=20260705)


def test_prop_1_lam1_fast_igual_ref(grafos_1000):
    for G in grafos_1000:
        assert abs(lam1_fast(A_de_grafo(G)) - lam1_ref(G)) <= 1e-8


def test_prop_2_invarianza_bajo_permutacion(grafos_1000):
    rng = random.Random(424242)
    for G in grafos_1000:
        n = G.number_of_nodes()
        perm = list(range(n))
        rng.shuffle(perm)
        H = nx.relabel_nodes(G, dict(zip(sorted(G.nodes()), perm)))
        assert abs(lam1_fast(A_de_grafo(G)) - lam1_fast(A_de_grafo(H))) <= 1e-8
        assert mu_fast(G) == mu_fast(H)
        assert abs(gap_grafo(G) - gap_grafo(H)) <= 1e-8


def test_prop_3_mu_fast_igual_mu_brute(grafos_1000):
    chicos = [G for G in grafos_1000 if G.number_of_nodes() <= 12]
    chicos += _grafos_conexos(200, 3, 12, semilla=777)
    assert len(chicos) >= 150, "cobertura insuficiente de casos n<=12"
    for G in chicos:
        assert mu_fast(G) == mu_brute(G)


def test_prop_4_gap_estrellas_cero():
    for n in range(3, 121):
        assert abs(gap_grafo(nx.star_graph(n - 1))) <= TOL


# ---------------------------------------------------------------- validar() (§3)

def test_validar_triangulo_ok():
    r = validar("0 1\n1 2\n2 0\n")
    assert r["ok"] is True and r["error"] is None
    assert r["n"] == 3
    assert isinstance(r["A"], np.ndarray) and r["A"].shape == (3, 3)
    assert r["A"].sum() == 6.0 and np.allclose(r["A"], r["A"].T)


def test_validar_estrella_ok():
    r = validar("0 1\n0 2\n0 3")
    assert r["ok"] is True and r["n"] == 4


def test_validar_lazo():
    r = validar("0 1\n1 2\n3 3\n2 3")
    assert r["ok"] is False and "lazo" in r["error"]


def test_validar_multiarista():
    r = validar("0 1\n1 2\n2 0\n1 0")
    assert r["ok"] is False and "multiarista" in r["error"]


def test_validar_huecos():
    r = validar("0 2\n2 3\n3 0")  # falta el vértice 1
    assert r["ok"] is False and "huecos" in r["error"]


def test_validar_vertice_negativo():
    r = validar("-1 2\n2 3")
    assert r["ok"] is False and r["error"]


def test_validar_n_muy_chico():
    r = validar("0 1")
    assert r["ok"] is False and "n_fuera_de_rango" in r["error"]


def test_validar_n_muy_grande():
    texto = "\n".join(f"{i} {i + 1}" for i in range(301))  # camino con n=302
    r = validar(texto)
    assert r["ok"] is False and "n_fuera_de_rango" in r["error"]


def test_validar_desconexo():
    r = validar("0 1\n1 2\n2 0\n3 4\n4 5\n5 3")
    assert r["ok"] is False and "desconexo" in r["error"]


def test_validar_basura():
    r = validar("hola mundo\n0 1")
    assert r["ok"] is False and "linea_invalida" in r["error"]


def test_validar_flotantes_y_tokens_extra():
    assert validar("0.5 1\n1 2")["ok"] is False
    assert validar("0 1 2\n1 2")["ok"] is False


def test_validar_vacio():
    for texto in ("", "   ", "\n\n"):
        r = validar(texto)
        assert r["ok"] is False and r["error"]


def test_validar_entero_gigante():
    r = validar("0 99999999999999999999")
    assert r["ok"] is False and r["error"]


@given(st.text(max_size=2000))
def test_validar_nunca_lanza_excepcion(texto):
    """Contrato §3: cualquier violación → rechazo estructurado, NUNCA excepción."""
    r = validar(texto)
    assert isinstance(r, dict) and "ok" in r
    if not r["ok"]:
        assert isinstance(r["error"], str) and r["error"]
    else:
        assert r["A"] is not None and 3 <= r["n"] <= 300

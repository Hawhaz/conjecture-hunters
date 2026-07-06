"""Nivel 1.5 — fixtures de contraejemplos publicados (§6).

Confirman los evaluadores contra la realidad publicada SIN ejecutar búsqueda.
Cada test se salta (skip) si el .g6 aún no existe; verde cuando exista.
"""
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

FIX = Path(__file__).resolve().parent / "fixtures"


def _cargar(nombre):
    G = nx.read_graph6(str(FIX / nombre))
    return nx.convert_node_labels_to_integers(G)


@pytest.mark.skipif(not (FIX / "fixture_l1mu.g6").exists(),
                    reason="falta fixture_l1mu.g6 (Fixture A, §6)")
def test_fixture_A_l1mu_gap_positivo():
    """Contraejemplo de lambda1 + mu (Wagner 2021 / AMCS 2023): gap > 0."""
    from evaluators.agx_l1_mu import gap_grafo

    G = _cargar("fixture_l1mu.g6")
    assert G.number_of_nodes() >= 3 and nx.is_connected(G)
    gap = gap_grafo(G)
    assert gap > 1e-12, f"el fixture publicado debe refutar CAL-1; gap={gap}"


@pytest.mark.skipif(not (FIX / "wagner19.g6").exists(),
                    reason="TODO HUMANO: falta wagner19.g6 (§1)")
def test_fixture_wagner19_gap_positivo():
    from evaluators.agx_l1_mu import gap_grafo

    G = _cargar("wagner19.g6")
    assert nx.is_connected(G)
    assert gap_grafo(G) > 1e-12


@pytest.mark.skipif(not (FIX / "fixture_c4_estrellas.g6").exists(),
                    reason="falta fixture_c4_estrellas.g6 (Fixture B, §6)")
def test_fixture_B_lambda2_mayor_que_armonico():
    """CAL-2 (lambda2 <= Hc, Favaron et al. 1993) refutada por AMCS 2023.

    Receta §6: unir los centros de las estrellas S15 y S19 a un vértice nuevo.
    """
    G = _cargar("fixture_c4_estrellas.g6")
    assert nx.is_connected(G)
    A = nx.to_numpy_array(G, nodelist=sorted(G.nodes()), dtype=np.float64)
    lam2 = float(np.linalg.eigvalsh(A)[-2])
    hc = sum(2.0 / (G.degree[u] + G.degree[v]) for u, v in G.edges())
    assert lam2 - hc > 1e-12, f"lambda2={lam2} debe superar Hc={hc}"


@pytest.mark.skipif(not (FIX / "fixture_c2_203.g6").exists(),
                    reason="falta fixture_c2_203.g6 (Fixture C, §6)")
def test_fixture_C_proximidad_mas_delta_2D3_negativa():
    """CAL-3 (pi + delta_{floor(2D/3)} > 0, Aouchiche–Hansen 2016) refutada por AMCS.

    Receta §6: centro de S191 unido a un extremo de un P7 y a un extremo de un P5.
    n = 203, score publicado ~ 0.00028. Benchmark DURO (solo AMCS lo re-encontró).
    """
    import scipy.sparse as sp
    import scipy.sparse.csgraph as csg

    G = _cargar("fixture_c2_203.g6")
    n = G.number_of_nodes()
    assert n == 203 and nx.is_connected(G)

    D = csg.shortest_path(sp.csr_matrix(nx.to_scipy_sparse_array(G, nodelist=sorted(G.nodes()))),
                          method="D", unweighted=True)
    diam = int(D.max())
    assert diam == 12  # extremo de P7 ... centro ... extremo de P5
    k = (2 * diam) // 3  # = 8
    delta_desc = np.sort(np.linalg.eigvalsh(D))[::-1]
    delta_k = float(delta_desc[k - 1])  # delta_i con i 1-indexado, orden decreciente
    proximidad = float(D.sum(axis=1).min()) / (n - 1)

    score = -(proximidad + delta_k)
    assert score > 0.0, f"pi + delta_{k} = {-score} debería ser negativa (refutación)"
    assert abs(score - 0.00028) < 1e-4, f"score={score:.6f} lejos del ~0.00028 publicado"

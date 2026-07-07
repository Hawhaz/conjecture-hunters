# -*- coding: utf-8 -*-
"""Gate anti-basura del pack de conjeturas, como pytest (verde ANTES de la GPU).

Blinda: (1) las de validación re-descubren su contraejemplo conocido; (2) las
abiertas se sostienen en TODO el corpus de control; (3) los extremales reclamados
dan igualdad (cota ajustada); (4) el falso positivo K4 de Bollobás queda excluido.
Si alguna conjetura está mal codificada (basura de mates o de código), esto falla.
"""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack_conjeturas as pc  # noqa: E402


def test_gate_anti_basura_completo():
    assert pc.verificar(verbose=False) is True


def test_validacion_jia_song_redescubre_F2():
    # el grafo de la amistad F2 refuta Jia-Song (nuestro resultado estrella)
    assert pc.gap_jia_song(pc.friendship(2)) > pc.TOL


def test_validacion_elphick_redescubre_C7():
    # C7 refuta la variante ell=n+ (contraejemplo conocido de la literatura)
    assert pc.gap_elphick_np(nx.cycle_graph(7)) > pc.TOL


def test_bollobas_excluye_completos_el_caso_K4():
    K4 = nx.complete_graph(4)
    # sin exclusión, K4 daría un FALSO POSITIVO (+1): (n-1)^2+1 > (n-1)^2
    assert pc.gap_bollobas(K4) > 0.5
    # el carril lo excluye correctamente (la conjetura excluye grafos completos)
    lane = next(L for L in pc.LANES if L[0].startswith("bollobas"))
    aplica = lane[3]
    assert aplica(K4) is False


def test_lin_p4_igualdad_en_bipartito_balanceado():
    for n in (4, 6, 8, 10):
        assert abs(pc.gap_lin_p4(nx.complete_bipartite_graph(n // 2, n // 2))) < 1e-6


def test_graffiti_igualdad_en_completo():
    for n in (4, 5, 6):
        assert abs(pc.gap_graffiti(nx.complete_graph(n))) < 1e-6


def test_todas_las_abiertas_se_sostienen_en_corpus():
    C = pc.corpus_control()
    for nombre, kind, gap, aplica, extremal, ce in pc.LANES:
        if kind != "abierta":
            continue
        for G in C:
            if aplica(G):
                assert gap(G) <= pc.TOL, f"{nombre}: falso positivo en n={G.number_of_nodes()}"

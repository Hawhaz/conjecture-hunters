# -*- coding: utf-8 -*-
"""Gate anti-basura de los 11 carriles extra (validacion + abiertas). Verde ANTES
de la GPU. Las de validacion re-descubren su contraejemplo con el score exacto de
la literatura; las abiertas se sostienen y sus extremales son ajustados."""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pack_extra as pe  # noqa: E402


def test_gate_extra_completo():
    assert pe.verificar(verbose=False) is True


def test_validacion_re_descubre_todas():
    for nombre, kind, gap, aplica, extremal, ce in pe.LANES_EXTRA:
        if kind == "validacion":
            assert gap(ce()) > pe.TOL, f"{nombre} no re-descubre su CE"


def test_scores_literatura():
    # coinciden con los papers (AMCS / Wagner) a 4 decimales
    assert abs(pe.gap_lambda1_pi(pe.k5_p7()) - 0.05923) < 1e-3
    assert abs(pe.gap_cal1_lambda_mu(pe.broom2(8, 8)) - 0.08036) < 1e-3
    assert abs(pe.gap_gutman_energy(pe.line_k5()) - 2.0) < 1e-6


def test_abiertas_se_sostienen():
    C = pe.corpus_control()
    for nombre, kind, gap, aplica, extremal, ce in pe.LANES_EXTRA:
        if kind != "abierta":
            continue
        for G in C:
            if aplica(G):
                assert gap(G) <= 1e-6, f"{nombre}: falso positivo n={G.number_of_nodes()}"


def test_extremal_pineapple_y_dcomet_ajustados():
    for n in (6, 8, 10):
        assert pe.gap_pineapple_le(pe.pineapple(n)) <= 1e-6
        T = pe.min_comet_table(n)
        assert abs(pe.gap_tree_spectral(T)) <= 1e-6

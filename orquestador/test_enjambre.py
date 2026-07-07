# -*- coding: utf-8 -*-
"""Tests del mutador Gemma del enjambre (parseo/aplicacion de la edicion que
propone el LLM). Puro, sin red: valida la tuberia AlphaEvolve (LLM propone ->
aritmetica exacta juzga) antes de gastar GPU."""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enjambre as ej  # noqa: E402


def test_apply_edit_add():
    H = ej._apply_edit(nx.path_graph(5), "ADD 0 4")
    assert H is not None and H.has_edge(0, 4)


def test_apply_edit_del_minuscula():
    H = ej._apply_edit(nx.path_graph(5), "del 1 2")
    assert H is not None and not H.has_edge(1, 2)


def test_apply_edit_invalidos():
    G = nx.path_graph(5)
    assert ej._apply_edit(G, "hola gemma") is None      # no parsea
    assert ej._apply_edit(G, "ADD 0 9") is None          # fuera de rango
    assert ej._apply_edit(G, "DEL 0 4") is None          # arista inexistente
    assert ej._apply_edit(G, "ADD 2 2") is None          # bucle


def test_gemma_sin_endpoint_devuelve_none():
    os.environ.pop("CONJ_API_BASE", None)
    assert ej._gemma_edit(nx.path_graph(5), "lin_p4", -1.0) is None


def test_hay_20_carriles_o_fallback():
    # con pack_conjeturas cargado son 20; en fallback (glitch de mount) 11
    assert len(ej.ALL_LANES) in (11, 20)

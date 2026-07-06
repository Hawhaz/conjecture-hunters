"""Nivel 1 — oráculo exhaustivo (§5).

Todos los grafos conexos con 3 <= n <= 7 (atlas de networkx) deben cumplir la
conjetura CAL-1: gap(G) <= 1e-9. Si alguno "viola", con probabilidad ~1 es bug
de fórmula: detener y auditar contra los vectores del §4.
"""
import networkx as nx
import pytest

from evaluators.agx_l1_mu import gap_grafo


def test_atlas_exhaustivo_n_le_7():
    from networkx.generators.atlas import graph_atlas_g

    atlas = graph_atlas_g()
    conexos = [G for G in atlas if G.number_of_nodes() >= 3 and nx.is_connected(G)]
    # 2 + 6 + 21 + 112 + 853 grafos conexos con n = 3..7 (An Atlas of Graphs)
    assert len(conexos) == 994

    violaciones = []
    for i, G in enumerate(conexos):
        g = gap_grafo(G)
        if g > 1e-9:
            violaciones.append((i, G.number_of_nodes(), sorted(G.edges()), g))
    assert violaciones == [], (
        f"{len(violaciones)} 'violaciones' con n<=7: bug de fórmula (§5). "
        f"Primeras: {violaciones[:3]}"
    )

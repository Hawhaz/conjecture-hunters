"""Construye los fixtures B y C con las recetas EXPLÍCITAS del §6 (Vito–Stefanus
2023, arXiv 2306.07956). NO se inventan grafos: receta literal + verificación
numérica contra la desigualdad publicada antes de escribir el .g6.

  B (fixture_c4_estrellas.g6): unir los centros de las estrellas S15 y S19 a un
    vértice nuevo. Contraejemplo de CAL-2: λ₂ ≤ Hc (índice armónico).
  C (fixture_c2_203.g6): unir el centro de una estrella S191 a un extremo de un
    P7 y a un extremo de un P5 (n = 203, score ≈ 0.00028). Contraejemplo de
    CAL-3: π + ∂_{⌊2D/3⌋} > 0.

Convención Sₙ = estrella CON n vértices (K_{1,n−1}); es la única que hace
n = 191 + 7 + 5 = 203 como publica el paper.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx
import numpy as np

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures")


def estrella_n(n):
    """Estrella con n vértices: centro 0, hojas 1..n-1."""
    return nx.star_graph(n - 1)


def unir_disjuntos(*grafos):
    """Unión disjunta renumerando; devuelve (G, offsets de cada bloque)."""
    G = nx.Graph()
    offsets = []
    total = 0
    for H in grafos:
        offsets.append(total)
        G.add_nodes_from(v + total for v in H.nodes())
        G.add_edges_from((u + total, v + total) for u, v in H.edges())
        total += H.number_of_nodes()
    return G, offsets, total


def construir_B():
    """Centros de S15 y S19 unidos a un vértice nuevo (n = 35)."""
    G, off, total = unir_disjuntos(estrella_n(15), estrella_n(19))
    nuevo = total
    G.add_edge(off[0] + 0, nuevo)  # centro de S15
    G.add_edge(off[1] + 0, nuevo)  # centro de S19
    return G


def construir_C():
    """Centro de S191 unido a un extremo de un P7 y a un extremo de un P5 (n = 203)."""
    G, off, total = unir_disjuntos(estrella_n(191), nx.path_graph(7), nx.path_graph(5))
    centro = off[0] + 0
    G.add_edge(centro, off[1] + 0)  # extremo del P7
    G.add_edge(centro, off[2] + 0)  # extremo del P5
    return G


def verificar_B(G):
    A = nx.to_numpy_array(G, nodelist=sorted(G.nodes()), dtype=np.float64)
    lam2 = float(np.linalg.eigvalsh(A)[-2])
    hc = sum(2.0 / (G.degree[u] + G.degree[v]) for u, v in G.edges())
    gap = lam2 - hc
    print(f"[B] n={G.number_of_nodes()}, λ₂={lam2:.6f}, Hc={hc:.6f}, λ₂−Hc={gap:.6f}")
    assert nx.is_connected(G) and gap > 0, "B no refuta CAL-2: revisar receta"
    return gap


def verificar_C(G):
    import scipy.sparse as sp
    import scipy.sparse.csgraph as csg

    n = G.number_of_nodes()
    D = csg.shortest_path(sp.csr_matrix(nx.to_scipy_sparse_array(G, nodelist=sorted(G.nodes()))),
                          method="D", unweighted=True)
    diam = int(D.max())
    k = (2 * diam) // 3
    delta_desc = np.sort(np.linalg.eigvalsh(D))[::-1]
    delta_k = float(delta_desc[k - 1])
    proximidad = float(D.sum(axis=1).min()) / (n - 1)
    score = -(proximidad + delta_k)
    print(f"[C] n={n}, D={diam}, k={k}, π={proximidad:.6f}, ∂_{k}={delta_k:.6f}, "
          f"score=−(π+∂_{k})={score:.6f}")
    assert nx.is_connected(G) and n == 203 and diam == 12, "C: estructura inesperada"
    assert score > 0, "C no refuta CAL-3: revisar receta"
    assert abs(score - 0.00028) < 1e-4, f"C: score {score:.6f} lejos del ~0.00028 publicado"
    return score


def guardar(G, nombre):
    ruta = os.path.join(FIXTURES, nombre)
    g6 = nx.to_graph6_bytes(nx.convert_node_labels_to_integers(G), header=False).decode("ascii").strip()
    with open(ruta, "w", encoding="ascii", newline="\n") as f:
        f.write(g6 + "\n")
    print(f"[ok] {nombre} escrito ({len(g6)} chars g6)")


if __name__ == "__main__":
    B = construir_B()
    verificar_B(B)
    guardar(B, "fixture_c4_estrellas.g6")

    C = construir_C()
    verificar_C(C)
    guardar(C, "fixture_c2_203.g6")
    print("[ok] fixtures B y C construidos y verificados contra lo publicado")

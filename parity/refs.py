"""Oráculo de paridad (ground-truth) para el port Rust del buscador de contraejemplos.

Reutiliza VERBATIM las funciones del repo (no se inventan fórmulas):
  - CAL-1: evaluators.agx_l1_mu.{gap_grafo, cota} + common.invariantes.{lam1_fast, mu_fast, A_de_grafo}
  - CAL-2: λ₂ = eigvalsh(A)[-2]; Hc = Σ 2/(deg[u]+deg[v]); gap2 = λ₂ − Hc
  - CAL-3: espejo EXACTO de calibracion/construir_fixtures_b_c.py::verificar_C

Todos los grafos se reetiquetan 0..n−1 en orden ("sorted") antes de calcular.
"""
import os
import sys

# raíz del repo en sys.path para importar los módulos del repo
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.csgraph as csg

from common.invariantes import A_de_grafo, lam1_fast, mu_fast  # noqa: F401  (reuso repo)
from evaluators.agx_l1_mu import cota, gap_grafo  # noqa: F401  (reuso repo)


def _relabel(G):
    """Reetiqueta a 0..n−1 en orden estable ('sorted'), como exige el oráculo."""
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


def g6_of(G):
    """graph6 canónico (sin cabecera) del grafo reetiquetado 0..n−1 en orden."""
    H = _relabel(G)
    return nx.to_graph6_bytes(H, header=False).decode("ascii").strip()


def cal1(G):
    """CAL-1 → (lam1, mu, gap1). Reusa gap_grafo/lam1_fast/mu_fast del repo.

    gap1 = (√(n−1)+1) − (λ₁ + μ), con λ₁ = eigvalsh(A)[-1] y μ = |max matching|.
    """
    H = _relabel(G)
    A = A_de_grafo(H)
    lam1 = lam1_fast(A)
    mu = mu_fast(H)
    gap1 = gap_grafo(H)  # = cota(n) − (lam1 + mu); idéntico al evaluador congelado
    return lam1, mu, gap1


def cal2(G):
    """CAL-2 → (lam2, hc, gap2).

    λ₂ = eigvalsh(A)[-2]; Hc = Σ_{uv∈E} 2/(deg[u]+deg[v]); gap2 = λ₂ − Hc.
    (Índice de grado idéntico a verificar_B: G.degree sobre el grafo reetiquetado.)
    """
    H = _relabel(G)
    A = A_de_grafo(H)
    lam2 = float(np.linalg.eigvalsh(A)[-2])
    hc = sum(2.0 / (H.degree[u] + H.degree[v]) for u, v in H.edges())
    gap2 = lam2 - hc
    return lam2, hc, gap2


def cal3(G):
    """CAL-3 → (pi, diam, k, delta_k, gap3). Espejo EXACTO de verificar_C.

    D = shortest_path(csr(to_scipy_sparse_array(G, nodelist=sorted)), 'D', unweighted=True)
    diam = int(D.max()); k = (2*diam)//3
    delta_desc = np.sort(eigvalsh(D))[::-1]; delta_k = float(delta_desc[k-1])
      (semántica de índice negativo de Python: k==0 ⇒ delta_desc[-1] = el MENOR eigen)
    pi = D.sum(axis=1).min() / (n−1); gap3 = −(pi + delta_k).
    """
    H = _relabel(G)
    n = H.number_of_nodes()
    D = csg.shortest_path(
        sp.csr_matrix(nx.to_scipy_sparse_array(H, nodelist=sorted(H.nodes()))),
        method="D",
        unweighted=True,
    )
    diam = int(D.max())
    k = (2 * diam) // 3
    delta_desc = np.sort(np.linalg.eigvalsh(D))[::-1]
    delta_k = float(delta_desc[k - 1])
    pi = float(D.sum(axis=1).min()) / (n - 1)
    gap3 = -(pi + delta_k)
    return pi, diam, k, delta_k, gap3

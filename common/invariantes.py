"""Invariantes espectrales y de matching (§3) + validación de grafos.

Doble implementación deliberada: *fast* (hot path del evaluador) y *ref/brute*
(SOLO tests). Si fast y ref divergen, el bug es nuestro.

⚠️ Trampa conocida (§3): networkx.maximal_matching es GREEDY (maximal ≠ maximum)
y produce basura silenciosa. Aquí solo se usa max_weight_matching(...,
maxcardinality=True).
"""
import math
from collections import deque

import networkx as nx
import numpy as np

N_MIN, N_MAX = 3, 300


def A_de_grafo(G):
    """Matriz de adyacencia densa float64 con filas/columnas en orden de etiqueta."""
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()), dtype=np.float64)


def lam1_fast(A):
    """λ₁: mayor eigenvalor de la matriz de adyacencia (eigvalsh, denso, float64)."""
    A = np.asarray(A, dtype=np.float64)
    return float(np.linalg.eigvalsh(A)[-1])


def lam1_ref(G):
    """SOLO tests: λ₁ vía networkx.adjacency_spectrum (máxima parte real)."""
    return float(max(v.real for v in nx.adjacency_spectrum(G)))


def mu_fast(G):
    """μ: número de emparejamiento (maximum matching por cardinalidad)."""
    return len(nx.max_weight_matching(G, maxcardinality=True))


def mu_brute(G, n_max=12):
    """SOLO tests: matching máximo exacto por recursión con memo sobre bitmasks (n ≤ 12)."""
    n = G.number_of_nodes()
    if n > n_max:
        raise ValueError(f"mu_brute es solo para n <= {n_max}; llegó n={n}")
    nodos = sorted(G.nodes())
    idx = {v: i for i, v in enumerate(nodos)}
    ady = [0] * n
    for u, v in G.edges():
        if u != v:
            ady[idx[u]] |= 1 << idx[v]
            ady[idx[v]] |= 1 << idx[u]
    memo = {}

    def f(mask):
        if mask == 0:
            return 0
        if mask in memo:
            return memo[mask]
        v = (mask & -mask).bit_length() - 1
        resto = mask & ~(1 << v)
        mejor = f(resto)  # v queda sin emparejar
        vecinos = ady[v] & mask
        while vecinos:
            u = (vecinos & -vecinos).bit_length() - 1
            vecinos &= vecinos - 1
            mejor = max(mejor, 1 + f(resto & ~(1 << u)))
        memo[mask] = mejor
        return mejor

    return f((1 << n) - 1)


def validar(texto_aristas):
    """Parsea stdout ('u v' por línea, enteros 0-indexed) → dict estructurado.

    Reglas (§3): grafo simple (sin lazos ni multiaristas), conexo (BFS),
    3 ≤ n ≤ 300, vértices etiquetados 0..n−1 sin huecos. Cualquier violación
    → rechazo estructurado; esta función NUNCA lanza excepción.
    """
    try:
        return _validar(texto_aristas)
    except Exception as e:  # cinturón y tirantes: el orquestador sigue vivo
        return _rechazo(f"error_interno_validar: {type(e).__name__}: {e}")


def _rechazo(motivo):
    return {"ok": False, "error": motivo, "A": None, "G": None, "n": None}


def _validar(texto):
    if texto is None:
        return _rechazo("vacio: stdout None")
    if isinstance(texto, bytes):
        texto = texto.decode("utf-8", errors="replace")

    lineas = [l.strip() for l in texto.splitlines()]
    lineas = [l for l in lineas if l]
    if not lineas:
        return _rechazo("vacio: stdout sin aristas")

    aristas = []
    vistos = set()
    for i, linea in enumerate(lineas, 1):
        partes = linea.split()
        if len(partes) != 2:
            return _rechazo(f"linea_invalida (línea {i}): {linea[:60]!r} — se espera 'u v'")
        try:
            u, v = int(partes[0]), int(partes[1])
        except ValueError:
            return _rechazo(f"linea_invalida (línea {i}): {linea[:60]!r} — enteros requeridos")
        if u < 0 or v < 0:
            return _rechazo(f"vertice_negativo (línea {i}): {linea[:60]!r}")
        if u == v:
            return _rechazo(f"lazo (línea {i}): vértice {u}")
        clave = (u, v) if u < v else (v, u)
        if clave in vistos:
            return _rechazo(f"multiarista (línea {i}): {clave}")
        vistos.add(clave)
        aristas.append(clave)

    n = max(max(u, v) for u, v in aristas) + 1
    if n < N_MIN or n > N_MAX:
        return _rechazo(f"n_fuera_de_rango: n={n}, se exige {N_MIN} <= n <= {N_MAX}")

    presentes = set()
    for u, v in aristas:
        presentes.add(u)
        presentes.add(v)
    if presentes != set(range(n)):
        faltan = sorted(set(range(n)) - presentes)[:5]
        return _rechazo(f"vertices_con_huecos: faltan {faltan} (se exigen etiquetas 0..{n - 1})")

    # conexidad por BFS (§3)
    ady = [[] for _ in range(n)]
    for u, v in aristas:
        ady[u].append(v)
        ady[v].append(u)
    visto = [False] * n
    visto[0] = True
    cola = deque([0])
    alcanzados = 1
    while cola:
        x = cola.popleft()
        for y in ady[x]:
            if not visto[y]:
                visto[y] = True
                alcanzados += 1
                cola.append(y)
    if alcanzados != n:
        return _rechazo(f"desconexo: BFS alcanza {alcanzados} de {n} vértices")

    A = np.zeros((n, n), dtype=np.float64)
    for u, v in aristas:
        A[u, v] = 1.0
        A[v, u] = 1.0
    return {"ok": True, "error": None, "A": A, "G": nx.from_numpy_array(A), "n": n}

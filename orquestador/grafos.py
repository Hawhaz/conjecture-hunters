#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers de grafos para el orquestador evolutivo.

Codec graph6 (via networkx, con la MISMA convencion de reetiquetado 0..n-1 en
orden 'sorted' que usan el oraculo `parity/refs.py`, los evaluadores congelados
y `certificados/verify.py`), aplicacion determinista de deltas de aristas,
descriptores (n, densidad) para el archivo MAP-Elites, hash Weisfeiler-Lehman
para rechazo por novedad, operadores estructurales (arbol/conexo) y las
familias de semillas por conjetura (replicadas de `calibracion/ga_graphs.py`).

NADA aqui reinventa formulas de gap: la evaluacion vive en `evaluar.py`
(binario Rust) y la certificacion en `certificar.py` (verify.certificar). Este
modulo solo produce/transforma grafos y los serializa a g6.

Convencion critica (paridad con el resto del stack): TODO grafo se normaliza a
0..n-1 en orden estable ('sorted') antes de emitir g6. Asi el g6 que el
orquestador pasa al Rust y al certificador es byte-identico al del oraculo.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

import networkx as nx

# ---------------------------------------------------------------------------
# Banda de tamano (identica a calibracion/ga_graphs.py::N_MIN,N_MAX).
# ---------------------------------------------------------------------------
N_MIN = 10
N_MAX = 40

# Binning de descriptores para MAP-Elites (celdas del archivo). Los bins NO
# incluyen matching ni eigenvalores (correlacionan con el fitness): solo n y
# densidad m/C(n,2) (decision 3 del diseno, MAP-Elites/AlphaEvolve).
DENSITY_BINS = 8  # cuantiza densidad en [0,1] en 8 cubetas


# ---------------------------------------------------------------------------
# Normalizacion + codec graph6
# ---------------------------------------------------------------------------
def norm(G: nx.Graph) -> nx.Graph:
    """Reetiqueta a 0..n-1 en orden estable ('sorted'). Igual que el oraculo."""
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


def g6_of(G: nx.Graph) -> str:
    """graph6 canonico (sin cabecera) del grafo normalizado 0..n-1 'sorted'."""
    H = norm(G)
    return nx.to_graph6_bytes(H, header=False).decode("ascii").strip()


def from_g6(s: str) -> nx.Graph:
    """Decodifica un g6 (con o sin espacios sobrantes) a un grafo normalizado."""
    G = nx.from_graph6_bytes(s.strip().encode("ascii"))
    return norm(G)


# ---------------------------------------------------------------------------
# Descriptores (para el archivo MAP-Elites)
# ---------------------------------------------------------------------------
def densidad(G: nx.Graph) -> float:
    """m / C(n,2). 0 para n<2. Es la densidad de aristas del grafo simple."""
    n = G.number_of_nodes()
    if n < 2:
        return 0.0
    return G.number_of_edges() / (n * (n - 1) / 2.0)


def descriptores(G: nx.Graph) -> Tuple[int, float]:
    """(n, densidad). Los dos ejes 'ortogonales al fitness' del archivo."""
    return G.number_of_nodes(), densidad(G)


def celda(G: nx.Graph, n_min: int = N_MIN, n_max: int = N_MAX,
          density_bins: int = DENSITY_BINS) -> Tuple[int, int]:
    """Celda MAP-Elites = (n_bin, density_bin).

    n_bin = n recortado a [n_min, n_max] (un bin por tamano exacto: la banda es
    estrecha, 10..40). density_bin = floor(densidad * density_bins) en
    [0, density_bins-1]. NO usa matching ni eigenvalores (decision 3).
    """
    n = G.number_of_nodes()
    n_bin = max(n_min, min(n_max, n))
    d = densidad(G)
    db = int(math.floor(d * density_bins))
    if db >= density_bins:
        db = density_bins - 1
    if db < 0:
        db = 0
    return (n_bin, db)


def wl_hash(G: nx.Graph, iterations: int = 3) -> str:
    """Hash Weisfeiler-Lehman (isomorfismo-invariante) para rechazo por novedad.

    Dos grafos isomorfos comparten hash; el orquestador lo usa para NO gastar
    evaluaciones en duplicados estructurales dentro de una isla (decision 6,
    ShinkaEvolve). Usa networkx.weisfeiler_lehman_graph_hash.
    """
    return nx.weisfeiler_lehman_graph_hash(norm(G), iterations=iterations)


# ---------------------------------------------------------------------------
# Validez barata (cascada T1, AlphaEvolve): sin tocar el gap.
# ---------------------------------------------------------------------------
def valido(G: Optional[nx.Graph], n_min: int = N_MIN, n_max: int = N_MAX,
           requiere_conexo: bool = True) -> bool:
    """T1: grafo simple, conexo (opcional) y n en la banda. NO evalua gap."""
    if G is None:
        return False
    n = G.number_of_nodes()
    if n < n_min or n > n_max:
        return False
    if G.number_of_edges() == 0 and n > 1:
        return False
    if requiere_conexo and not nx.is_connected(G):
        return False
    return True


# ---------------------------------------------------------------------------
# Aplicacion de deltas de aristas (LLM-delta / operadores expresados como delta)
# ---------------------------------------------------------------------------
def aplicar_delta(G: nx.Graph,
                  agregar: Iterable[Tuple[int, int]] = (),
                  quitar: Iterable[Tuple[int, int]] = ()) -> nx.Graph:
    """Aplica un delta de aristas de forma DETERMINISTA sobre una copia.

    `agregar`/`quitar` son listas de pares (u,v) sobre las etiquetas ACTUALES
    del grafo (0..n-1). Aristas de vertices nuevos (u o v == n) extienden el
    grafo por uno; se ignoran indices fuera de rango >n. Devuelve el grafo
    normalizado. No valida conectividad: eso lo hace `valido()`.
    """
    H = norm(G).copy()
    n = H.number_of_nodes()
    for (u, v) in quitar:
        if H.has_edge(u, v):
            H.remove_edge(u, v)
    for (u, v) in agregar:
        # permite crear a lo sumo UN vertice nuevo por extremo (indice == n)
        for w in (u, v):
            if w == H.number_of_nodes():
                H.add_node(w)
        if 0 <= u < H.number_of_nodes() and 0 <= v < H.number_of_nodes() and u != v:
            H.add_edge(u, v)
    return norm(H)


# ---------------------------------------------------------------------------
# Operadores estructurales (decision 5). Todos son DETERMINISTAS dado el rng.
# Devuelven un grafo nuevo normalizado, o None si el operador no aplica.
# Los operadores de ARBOL (add_leaf, subdivide_edge, prune_leaf,
# prune_subdivision) preservan conectividad por construccion. add_edge SOLO se
# ofrece en modo conexo (no --trees-only).
# ---------------------------------------------------------------------------
def op_add_leaf(G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Cuelga una hoja nueva de un vertice existente elegido al azar."""
    H = norm(G).copy()
    if H.number_of_nodes() >= N_MAX:
        return None
    base = rng.choice(list(H.nodes()))
    nuevo = H.number_of_nodes()
    H.add_edge(base, nuevo)
    return norm(H)


def op_subdivide_edge(G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Subdivide una arista (u,v): la parte en u-w-v con w vertice nuevo."""
    H = norm(G).copy()
    if H.number_of_nodes() >= N_MAX:
        return None
    aristas = list(H.edges())
    if not aristas:
        return None
    u, v = aristas[rng.randrange(len(aristas))]
    w = H.number_of_nodes()
    H.remove_edge(u, v)
    H.add_edge(u, w)
    H.add_edge(w, v)
    return norm(H)


def op_prune_leaf(G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Elimina una hoja (grado 1) al azar. Mantiene conectividad."""
    H = norm(G).copy()
    if H.number_of_nodes() <= N_MIN:
        return None
    hojas = [x for x in H.nodes() if H.degree[x] == 1]
    if not hojas:
        return None
    v = hojas[rng.randrange(len(hojas))]
    H.remove_node(v)
    return norm(H)


def op_prune_subdivision(G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Contrae un vertice de grado 2 (u-w-v) uniendo u-v (inverso de subdivide).

    Solo si u,v no eran ya adyacentes (para no crear multigrafo) y n>N_MIN.
    Preserva conectividad.
    """
    H = norm(G).copy()
    if H.number_of_nodes() <= N_MIN:
        return None
    grado2 = [x for x in H.nodes() if H.degree[x] == 2]
    rng.shuffle(grado2)
    for w in grado2:
        u, v = list(H.neighbors(w))
        if u != v and not H.has_edge(u, v):
            H.remove_node(w)
            H.add_edge(u, v)
            return norm(H)
    return None


def op_add_edge(G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Agrega una arista faltante (SOLO modo conexo, no --trees-only)."""
    H = norm(G).copy()
    faltantes = list(nx.non_edges(H))
    if not faltantes:
        return None
    u, v = faltantes[rng.randrange(len(faltantes))]
    H.add_edge(u, v)
    return norm(H)


# Nombres canonicos de operadores (arms del bandit se cruzan con estos).
OPS_ARBOL = ["add_leaf", "subdivide_edge", "prune_leaf", "prune_subdivision"]
OPS_CONEXO_EXTRA = ["add_edge"]  # solo fuera de --trees-only

_OP_FUNCS = {
    "add_leaf": op_add_leaf,
    "subdivide_edge": op_subdivide_edge,
    "prune_leaf": op_prune_leaf,
    "prune_subdivision": op_prune_subdivision,
    "add_edge": op_add_edge,
}


def operadores(trees_only: bool) -> List[str]:
    """Lista de operadores estructurales activos segun el modo.

    --trees-only restringe a operadores de arbol (decision 5): la palanca de
    mayor apalancamiento (lo que dejo a AMCS crackear el benchmark n=203).
    """
    if trees_only:
        return list(OPS_ARBOL)
    return list(OPS_ARBOL) + list(OPS_CONEXO_EXTRA)


def aplicar_operador(nombre: str, G: nx.Graph, rng) -> Optional[nx.Graph]:
    """Aplica el operador estructural `nombre` al grafo. None si no aplica."""
    f = _OP_FUNCS.get(nombre)
    if f is None:
        return None
    return f(G, rng)


# ---------------------------------------------------------------------------
# Familias de semillas por conjetura (decision 8). Constructores replicados de
# calibracion/ga_graphs.py (estrellas, caminos, cometas de doble cola, kites,
# dos-estrellas, peines). Para CAL-3 se agrega el esqueleto-cola P13.
# ---------------------------------------------------------------------------
def _estrella(n: int) -> nx.Graph:
    return nx.star_graph(n - 1)


def _camino(n: int) -> nx.Graph:
    return nx.path_graph(n)


def _cometa(n: int, t: Optional[int] = None) -> nx.Graph:
    """Estrella + cola de largo t (comet)."""
    if t is None:
        t = max(2, (n - 1) // 3)
    t = max(1, min(t, n - 2))
    G = nx.star_graph(n - t - 1)
    prev = 0
    base = n - t
    for k in range(t):
        G.add_edge(prev, base + k)
        prev = base + k
    return G


def _dtc(n: int, p: Optional[int] = None, q: Optional[int] = None) -> nx.Graph:
    """Cometa de doble cola DTC(n,p,q): estrella con dos colas p y q."""
    if p is None:
        p = max(1, (n - 4) // 3)
    if q is None:
        q = max(1, (n - 4) // 3)
    p = max(1, p)
    q = max(1, q)
    while n - p - q - 1 < 1 and (p > 1 or q > 1):
        if p >= q and p > 1:
            p -= 1
        elif q > 1:
            q -= 1
    G = nx.star_graph(max(1, n - p - q - 1))
    sig = G.number_of_nodes()
    prev = 0
    for _ in range(p):
        G.add_edge(prev, sig)
        prev = sig
        sig += 1
    prev = 0
    for _ in range(q):
        G.add_edge(prev, sig)
        prev = sig
        sig += 1
    return G


def _kite(n: int, w: Optional[int] = None) -> nx.Graph:
    """K_w + camino pendiente (kite)."""
    if w is None:
        w = min(5, max(3, n // 4))
    w = max(3, min(w, n - 1))
    G = nx.complete_graph(w)
    prev = 0
    for k in range(n - w):
        G.add_edge(prev, w + k)
        prev = w + k
    return G


def _dos_estrellas(n: int, a: Optional[int] = None) -> nx.Graph:
    """T(2,b): centros de dos estrellas unidos a un vertice nuevo (two-star)."""
    if a is None:
        a = max(3, (n - 1) // 2)
    a = max(3, min(a, n - 4))
    b = n - 1 - a
    if b < 2:
        b = 2
        a = n - 1 - b
    G = nx.star_graph(a - 1)
    off = a
    G.add_edges_from((off, off + k) for k in range(1, b))
    nuevo = G.number_of_nodes()
    G.add_edge(0, nuevo)
    G.add_edge(off, nuevo)
    return G


def _peine1(n: int) -> nx.Graph:
    """Espina P_k con una hoja por vertice (comb)."""
    k = n // 2
    G = nx.path_graph(k)
    for v in range(k):
        if G.number_of_nodes() < n:
            G.add_edge(v, G.number_of_nodes())
    return G


def _peine2(n: int) -> nx.Graph:
    """Espina P_k con pata de largo 2 por vertice (comb-2)."""
    k = max(2, n // 3)
    G = nx.path_graph(k)
    sig = k
    for v in range(k):
        if sig + 1 < n:
            G.add_edge(v, sig)
            G.add_edge(sig, sig + 1)
            sig += 2
    return G


def _lollipop(n: int, g: Optional[int] = None) -> nx.Graph:
    """K_g + camino (lollipop)."""
    if g is None:
        g = max(3, n // 3)
    g = max(3, min(g, n - 1))
    return nx.lollipop_graph(g, n - g)


def _tail_skeleton_p13(n: int) -> nx.Graph:
    """Semilla 'esqueleto-cola' para CAL-3: estrella central con dos colas

    largas, analoga a la receta del contraejemplo publicado n=203 (centro de
    S_grande unido a un extremo de P7 y a un extremo de P5). Aqui, dentro de la
    banda 10..40, se construye la version pequena: estrella central con dos
    caminos colgados cuyas longitudes suman ~n para forzar diametro alto (el
    regimen donde vive el margen de CAL-3). El nombre alude al P13 objetivo del
    esqueleto de cola cuando se escala fuera de banda.
    """
    # Reparte el "presupuesto" de vertices: nucleo estrella pequeno + dos colas.
    colas = max(3, (n - 3) // 2)
    p = colas
    q = n - 3 - colas
    if q < 2:
        q = 2
        p = max(2, n - 3 - q)
    centro_hojas = n - p - q - 1
    if centro_hojas < 1:
        centro_hojas = 1
        p = max(2, (n - 2) // 2)
        q = n - 2 - p
    G = nx.star_graph(centro_hojas)
    sig = G.number_of_nodes()
    prev = 0
    for _ in range(p):
        G.add_edge(prev, sig)
        prev = sig
        sig += 1
    prev = 0
    for _ in range(q):
        if sig >= n:
            break
        G.add_edge(prev, sig)
        prev = sig
        sig += 1
    return G


# Familias base compartidas por todas las conjeturas (estructuras extremales
# donde estas conjeturas espectrales mueren: estrellas, caminos, cometas...).
_FAMILIAS_BASE = [_estrella, _camino, _cometa, _dtc, _kite, _dos_estrellas,
                  _peine1, _peine2, _lollipop]


def familias_semilla(conj: str) -> list:
    """Constructores de semilla para la conjetura `conj` (cal1|cal2|cal3).

    Cada constructor es una funcion n->grafo. CAL-3 agrega el esqueleto-cola
    P13 (diametro alto), regimen donde vive su margen (decision 8).
    """
    conj = conj.lower().strip()
    fams = list(_FAMILIAS_BASE)
    if conj == "cal3":
        fams = [_tail_skeleton_p13] + fams  # prioriza diametro alto
    return fams


def semillas(conj: str, rng, cantidad: int,
             n_min: int = N_MIN, n_max: int = N_MAX) -> List[nx.Graph]:
    """Genera `cantidad` semillas conexas y validas para la conjetura.

    Barre tamanos y familias de forma reproducible dado `rng`. Descarta
    (y reintenta) construcciones desconexas o fuera de banda.
    """
    fams = familias_semilla(conj)
    out: List[nx.Graph] = []
    intentos = 0
    max_intentos = cantidad * 20 + 50
    while len(out) < cantidad and intentos < max_intentos:
        intentos += 1
        n = rng.randint(n_min, n_max)
        fam = fams[rng.randrange(len(fams))]
        try:
            G = norm(fam(n))
        except Exception:
            continue
        if valido(G, n_min, n_max, requiere_conexo=True):
            out.append(G)
    # Garantiza al menos un camino y una estrella (semillas triviales seguras).
    if not out:
        out.append(norm(nx.path_graph((n_min + n_max) // 2)))
    return out[:cantidad]

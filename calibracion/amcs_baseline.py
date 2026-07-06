"""Port fiel a Python/networkx del algoritmo AMCS (Vito–Stefanus 2023).

Fuente: github.com/valentinovito/Adaptive_MC_Search (amcs.sage + nmcs.sage),
paper arXiv 2306.07956. Es el "organismo baseline" obligatorio del GA (§9):
el estado del arte es el punto de partida de la población, no el rival.

Movimientos NMCS: agregar hoja / subdividir arista / (grafos conexos) agregar
arista del complemento. AMCS: poda aleatoria + profundidad y nivel adaptativos
al estancarse. Un score > 0 ⇔ contraejemplo (misma convención que el repo).
"""
import random

import networkx as nx


# ------------------------------------------------------ movimientos (nmcs.sage)

def agregar_hoja_aleatoria(G, rng):
    n = G.number_of_nodes()
    G.add_edge(rng.choice(list(G.nodes())), n)


def agregar_hoja(G, v):
    G.add_edge(v, G.number_of_nodes())


def subdividir_arista_aleatoria(G, rng):
    u, v = rng.choice(list(G.edges()))
    n = G.number_of_nodes()
    G.remove_edge(u, v)
    G.add_edge(u, n)
    G.add_edge(n, v)


def subdividir_arista(G, arista):
    u, v = arista
    n = G.number_of_nodes()
    G.remove_edge(u, v)
    G.add_edge(u, n)
    G.add_edge(n, v)


def quitar_hoja_aleatoria(G, rng):
    hojas = [v for v in G.nodes() if G.degree(v) == 1]
    if not hojas:
        return None
    hoja = rng.choice(hojas)
    G.remove_node(hoja)
    return hoja


def quitar_subdivision(G, rng):
    """Contrae un vértice de grado 2 (o quita una hoja si no hay)."""
    deg2 = [v for v in G.nodes() if G.degree(v) == 2]
    if not deg2:
        return quitar_hoja_aleatoria(G, rng)
    v = rng.choice(deg2)
    a, b = list(G.neighbors(v))
    G.remove_node(v)
    G.add_edge(a, b)  # si ya existía, no-op (grafo simple), igual que en Sage
    return v


def _renumerar(G):
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


# ------------------------------------------------------ NMCS (nmcs.sage)

def nmcs_arboles(G, depth, level, score, rng, es_padre=True):
    mejor, mejor_score = G, score(G)
    if level == 0:
        H = G.copy()
        for _ in range(depth):
            if rng.random() < 0.5:
                agregar_hoja_aleatoria(H, rng)
            else:
                subdividir_arista_aleatoria(H, rng)
        if score(H) > mejor_score:
            mejor = H
    else:
        candidatos = [("hoja", v) for v in G.nodes()] + [("subdiv", e) for e in G.edges()]
        for tipo, x in candidatos:
            H = G.copy()
            if tipo == "hoja":
                agregar_hoja(H, x)
            else:
                subdividir_arista(H, x)
            H = nmcs_arboles(H, depth, level - 1, score, rng, False)
            s = score(H)
            if s > mejor_score:
                mejor, mejor_score = H, s
                if G.number_of_nodes() > 20 and es_padre:
                    break
    return mejor


def nmcs_grafos_conexos(G, depth, level, score, rng, es_padre=True):
    mejor, mejor_score = G, score(G)
    if level == 0:
        H = G.copy()
        for _ in range(depth):
            r = rng.random()
            no_aristas = list(nx.non_edges(H))
            if r < 0.5 and no_aristas:
                H.add_edge(*rng.choice(no_aristas))
            elif r < 0.8:
                agregar_hoja_aleatoria(H, rng)
            else:
                subdividir_arista_aleatoria(H, rng)
        if score(H) > mejor_score:
            mejor = H
    else:
        candidatos = (
            [("hoja", v) for v in G.nodes()]
            + [("subdiv", e) for e in G.edges()]
            + [("arista", e) for e in nx.non_edges(G)]
        )
        for tipo, x in candidatos:
            H = G.copy()
            if tipo == "hoja":
                agregar_hoja(H, x)
            elif tipo == "subdiv":
                subdividir_arista(H, x)
            else:
                H.add_edge(*x)
            H = nmcs_grafos_conexos(H, depth, level - 1, score, rng, False)
            s = score(H)
            if s > mejor_score:
                mejor, mejor_score = H, s
                if G.number_of_nodes() > 20 and es_padre:
                    break
    return mejor


# ------------------------------------------------------ AMCS (amcs.sage)

def amcs(score, grafo_inicial=None, max_depth=5, max_level=3, solo_arboles=False,
         rng=None, verboso=False, max_n=None, umbral=1e-9):
    """AMCS fiel al repo. Devuelve el mejor grafo encontrado (score>0 ⇔ contraejemplo).

    `max_n` (extensión nuestra, opcional): cota superior de orden para usarlo
    como baseline del GA con n ∈ [10, 40]; None = sin cota, como el original.
    """
    rng = rng or random.Random()
    if grafo_inicial is None:
        grafo_inicial = nx.random_labeled_tree(5, seed=rng.randint(0, 10**9))
    nmcs = nmcs_arboles if solo_arboles else nmcs_grafos_conexos

    def score_capado(G):
        if max_n is not None and G.number_of_nodes() > max_n:
            return float("-inf")
        return score(G)

    depth, level = 0, 1
    min_orden = grafo_inicial.number_of_nodes()
    actual = grafo_inicial.copy()
    if verboso:
        print(f"[amcs] score inicial: {float(score_capado(actual)):.6f}", flush=True)
    while score_capado(actual) <= umbral and level <= max_level:  # Sage compara con 0 exacto-simbolico; en float, umbral
        siguiente = actual.copy()
        while siguiente.number_of_nodes() > min_orden:
            if rng.random() < depth / (depth + 1):
                if rng.random() < 0.5:
                    v = quitar_hoja_aleatoria(siguiente, rng)
                else:
                    v = quitar_subdivision(siguiente, rng)
                if v is None:
                    break
                siguiente = _renumerar(siguiente)
            else:
                break
        siguiente = nmcs(siguiente, depth, level, score_capado, rng)
        if verboso:
            tope = max(score_capado(siguiente), score_capado(actual))
            print(f"[amcs] nivel {level}, prof {depth}: mejor={float(tope):.6f} "
                  f"(n={siguiente.number_of_nodes()})", flush=True)
        if score_capado(siguiente) > score_capado(actual):
            actual = _renumerar(siguiente.copy())
            depth, level = 0, 1
        elif depth < max_depth:
            depth += 1
        else:
            depth = 0
            level += 1
    return _renumerar(actual)

"""Ensambla un corpus determinista de grafos simples conexos (n>=3) desde TODAS
las fuentes exigidas, deduplica por g6, y escribe parity/parity_corpus.csv con los
valores ground-truth de CAL-1/2/3 calculados por el código del repo (vía refs.py).

Fuentes:
  (a) formas cerradas Nivel-0 + estrellas star_graph(k) k=2..119 (n=3..120)
  (b) graph_atlas_g() filtrado a conexos n>=3 (debe dar 994)
  (c) todo best_g6 en calibracion/runs/ga_log.csv y ga_log_sin_seeds.csv
  (d) grafos aleatorios conexos sembrados con random.Random(20260706)
  (e) fixtures A/B/C decodificados de tests/fixtures/*.g6

Formato de floats: repr(float(x)) (round-trippable). mu,n,diam,k son enteros.
"""
import csv
import os
import random
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx
from networkx.generators.atlas import graph_atlas_g

import refs

FIXTURES = os.path.join(_RAIZ, "tests", "fixtures")
RUNS = os.path.join(_RAIZ, "calibracion", "runs")
SALIDA = os.path.join(_AQUI, "parity_corpus.csv")

HEADER = ["g6", "n", "lam1", "mu", "gap1", "lam2", "hc", "gap2",
          "pi", "diam", "k", "delta_k", "gap3"]

# corpus: g6 -> (grafo, conjunto de fuentes). counts por fuente para el reporte.
_corpus = {}          # g6 -> nx.Graph (reetiquetado)
_fuente_de = {}       # g6 -> primera fuente que lo aportó
_conteo_fuente = {}   # fuente -> nº de grafos NUEVOS aportados
_marcas = {"stars": set(), "completes": set()}  # g6's para sanity de detectores


def _agregar(G, fuente, marca=None):
    """Registra un grafo conexo n>=3 en el corpus (dedup por g6). Devuelve el g6."""
    if G.number_of_nodes() < 3 or not nx.is_connected(G):
        return None
    g6 = refs.g6_of(G)
    if marca is not None:
        _marcas[marca].add(g6)
    if g6 not in _corpus:
        _corpus[g6] = refs._relabel(G)
        _fuente_de[g6] = fuente
        _conteo_fuente[fuente] = _conteo_fuente.get(fuente, 0) + 1
    return g6


# ---------------------------------------------------------------- (a) formas cerradas
def fuente_a():
    cerrados = [
        nx.complete_graph(3), nx.complete_graph(10),
        nx.star_graph(4), nx.star_graph(9),
        nx.path_graph(4), nx.cycle_graph(5), nx.cycle_graph(6),
        nx.complete_bipartite_graph(2, 3), nx.complete_bipartite_graph(3, 3),
        nx.petersen_graph(),
    ]
    for G in cerrados:
        marca = "completes" if (G.number_of_edges() ==
                                G.number_of_nodes() * (G.number_of_nodes() - 1) // 2) else None
        _agregar(G, "a_cerradas", marca=marca)
    # completos K3, K10 marcados explícitamente para el sanity de |gap3|<1e-9
    _agregar(nx.complete_graph(3), "a_cerradas", marca="completes")
    _agregar(nx.complete_graph(10), "a_cerradas", marca="completes")
    # estrellas star_graph(k) k=2..119  => n=3..120  (detectores de igualdad exacta)
    for k in range(2, 120):
        _agregar(nx.star_graph(k), "a_cerradas", marca="stars")


# ---------------------------------------------------------------- (b) atlas
def fuente_b():
    atlas = graph_atlas_g()
    for G in atlas:
        if G.number_of_nodes() >= 3 and nx.is_connected(G):
            _agregar(G, "b_atlas")


# ---------------------------------------------------------------- (c) logs GA
def _leer_best_g6(ruta):
    salida = []
    if not os.path.exists(ruta):
        return salida
    with open(ruta, "r", encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            s = (fila.get("best_g6") or "").strip()
            if s:
                salida.append(s)
    return salida


def fuente_c():
    for nombre in ("ga_log.csv", "ga_log_sin_seeds.csv"):
        for s in _leer_best_g6(os.path.join(RUNS, nombre)):
            try:
                G = nx.from_graph6_bytes(s.encode())
            except Exception:
                continue
            _agregar(G, "c_ga_logs")


# ---------------------------------------------------------------- (d) aleatorios sembrados
def fuente_d():
    rng = random.Random(20260706)
    # barrido de n en [4,120] (denso) + un puñado hasta 300; ~1500 conexos.
    ns = list(range(4, 121)) + [140, 160, 180, 200, 220, 240, 260, 280, 300]
    objetivo = 1500
    nuevos = 0
    # varias pasadas barajando p para acumular ~1500 grafos conexos NUEVOS
    for _ in range(60):
        if nuevos >= objetivo:
            break
        for n in ns:
            if nuevos >= objetivo:
                break
            # p por encima del umbral de conexidad (~ln n / n) para maximizar conexos
            base = (2.0 + rng.random() * 6.0) / n
            p = min(0.95, max(base, rng.uniform(0.05, 0.6)))
            semilla = rng.randrange(1, 2**31 - 1)
            G = nx.gnp_random_graph(n, p, seed=semilla)
            if G.number_of_nodes() >= 3 and nx.is_connected(G):
                antes = len(_corpus)
                _agregar(G, "d_aleatorios")
                if len(_corpus) > antes:
                    nuevos += 1


# ---------------------------------------------------------------- (e) fixtures
def _cargar_fixture(nombre):
    ruta = os.path.join(FIXTURES, nombre)
    with open(ruta, "r", encoding="ascii") as f:
        s = f.read().strip().splitlines()[0].strip()
    return nx.from_graph6_bytes(s.encode())


_FIX = {}


def fuente_e():
    for clave, nombre in (("A", "fixture_l1mu.g6"),
                          ("B", "fixture_c4_estrellas.g6"),
                          ("C", "fixture_c2_203.g6")):
        G = _cargar_fixture(nombre)
        g6 = _agregar(G, "e_fixtures")
        _FIX[clave] = g6 if g6 is not None else refs.g6_of(G)


# ---------------------------------------------------------------- construir + escribir
def construir():
    fuente_a()
    fuente_b()
    fuente_c()
    fuente_d()
    fuente_e()


def escribir_csv():
    filas = []
    for g6 in _corpus:  # dict preserva orden de inserción (determinista)
        G = _corpus[g6]
        n = G.number_of_nodes()
        lam1, mu, gap1 = refs.cal1(G)
        lam2, hc, gap2 = refs.cal2(G)
        pi, diam, k, delta_k, gap3 = refs.cal3(G)  # todos conexos n>=3
        filas.append([
            g6, int(n),
            repr(float(lam1)), int(mu), repr(float(gap1)),
            repr(float(lam2)), repr(float(hc)), repr(float(gap2)),
            repr(float(pi)), int(diam), int(k), repr(float(delta_k)), repr(float(gap3)),
        ])
    with open(SALIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(filas)
    return filas


# ---------------------------------------------------------------- sanity
def _valores_por_g6(g6):
    G = _corpus[g6]
    lam1, mu, gap1 = refs.cal1(G)
    lam2, hc, gap2 = refs.cal2(G)
    pi, diam, k, delta_k, gap3 = refs.cal3(G)
    return dict(n=G.number_of_nodes(), gap1=gap1, gap2=gap2,
                diam=diam, gap3=gap3, lam1=lam1, mu=mu)


def sanity(n_filas):
    print(f"[schema] {','.join(HEADER)}")
    print(f"[total] filas={n_filas}")
    for fuente in ("a_cerradas", "b_atlas", "c_ga_logs", "d_aleatorios", "e_fixtures"):
        print(f"[fuente] {fuente}: {_conteo_fuente.get(fuente, 0)}")

    assert n_filas > 3000, f"corpus demasiado pequeño: {n_filas} <= 3000"

    A = _valores_por_g6(_FIX["A"])
    B = _valores_por_g6(_FIX["B"])
    C = _valores_por_g6(_FIX["C"])
    print(f"[fixture A] n={A['n']} gap1={A['gap1']!r}  (esperado >0 ~+0.0218)")
    print(f"[fixture B] n={B['n']} gap2={B['gap2']!r}  (esperado >0 ~+0.0795)")
    print(f"[fixture C] n={C['n']} diam={C['diam']} gap3={C['gap3']!r}  (esperado >0 ~+0.00028)")

    assert A["gap1"] > 0, "fixture A: gap1 no es > 0"
    assert abs(A["gap1"] - 0.0218) < 1e-3, f"fixture A: gap1={A['gap1']} lejos de +0.0218"
    assert B["gap2"] > 0, "fixture B: gap2 no es > 0"
    assert abs(B["gap2"] - 0.0795) < 1e-3, f"fixture B: gap2={B['gap2']} lejos de +0.0795"
    assert C["n"] == 203, f"fixture C: n={C['n']} != 203"
    assert C["diam"] == 12, f"fixture C: diam={C['diam']} != 12"
    assert C["gap3"] > 0, "fixture C: gap3 no es > 0"
    assert abs(C["gap3"] - 0.00028) < 1e-4, f"fixture C: gap3={C['gap3']} lejos de +0.00028"

    # detectores de igualdad exacta: estrellas |gap1|<1e-9, completos |gap3|<1e-9
    peor_estrella = 0.0
    for g6 in _marcas["stars"]:
        v = _valores_por_g6(g6)
        peor_estrella = max(peor_estrella, abs(v["gap1"]))
    print(f"[detector] estrellas={len(_marcas['stars'])} max|gap1|={peor_estrella!r}")
    assert peor_estrella < 1e-9, f"alguna estrella con |gap1|={peor_estrella} >= 1e-9"

    peor_completo = 0.0
    for g6 in _marcas["completes"]:
        v = _valores_por_g6(g6)
        peor_completo = max(peor_completo, abs(v["gap3"]))
    print(f"[detector] completos={len(_marcas['completes'])} max|gap3|={peor_completo!r}")
    assert peor_completo < 1e-9, f"algún completo con |gap3|={peor_completo} >= 1e-9"

    print("[ok] todos los chequeos de sanidad pasaron")


if __name__ == "__main__":
    construir()
    filas = escribir_csv()
    sanity(len(filas))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capa de CERTIFICACION proof-grade (precision y exactitud) de contraejemplos.

Esta capa NO participa en la busqueda. Corre SOLO sobre candidatos finales y
demuestra, de forma rigurosa (aritmetica exacta / intervalos con cota a
posteriori), que::

    gap(G) > 0   (en el sentido MATEMATICO, no como comparacion de float64)

Es la ULTIMA compuerta antes de afirmar "esto refuta la conjetura". El f64 del
buscador dice "candidato"; esta capa lo convierte en teorema (o lo rechaza).

Convenciones (identicas al oraculo `parity/refs.py`, `evaluators/agx_l1_mu.py`,
`calibracion/construir_fixtures_b_c.py` -- reetiquetado 0..n-1 en orden 'sorted'):

  CAL-1:  gap = (sqrt(n-1)+1) - (lam1 + mu)
          lam1 = mayor eigenvalor de la matriz de ADYACENCIA 0/1 (simetrica)
          mu   = cardinalidad del emparejamiento maximo (entero exacto)

  CAL-2:  gap = lam2 - Hc
          lam2 = 2do mayor eigenvalor de la ADYACENCIA  ( eigvalsh(A)[-2] )
          Hc   = sum_{uv in E} 2/(d_u + d_v)   (racional exacto)

  CAL-3:  gap = -(pi + delta_k)
          D    = matriz de DISTANCIAS entera (enteros; grafo conexo)
          Dmax = diametro = int(D.max())
          k    = floor(2*Dmax/3)
          delta_k = k-esimo MAYOR eigenvalor de D, indexado delta_desc[k-1]
                    (convencion de indice NEGATIVO de Python: k==0 en grafos
                     completos -> delta_desc[-1] = el MENOR eigenvalor)
          pi   = min_v( sum_u d(v,u) ) / (n-1)   (racional exacto, distancias enteras)

Metodo de la cota del eigenvalor (el unico termino no trivialmente exacto):

  * n <= UMBRAL_EXACTO (=40):  metodo "exacto-charpoly".
    Polinomio caracteristico de la matriz ENTERA via sympy `Matrix(...).charpoly`
    (coeficientes enteros exactos). El eigenvalor objetivo se aisla con un metodo
    CERTIFICADO (`CRootOf` -> intervalo racional aislante, refinado por biseccion
    de Sturm hasta ancho arbitrario). Se obtiene [lo, hi] que PROVABLEMENTE
    contiene al eigenvalor. Luego se prueba gap>0 de forma simbolica/exacta
    (p. ej. CAL-1: (sqrt(n-1)+1) - (hi_lam1 + mu) con sqrt(n-1) como numero
    algebraico de sympy; `expr.is_positive` es una decision exacta).

  * n >  UMBRAL_EXACTO:  metodo "mpmath-<dps>dps+residual".
    El polinomio caracteristico exacto es inviable (n=203). Se usa una cota
    RIGUROSA a posteriori: para una matriz simetrica M y un vector unitario x,
        min_i | lambda_i(M) - theta |  <=  || M x - theta x ||          (Weyl)
    con theta = x^T M x (cociente de Rayleigh). Es decir, M tiene un eigenvalor
    en el intervalo cerrado [theta - r, theta + r] con r = || M x - theta x ||.
    x se toma de numpy (aproximacion excelente), pero theta y r se calculan en
    mpmath a alta precision a partir de la matriz ENTERA exacta -> el intervalo
    es un teorema. Para fijar que el eigenvalor encerrado es EXACTAMENTE el
    k-esimo mayor, se certifican tambien los vecinos y se verifica que sus
    intervalos son disjuntos y estan correctamente ordenados (separacion).

Salida de `certificar(g6, conj)` (dict) incluye al menos:
    certificado : bool
    metodo      : "exacto-charpoly" | "mpmath-<dps>dps+residual"
    margen      : str  (cota INFERIOR racional/mpf, exacta, de gap; > 0 si certifica)
    detalle     : dict con los intermedios (lam/mu/Hc/pi, intervalos, residuos...)

Requiere: networkx, numpy, scipy, sympy, mpmath.
"""
from __future__ import annotations

import argparse
import os
import sys
from fractions import Fraction

import networkx as nx
import numpy as np

# --- raiz del repo en sys.path (para reutilizar convenciones si hiciera falta)
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import sympy as sp  # noqa: E402
from sympy import Integer, Rational, sqrt  # noqa: E402

import mpmath  # noqa: E402
from mpmath import mp, mpf  # noqa: E402

import scipy.sparse as _spsp  # noqa: E402
import scipy.sparse.csgraph as _csg  # noqa: E402

# ---------------------------------------------------------------------------
# Parametros de la capa
# ---------------------------------------------------------------------------
UMBRAL_EXACTO = 40          # n <= 40  -> polinomio caracteristico exacto
REFINAMIENTOS_CROOT = 12    # refinamientos del intervalo racional (ancho ~ 2^-12 * inicial)
DPS_GRANDE = 80             # digitos decimales de mpmath para el caso grande
VECINOS_SEPARACION = 2      # cuantos eigenvalores vecinos certificar a cada lado


# ---------------------------------------------------------------------------
# Utilidades de carga / convencion (identicas al oraculo)
# ---------------------------------------------------------------------------
def _grafo_de_g6(g6: str) -> nx.Graph:
    """graph6 (str, sin cabecera) -> Graph reetiquetado 0..n-1 en orden 'sorted'."""
    g6 = g6.strip()
    G = nx.from_graph6_bytes(g6.encode("ascii"))
    return nx.convert_node_labels_to_integers(G, ordering="sorted")


def _adyacencia_entera(G: nx.Graph) -> np.ndarray:
    """Matriz de adyacencia 0/1 entera, filas/cols en orden de etiqueta."""
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()), dtype=np.int64)


def _distancias_enteras(G: nx.Graph) -> np.ndarray:
    """Matriz de distancias entera (BFS por vertice). Grafo conexo => finita."""
    D = _csg.shortest_path(
        _spsp.csr_matrix(nx.to_scipy_sparse_array(G, nodelist=sorted(G.nodes()))),
        method="D",
        unweighted=True,
    )
    if not np.all(np.isfinite(D)):
        raise ValueError("grafo desconexo: matriz de distancias con infinitos")
    Di = np.rint(D).astype(np.int64)
    if not np.array_equal(D, Di.astype(float)):
        raise ValueError("distancias no enteras (grafo con pesos?)")
    return Di


def _mu_exacto(G: nx.Graph) -> int:
    """mu: cardinalidad del emparejamiento maximo (entero exacto).

    max_weight_matching(..., maxcardinality=True) devuelve un conjunto de aristas;
    su tamano es el numero de emparejamiento (NO maximal_matching, que es greedy).
    """
    return len(nx.max_weight_matching(G, maxcardinality=True))


def _hc_exacto(G: nx.Graph) -> Fraction:
    """Hc = sum_{uv in E} 2/(d_u + d_v) como Fraction EXACTO (grados enteros)."""
    tot = Fraction(0)
    for u, v in G.edges():
        tot += Fraction(2, G.degree[u] + G.degree[v])
    return tot


# ---------------------------------------------------------------------------
# Caso EXACTO (n <= UMBRAL_EXACTO): polinomio caracteristico entero + CRootOf
# ---------------------------------------------------------------------------
def _charpoly_entero(A: np.ndarray) -> sp.Poly:
    """Polinomio caracteristico de la matriz ENTERA A, con coeficientes enteros."""
    M = sp.Matrix(A.astype(int).tolist())
    x = sp.symbols("x")
    return sp.Poly(M.charpoly(x).as_expr(), x)


def _num_raices_reales(p: sp.Poly) -> int:
    """Numero de raices reales (con multiplicidad) via intervalos aislantes de Sturm."""
    return sum(m for (_, m) in p.intervals())


def _raices_reales_asc(p: sp.Poly):
    """Raices reales EXACTAS de p en orden ASCENDENTE, con multiplicidad.

    `sympy.polys.real_roots` usa aislamiento de Sturm (exacto): devuelve cada raiz
    como `CRootOf` (algebraica irracional), o como numero exacto cerrado
    (`Rational`, `0`, o un surdo tipo `2*sqrt(5)`) cuando es representable asi.
    """
    return sp.polys.real_roots(p)


def _bracket_certificado(raiz, refinamientos: int):
    """Bracket CERTIFICADO (lo, hi) que PROVABLEMENTE contiene a `raiz`, una raiz
    real EXACTA (CRootOf o numero algebraico cerrado). Casos:

      * `raiz.is_rational`          -> intervalo puntual [q, q] (exacto).
      * `CRootOf`                   -> intervalo racional aislante de Sturm,
                                       refinado por biseccion exacta.
      * otro algebraico cerrado     -> el propio valor simbolico como lo=hi=raiz
        (surdo, p.ej. 2*sqrt(5)):      (es exacto; la comparacion final la decide
                                        `sympy` de forma exacta con is_positive).

    lo, hi son objetos sympy (Rational o expresion algebraica) con lo <= raiz <= hi.
    """
    if getattr(raiz, "is_rational", False):
        q = raiz if raiz.is_Rational else sp.nsimplify(raiz)
        q = Rational(q)
        return q, q
    if isinstance(raiz, sp.polys.rootoftools.ComplexRootOf):
        itv = raiz._get_interval()
        for _ in range(refinamientos):
            itv = itv.refine()
        return Rational(itv.a), Rational(itv.b)
    # numero algebraico cerrado exacto (surdo): es EXACTO -> lo = hi = valor simbolico
    val = sp.sympify(raiz)
    return val, val


def _intervalo_certificado(p: sp.Poly, indice_real_asc: int, refinamientos: int):
    """(lo, hi, raiz) con lo <= (raiz real de indice `indice_real_asc`) <= hi,
    en orden ASCENDENTE entre las raices reales. lo/hi son exactos (racionales o
    simbolicos); el enclosure es un teorema (aislamiento de Sturm)."""
    rr = _raices_reales_asc(p)
    raiz = rr[indice_real_asc]
    lo, hi = _bracket_certificado(raiz, refinamientos)
    return lo, hi, raiz


def _certificar_cal1_exacto(G: nx.Graph) -> dict:
    n = G.number_of_nodes()
    mu = _mu_exacto(G)
    A = _adyacencia_entera(G)
    p = _charpoly_entero(A)
    nre = _num_raices_reales(p)
    # lam1 = MAYOR raiz real => indice ascendente nre-1
    lo, hi, _r = _intervalo_certificado(p, nre - 1, REFINAMIENTOS_CROOT)
    # gap = (sqrt(n-1)+1) - (lam1 + mu) >= (sqrt(n-1)+1) - (hi + mu)  [cota inferior]
    cota_inf = (sqrt(Integer(n - 1)) + 1) - (hi + Integer(mu))
    positivo = bool(cota_inf.is_positive)
    detalle = {
        "n": n, "mu": mu,
        "grado_charpoly": p.degree(),
        "n_raices_reales": nre,
        "lam1_intervalo_certificado": [str(lo), str(hi)],
        "lam1_hi_float": float(hi),
        "cota_termino_raiz": "sqrt(%d) (numero algebraico exacto)" % (n - 1),
        "gap_cota_inferior_simbolica": str(cota_inf),
        "gap_cota_inferior_float": float(cota_inf),
    }
    return {"certificado": positivo, "margen": str(cota_inf), "detalle": detalle}


def _certificar_cal2_exacto(G: nx.Graph) -> dict:
    n = G.number_of_nodes()
    Hc = _hc_exacto(G)                       # Fraction exacto
    Hc_s = Rational(Hc.numerator, Hc.denominator)
    A = _adyacencia_entera(G)
    p = _charpoly_entero(A)
    nre = _num_raices_reales(p)
    # lam2 = 2do MAYOR raiz real => indice ascendente nre-2
    lo, hi, _r = _intervalo_certificado(p, nre - 2, REFINAMIENTOS_CROOT)
    # gap = lam2 - Hc >= lo - Hc  [cota inferior]  (necesitamos lam2 > Hc)
    cota_inf = lo - Hc_s
    positivo = bool(cota_inf.is_positive)
    detalle = {
        "n": n,
        "Hc_exacto": str(Hc_s), "Hc_float": float(Hc_s),
        "grado_charpoly": p.degree(),
        "n_raices_reales": nre,
        "lam2_intervalo_certificado": [str(lo), str(hi)],
        "lam2_lo_float": float(lo),
        "gap_cota_inferior_racional": str(cota_inf),
        "gap_cota_inferior_float": float(cota_inf),
    }
    return {"certificado": positivo, "margen": str(cota_inf), "detalle": detalle}


def _certificar_cal3_exacto(G: nx.Graph) -> dict:
    """CAL-3 exacto (n pequeno): charpoly de la matriz de DISTANCIAS entera.

    Objetivo: delta_k = k-esimo MAYOR eigenvalor, delta_desc[k-1].
    En orden ASCENDENTE de raices reales, el k-esimo mayor tiene indice nre-k
    (y para k==0, Python -> delta_desc[-1] = el MENOR = indice ascendente 0).
    """
    n = G.number_of_nodes()
    D = _distancias_enteras(G)
    diam = int(D.max())
    k = (2 * diam) // 3
    # pi = min row-sum / (n-1)  (racional exacto)
    pi = Fraction(int(D.sum(axis=1).min()), n - 1)
    pi_s = Rational(pi.numerator, pi.denominator)
    p = _charpoly_entero(D)
    nre = _num_raices_reales(p)
    # indice ascendente del k-esimo mayor, replicando delta_desc[k-1] de numpy:
    #   descendente[k-1]  ==  ascendente[nre-k]   para k>=1
    #   k==0 -> delta_desc[-1] -> el menor -> ascendente[0]
    if k == 0:
        idx_asc = 0
    else:
        idx_asc = nre - k
    lo, hi, _r = _intervalo_certificado(p, idx_asc, REFINAMIENTOS_CROOT)
    # gap = -(pi + delta_k) >= -(pi + hi)  [cota inferior]  (necesitamos delta_k < -pi)
    cota_inf = -(pi_s + hi)
    positivo = bool(cota_inf.is_positive)
    detalle = {
        "n": n, "diametro": diam, "k": k,
        "pi_exacto": str(pi_s), "pi_float": float(pi_s),
        "grado_charpoly": p.degree(),
        "n_raices_reales": nre,
        "indice_ascendente_delta_k": idx_asc,
        "delta_k_intervalo_certificado": [str(lo), str(hi)],
        "delta_k_hi_float": float(hi),
        "gap_cota_inferior_racional": str(cota_inf),
        "gap_cota_inferior_float": float(cota_inf),
    }
    return {"certificado": positivo, "margen": str(cota_inf), "detalle": detalle}


# ---------------------------------------------------------------------------
# Caso GRANDE (n > UMBRAL_EXACTO): mpmath + cota a posteriori por residuo
# ---------------------------------------------------------------------------
def _enclosure_residuo(M_int: np.ndarray, x_f64: np.ndarray):
    """Enclosure RIGUROSO [theta - r, theta + r] de UN eigenvalor de la matriz
    simetrica ENTERA `M_int`, a partir de una aproximacion de eigenvector `x_f64`.

    theta = x^T M x (Rayleigh) y r = || M x - theta x || se computan a alta
    precision (mp.dps actual) desde los enteros exactos de M. Teorema (matriz
    simetrica): existe un eigenvalor verdadero en [theta - r, theta + r].

    Devuelve (theta, r) como mpf.
    """
    n = M_int.shape[0]
    # x normalizado en mpf
    x = mpmath.matrix([mpf(float(t)) for t in x_f64])
    nx2 = mpmath.norm(x)
    x = x / nx2
    # Dx exacto-en-precision (fila entera * vector mpf), theta = x·Dx
    Dx = mpmath.matrix(n, 1)
    for i in range(n):
        row = M_int[i]
        s = mpf(0)
        # solo entradas no nulas (matriz de distancias es densa, pero adyacencia rala)
        for j in range(n):
            v = int(row[j])
            if v:
                s += v * x[j]
        Dx[i] = s
    theta = mpmath.fdot([x[i] for i in range(n)], [Dx[i] for i in range(n)])
    # r = || Dx - theta x ||
    acc = mpf(0)
    for i in range(n):
        d = Dx[i] - theta * x[i]
        acc += d * d
    r = mpmath.sqrt(acc)
    return theta, r


def _certificar_grande_eigen(M_int, w_f64, V_f64, idx_desc_objetivo, vecinos):
    """Certifica el eigenvalor cuyo rango DESCENDENTE es `idx_desc_objetivo`
    (1-indexado; 1 = el mayor) mediante enclosures por residuo, y verifica
    separacion frente a `vecinos` a cada lado (para fijar el indice).

    Retorna dict con theta, r, [lo,hi] del objetivo y de sus vecinos, y un flag
    `separado` (True si los intervalos del objetivo y sus vecinos son disjuntos y
    estan ordenados => el enclosure corresponde INEQUIVOCAMENTE al k-esimo mayor).
    """
    n = M_int.shape[0]
    orden_desc = np.argsort(w_f64)[::-1]     # indices (en w ascendente) de mayor a menor
    total = n

    def enclosure_de_rango(rango_desc_1):
        asc = int(orden_desc[rango_desc_1 - 1])
        th, r = _enclosure_residuo(M_int, V_f64[:, asc])
        return th, r, th - r, th + r

    # objetivo
    th, r, lo, hi = enclosure_de_rango(idx_desc_objetivo)
    info_vecinos = []
    separado = True
    # rangos vecinos validos: [1..total]
    rango_lo = max(1, idx_desc_objetivo - vecinos)
    rango_hi = min(total, idx_desc_objetivo + vecinos)
    encls = {}
    for rr in range(rango_lo, rango_hi + 1):
        encls[rr] = enclosure_de_rango(rr)
    # verificar orden estricto descendente y disjuncion entre enclosures consecutivos
    rangos = sorted(encls.keys())
    for a, b in zip(rangos, rangos[1:]):
        th_a, r_a, lo_a, hi_a = encls[a]   # a es mas grande (rango menor => eigen mayor)
        th_b, r_b, lo_b, hi_b = encls[b]
        # eigen(a) > eigen(b): exigimos lo_a > hi_b (intervalos disjuntos y ordenados)
        if not (lo_a > hi_b):
            separado = False
        info_vecinos.append({
            "rango_desc": a, "theta": mpmath.nstr(th_a, 25),
            "residuo": mpmath.nstr(r_a, 6),
            "intervalo": [mpmath.nstr(lo_a, 20), mpmath.nstr(hi_a, 20)],
        })
    # incluir el ultimo rango en el reporte de vecinos
    th_l, r_l, lo_l, hi_l = encls[rangos[-1]]
    info_vecinos.append({
        "rango_desc": rangos[-1], "theta": mpmath.nstr(th_l, 25),
        "residuo": mpmath.nstr(r_l, 6),
        "intervalo": [mpmath.nstr(lo_l, 20), mpmath.nstr(hi_l, 20)],
    })
    return {
        "theta": th, "residuo": r, "lo": lo, "hi": hi,
        "separado": bool(separado),
        "vecinos": info_vecinos,
        "rango_desc_objetivo": idx_desc_objetivo,
    }


def _certificar_cal3_grande(G: nx.Graph, dps: int = DPS_GRANDE) -> dict:
    n = G.number_of_nodes()
    D = _distancias_enteras(G)
    diam = int(D.max())
    k = (2 * diam) // 3
    pi = Fraction(int(D.sum(axis=1).min()), n - 1)     # racional exacto
    # aproximaciones f64 (solo para los eigenVECTORES; el residuo es exacto-en-mpf)
    w, V = np.linalg.eigh(D.astype(np.float64))
    mp.dps = dps
    # rango descendente 1-indexado del objetivo:
    #   delta_desc[k-1] -> el k-esimo mayor -> rango k       (k>=1)
    #   k==0 -> delta_desc[-1] -> el MENOR   -> rango n
    rango = k if k >= 1 else n
    info = _certificar_grande_eigen(D, w, V, rango, VECINOS_SEPARACION)
    hi = info["hi"]
    pi_mpf = mpf(pi.numerator) / mpf(pi.denominator)
    cota_inf = -(pi_mpf + hi)                          # cota INFERIOR de gap
    # certifica si: cota_inf > 0 (rigurosa)  Y  el eigenvalor esta separado (indice fijado)
    positivo = bool(cota_inf > 0) and info["separado"]
    detalle = {
        "n": n, "diametro": diam, "k": k,
        "pi_exacto": "%d/%d" % (pi.numerator, pi.denominator),
        "pi_float": float(pi),
        "dps": dps,
        "rango_descendente_objetivo": rango,
        "delta_k_theta": mpmath.nstr(info["theta"], 25),
        "delta_k_residuo": mpmath.nstr(info["residuo"], 6),
        "delta_k_enclosure": [mpmath.nstr(info["lo"], 20), mpmath.nstr(info["hi"], 20)],
        "eigen_separado_de_vecinos": info["separado"],
        "vecinos_certificados": info["vecinos"],
        "gap_cota_inferior_mpf": mpmath.nstr(cota_inf, 20),
        "gap_cota_inferior_float": float(cota_inf),
        "nota_residuo": ("cota Weyl: existe eigenvalor en [theta-r, theta+r], "
                         "r = ||D x - theta x|| a %d dps; separacion de vecinos "
                         "fija el indice k" % dps),
    }
    return {"certificado": positivo, "margen": mpmath.nstr(cota_inf, 20), "detalle": detalle}


# CAL-1 / CAL-2 grandes (n>40) via mpmath+residuo, por completitud del contrato.
def _certificar_cal1_grande(G: nx.Graph, dps: int = DPS_GRANDE) -> dict:
    n = G.number_of_nodes()
    mu = _mu_exacto(G)
    A = _adyacencia_entera(G)
    w, V = np.linalg.eigh(A.astype(np.float64))
    mp.dps = dps
    # lam1 = MAYOR eigenvalor -> rango descendente 1
    info = _certificar_grande_eigen(A, w, V, 1, VECINOS_SEPARACION)
    hi = info["hi"]
    # gap = (sqrt(n-1)+1) - (lam1+mu) >= (sqrt(n-1)+1) - (hi+mu)
    cota_inf = (mpmath.sqrt(n - 1) + 1) - (hi + mu)
    positivo = bool(cota_inf > 0) and info["separado"]
    detalle = {
        "n": n, "mu": mu, "dps": dps,
        "lam1_theta": mpmath.nstr(info["theta"], 25),
        "lam1_residuo": mpmath.nstr(info["residuo"], 6),
        "lam1_enclosure": [mpmath.nstr(info["lo"], 20), mpmath.nstr(info["hi"], 20)],
        "eigen_separado_de_vecinos": info["separado"],
        "gap_cota_inferior_mpf": mpmath.nstr(cota_inf, 20),
        "gap_cota_inferior_float": float(cota_inf),
    }
    return {"certificado": positivo, "margen": mpmath.nstr(cota_inf, 20), "detalle": detalle}


def _certificar_cal2_grande(G: nx.Graph, dps: int = DPS_GRANDE) -> dict:
    n = G.number_of_nodes()
    Hc = _hc_exacto(G)
    A = _adyacencia_entera(G)
    w, V = np.linalg.eigh(A.astype(np.float64))
    mp.dps = dps
    # lam2 = 2do mayor -> rango descendente 2
    info = _certificar_grande_eigen(A, w, V, 2, VECINOS_SEPARACION)
    lo = info["lo"]
    Hc_mpf = mpf(Hc.numerator) / mpf(Hc.denominator)
    cota_inf = lo - Hc_mpf                              # gap = lam2 - Hc >= lo - Hc
    positivo = bool(cota_inf > 0) and info["separado"]
    detalle = {
        "n": n, "dps": dps,
        "Hc_exacto": "%d/%d" % (Hc.numerator, Hc.denominator), "Hc_float": float(Hc),
        "lam2_theta": mpmath.nstr(info["theta"], 25),
        "lam2_residuo": mpmath.nstr(info["residuo"], 6),
        "lam2_enclosure": [mpmath.nstr(info["lo"], 20), mpmath.nstr(info["hi"], 20)],
        "eigen_separado_de_vecinos": info["separado"],
        "gap_cota_inferior_mpf": mpmath.nstr(cota_inf, 20),
        "gap_cota_inferior_float": float(cota_inf),
    }
    return {"certificado": positivo, "margen": mpmath.nstr(cota_inf, 20), "detalle": detalle}


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------
_CONJ = {"cal1", "cal2", "cal3"}


def certificar(g6: str, conj: str, dps: int = DPS_GRANDE) -> dict:
    """Certifica RIGUROSAMENTE que gap(G) > 0 para el grafo `g6` y la conjetura `conj`.

    conj in {"cal1", "cal2", "cal3"}. Devuelve dict con:
        certificado : bool  (True <=> gap>0 demostrado)
        metodo      : "exacto-charpoly" | "mpmath-<dps>dps+residual"
        margen      : str   (cota inferior EXACTA de gap; racional o mpf)
        detalle     : dict
        conj, g6, n : eco de entrada
    Nunca lanza por un g6 valido; errores estructurales -> certificado False + error.
    """
    conj = conj.lower().strip()
    if conj not in _CONJ:
        raise ValueError("conj debe ser uno de %s; llego %r" % (sorted(_CONJ), conj))
    try:
        G = _grafo_de_g6(g6)
    except Exception as e:  # g6 corrupto
        return {"certificado": False, "metodo": "n/a",
                "margen": "n/a", "detalle": {"error": "g6_invalido: %s" % e},
                "conj": conj, "g6": g6, "n": None}

    n = G.number_of_nodes()
    if not nx.is_connected(G):
        return {"certificado": False, "metodo": "n/a", "margen": "n/a",
                "detalle": {"error": "grafo_desconexo"}, "conj": conj, "g6": g6, "n": n}

    exacto = n <= UMBRAL_EXACTO
    metodo = "exacto-charpoly" if exacto else ("mpmath-%ddps+residual" % dps)

    if exacto:
        if conj == "cal1":
            res = _certificar_cal1_exacto(G)
        elif conj == "cal2":
            res = _certificar_cal2_exacto(G)
        else:
            res = _certificar_cal3_exacto(G)
    else:
        if conj == "cal1":
            res = _certificar_cal1_grande(G, dps=dps)
        elif conj == "cal2":
            res = _certificar_cal2_grande(G, dps=dps)
        else:
            res = _certificar_cal3_grande(G, dps=dps)

    res.update({"metodo": metodo, "conj": conj, "g6": G_a_g6(G), "n": n})
    return res


def G_a_g6(G: nx.Graph) -> str:
    return nx.to_graph6_bytes(
        nx.convert_node_labels_to_integers(G, ordering="sorted"), header=False
    ).decode("ascii").strip()


# ---------------------------------------------------------------------------
# CLI  (tambien __main__ de verify.py, ver enunciado deliverable 2)
# ---------------------------------------------------------------------------
_FIXTURES = {
    "A": ("fixture_l1mu.g6", "cal1", "n=18"),
    "B": ("fixture_c4_estrellas.g6", "cal2", "n=35"),
    "C": ("fixture_c2_203.g6", "cal3", "n=203"),
}


def _imprimir_cert(cert: dict, etiqueta: str = "") -> None:
    import json
    cab = ("=== CERTIFICADO %s (conj=%s, n=%s) ===" %
           (etiqueta or "", cert.get("conj"), cert.get("n")))
    print(cab)
    print("  certificado :", cert["certificado"])
    print("  metodo      :", cert["metodo"])
    print("  margen (cota inferior EXACTA de gap):")
    print("               ", cert["margen"])
    print("  detalle     :")
    print(json.dumps(cert["detalle"], indent=4, ensure_ascii=False,
                     default=str))
    print()


def _ruta_fixture(nombre: str) -> str:
    return os.path.join(_RAIZ, "tests", "fixtures", nombre)


def _leer_g6(ruta: str) -> str:
    with open(ruta, "r", encoding="ascii") as f:
        return f.read().strip()


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="verify.py",
        description="Certificacion proof-grade de contraejemplos (gap>0 exacto).",
    )
    ap.add_argument("--g6", type=str, default=None,
                    help="graph6 (str, sin cabecera) del candidato a certificar")
    ap.add_argument("--conj", type=str, default=None,
                    choices=["cal1", "cal2", "cal3"],
                    help="conjetura objetivo")
    ap.add_argument("--dps", type=int, default=DPS_GRANDE,
                    help="digitos mpmath para el caso grande (n>%d)" % UMBRAL_EXACTO)
    ap.add_argument("--fixtures", action="store_true",
                    help="certifica los 3 fixtures publicados A/B/C de tests/fixtures/")
    args = ap.parse_args(argv)

    if args.fixtures:
        ok_todos = True
        for etq, (nombre, conj, tam) in _FIXTURES.items():
            ruta = _ruta_fixture(nombre)
            if not os.path.exists(ruta):
                print("[FALTA] %s: %s no existe" % (etq, ruta))
                ok_todos = False
                continue
            g6 = _leer_g6(ruta)
            cert = certificar(g6, conj, dps=args.dps)
            _imprimir_cert(cert, "%s [%s, %s]" % (etq, nombre, tam))
            ok_todos = ok_todos and cert["certificado"]
        print("=== RESUMEN: %s ===" %
              ("TODOS CERTIFICADOS (gap>0 demostrado)" if ok_todos
               else "ALGUN FIXTURE NO CERTIFICO"))
        return 0 if ok_todos else 1

    if not args.g6 or not args.conj:
        ap.error("indique --g6 <str> --conj cal1|cal2|cal3  (o use --fixtures)")

    cert = certificar(args.g6, args.conj, dps=args.dps)
    _imprimir_cert(cert)
    return 0 if cert["certificado"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())

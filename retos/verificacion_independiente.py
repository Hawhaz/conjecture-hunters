#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VERIFICACION INDEPENDIENTE Y ADVERSARIAL de la refutacion de la Conjetura 1
de Jia-Song (rho + d_2 >= B(n), abierta).

Este script es un SEGUNDO metodo, deliberadamente distinto de
`retos/refutacion_jia_song.py`, para verificar de forma independiente y
adversarial que la familia K_1 v 2K_r (el mas chico = grafo de la amistad F_2,
n=5) refuta la conjetura, i.e. rho + d_2 < B(n).

Diferencias metodologicas frente al script de refutacion (para no heredar bugs):
  * rho (lejania): se construyen las distancias con
    nx.all_pairs_shortest_path_length (BFS por diccionarios), NO con
    floyd_warshall_numpy. rho = max_v transmision(v)/(n-1).
  * d_2 (2do mayor eigenvalor de la matriz de distancias):
      - float64 via numpy.linalg.eigvalsh (matriz simetrica), ordenado desc, [1];
      - EXACTO via sympy Matrix(...).eigenvals()  (diccionario autovalor->mult),
        NO via charpoly()+real_roots (que es lo que usa el otro script).
  * Comparacion rho+d_2 vs B(n) en TRES precisiones: float64, mpmath 50 digitos
    y EXACTA (sympy, decision de numeros algebraicos con is_negative).
  * Auditoria adversarial: conexidad, exclusion de {K_n, K_n-e}, no-isomorfismo
    de F_2 con K_5 y K_5-e, espectro de distancias completo (chequeo de
    multiplicidad en la cima => d_2 != d_1), signo del radical de B(n), e igualdad
    B(n) = rho+d_2 EXACTA en el grafo extremal reclamado K_n - e.

Uso:  python retos/verificacion_independiente.py
Salida: espectros, la comparacion en 3 precisiones y todos los chequeos de
        auditoria en verde, o el hueco encontrado.
NO usa ni importa refutacion_jia_song.py: es un cross-check autonomo.
"""
import sys

import networkx as nx
import numpy as np
import sympy as sp
import mpmath as mp

mp.mp.dps = 50  # 50 digitos decimales para la capa mpmath

# ---------------------------------------------------------------------------
# Construccion de los grafos (dos construcciones distintas + chequeo isomorfo)
# ---------------------------------------------------------------------------

def K1_join_2Kr_A(r):
    """K_1 v (2 K_r) por union disjunta + vertice universal (construccion A)."""
    G = nx.disjoint_union(nx.complete_graph(r), nx.complete_graph(r))
    u = G.number_of_nodes()               # nuevo vertice universal, id = 2r
    G.add_node(u)
    for v in range(u):
        G.add_edge(u, v)
    return G


def K1_join_2Kr_B(r):
    """Misma familia por una ruta INDEPENDIENTE: nx.join / etiquetas explicitas.

    Vertices: 'u' (universal), ('a',i) para i<r (clique A), ('b',j) para j<r
    (clique B). Aristas: dentro de A, dentro de B, y u-todos. NO hay aristas
    A-B (por eso el diametro es 2 y no es K_n). Esto reconstruye el grafo sin
    reutilizar la construccion A, para descartar un bug de construccion.
    """
    G = nx.Graph()
    u = "u"
    A = [("a", i) for i in range(r)]
    B = [("b", j) for j in range(r)]
    G.add_node(u)
    G.add_nodes_from(A)
    G.add_nodes_from(B)
    for i in range(r):
        for j in range(i + 1, r):
            G.add_edge(A[i], A[j])
            G.add_edge(B[i], B[j])
    for w in A + B:
        G.add_edge(u, w)
    return G


# ---------------------------------------------------------------------------
# rho por BFS de diccionarios (all_pairs_shortest_path_length) -- metodo 2
# ---------------------------------------------------------------------------

def rho_via_bfs_dicts(G):
    """rho = max sobre v de (suma de distancias de v a los demas)/(n-1),
    usando all_pairs_shortest_path_length (BFS), devuelto EXACTO (Rational)."""
    n = G.number_of_nodes()
    d = dict(nx.all_pairs_shortest_path_length(G))
    transmissions = {}
    for v in G.nodes():
        s = sum(d[v][w] for w in G.nodes() if w != v)
        transmissions[v] = s
    max_trans = max(transmissions.values())
    rho = sp.Rational(int(max_trans), n - 1)
    return rho, transmissions


# ---------------------------------------------------------------------------
# Matriz de distancias entera (orden de nodos fijo), y espectros
# ---------------------------------------------------------------------------

def distance_matrix_int(G):
    """Matriz de distancias entera via BFS-dicts, orden de nodos fijo."""
    nodes = list(G.nodes())
    idx = {v: k for k, v in enumerate(nodes)}
    n = len(nodes)
    d = dict(nx.all_pairs_shortest_path_length(G))
    D = np.zeros((n, n), dtype=np.int64)
    for v in nodes:
        for w in nodes:
            D[idx[v], idx[w]] = d[v][w]
    return D, nodes


def d2_float(D):
    """2do mayor eigenvalor por numpy.linalg.eigvalsh (simetrica), float64."""
    ev = np.linalg.eigvalsh(D.astype(float))   # ascendente
    ev_desc = np.sort(ev)[::-1]
    return ev_desc  # devolvemos el espectro entero ordenado desc


def d2_exact_eigenvals(D):
    """2do mayor eigenvalor EXACTO via sympy Matrix.eigenvals() (dict a->mult).

    Distinto de charpoly()+real_roots. Se expande el diccionario a lista con
    multiplicidad, se ordena descendente por valor numerico y se toma el [1].
    Todos los autovalores de una matriz simetrica real son reales, asi que el
    orden numerico es total.
    """
    M = sp.Matrix(D.tolist())
    eig = M.eigenvals()  # {autovalor: multiplicidad}
    flat = []
    for val, mult in eig.items():
        val = sp.nsimplify(val, rational=False)
        for _ in range(int(mult)):
            flat.append(sp.simplify(val))
    # orden descendente por valor numerico (todos reales)
    flat_sorted = sorted(flat, key=lambda z: float(sp.N(z, 40)), reverse=True)
    return flat_sorted


def B_exact(n):
    """B(n) = n/(n-1) + (n-1 - sqrt((n-1)^2 + 8))/2  (OJO: MENOS antes del radical)."""
    return sp.Rational(n, n - 1) + (sp.Integer(n - 1) - sp.sqrt((n - 1) ** 2 + 8)) / 2


def B_mpmath(n):
    n = mp.mpf(n)
    return n / (n - 1) + (n - 1 - mp.sqrt((n - 1) ** 2 + 8)) / 2


# ---------------------------------------------------------------------------
# Auditoria adversarial de hipotesis
# ---------------------------------------------------------------------------

def audit_hypotheses(G, n, label):
    """Devuelve (ok, lineas) con los chequeos de hipotesis de la conjetura."""
    lines = []
    ok = True

    connected = nx.is_connected(G)
    lines.append(f"    conexo?                 {connected}")
    ok = ok and connected

    n_ok = n >= 4
    lines.append(f"    n >= 4?                 {n_ok}  (n={n})")
    ok = ok and n_ok

    # No es K_n
    Kn = nx.complete_graph(n)
    is_Kn = nx.is_isomorphic(G, Kn)
    lines.append(f"    NO es K_n?              {not is_Kn}")
    ok = ok and (not is_Kn)

    # No es K_n - e
    Kn_e = nx.complete_graph(n)
    Kn_e.remove_edge(0, 1)
    is_Kn_e = nx.is_isomorphic(G, Kn_e)
    lines.append(f"    NO es K_n - e?          {not is_Kn_e}")
    ok = ok and (not is_Kn_e)

    # info extra: aristas, diametro
    m = G.number_of_edges()
    diam = nx.diameter(G)
    lines.append(f"    (aristas={m}, C(n,2)={n*(n-1)//2}, diametro={diam})")

    return ok, lines


def spectrum_report(vals_exact):
    """Cadena legible del espectro exacto con multiplicidades, orden desc."""
    # agrupar por valor (ya vienen simplificados)
    grouped = []
    for v in vals_exact:
        for g in grouped:
            if sp.simplify(g[0] - v) == 0:
                g[1] += 1
                break
        else:
            grouped.append([v, 1])
    parts = []
    for val, mult in grouped:
        fv = float(sp.N(val, 30))
        parts.append(f"{sp.nsimplify(val)} (~{fv:.6f}) x{mult}")
    return grouped, parts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def analyze(r, verbose=True):
    n = 2 * r + 1

    # Construccion A y B, chequeo de isomorfismo (independencia de construccion)
    GA = K1_join_2Kr_A(r)
    GB = K1_join_2Kr_B(r)
    iso = nx.is_isomorphic(GA, GB)

    # rho por BFS-dicts en la construccion A
    rho, trans = rho_via_bfs_dicts(GA)

    # matriz de distancias + espectros
    D, nodes = distance_matrix_int(GA)
    ev_desc_float = d2_float(D)
    vals_exact = d2_exact_eigenvals(D)

    d1_exact = vals_exact[0]
    d2_exact = vals_exact[1]
    d1_float = ev_desc_float[0]
    d2_float_val = ev_desc_float[1]

    s_exact = sp.simplify(rho + d2_exact)          # rho + d_2 exacto
    b_exact = B_exact(n)
    margin_exact = sp.simplify(b_exact - s_exact)  # B - (rho+d2); >0 <=> viola

    # decision exacta de numeros algebraicos
    violates_exact = bool((s_exact - b_exact).is_negative)  # rho+d2 < B

    # mpmath 50 dig
    d2_mp = mp.mpf(str(sp.N(d2_exact, 60)))
    rho_mp = mp.mpf(rho.p) / mp.mpf(rho.q)
    s_mp = rho_mp + d2_mp
    b_mp = B_mpmath(n)
    violates_mp = s_mp < b_mp

    # float64
    s_f = float(rho) + float(d2_float_val)
    b_f = float(B_mpmath(n))
    violates_f = s_f < b_f

    result = {
        "r": r, "n": n, "iso": iso, "rho": rho,
        "d1_exact": d1_exact, "d2_exact": d2_exact,
        "d1_float": d1_float, "d2_float": d2_float_val,
        "ev_desc_float": ev_desc_float, "vals_exact": vals_exact,
        "s_exact": s_exact, "b_exact": b_exact, "margin_exact": margin_exact,
        "violates_exact": violates_exact,
        "s_mp": s_mp, "b_mp": b_mp, "violates_mp": violates_mp,
        "s_f": s_f, "b_f": b_f, "violates_f": violates_f,
        "GA": GA, "trans": trans,
    }
    return result


def main():
    print("=" * 78)
    print("VERIFICACION INDEPENDIENTE (2do metodo) — Conjetura 1 de Jia-Song")
    print("  Conjetura:  rho + d_2  >=  B(n) := n/(n-1) + (n-1 - sqrt((n-1)^2+8))/2")
    print("  (G conexo, G no en {K_n, K_n-e}, n>=4;  igualdad sii G = K_n - e)")
    print("  Contraejemplo: K_1 v 2K_r (n=2r+1). r=2 => grafo de la amistad F_2 (n=5).")
    print("  Metodos: rho via BFS-dicts (all_pairs_shortest_path_length);")
    print("           d_2 via numpy.eigvalsh (float) Y sympy .eigenvals() (exacto).")
    print("=" * 78)

    targets = [2, 3, 5]  # F_2 (n=5), K_1 v 2K_3 (n=7), K_1 v 2K_5 (n=11)
    all_ok = True
    all_violate = True

    for r in targets:
        R = analyze(r)
        n = R["n"]
        name = "F_2 (amistad)" if r == 2 else f"K_1 v 2K_{r}"
        print(f"\n{'-'*78}")
        print(f"### {name}   (r={r}, n={n})")
        print(f"{'-'*78}")

        # --- Auditoria de hipotesis ---
        ok_h, lines = audit_hypotheses(R["GA"], n, name)
        print("  [AUDITORIA hipotesis de la conjetura]")
        for ln in lines:
            print(ln)
        # chequeo de construccion independiente
        print(f"    construccion A ~= B?    {R['iso']}  (dos rutas de construccion coinciden)")
        ok_h = ok_h and R["iso"]

        # --- rho ---
        print("  [rho: lejania por BFS-dicts]")
        print(f"    rho = max_v trans(v)/(n-1) = {R['rho']} = {float(R['rho']):.6f}"
              f"   (esperado 3/2 = 1.5)")
        rho_is_32 = sp.simplify(R["rho"] - sp.Rational(3, 2)) == 0
        print(f"    rho == 3/2 ?            {rho_is_32}")
        ok_h = ok_h and rho_is_32

        # --- Espectro de distancias completo (exacto) ---
        grouped, parts = spectrum_report(R["vals_exact"])
        print("  [ESPECTRO de distancias completo, exacto, orden descendente]")
        for p in parts:
            print(f"    {p}")
        # multiplicidad en la cima: d_1 debe ser SIMPLE (d_2 != d_1)
        top_val, top_mult = grouped[0]
        d2_distinct = (top_mult == 1) and (sp.simplify(R["d1_exact"] - R["d2_exact"]) != 0)
        print(f"    d_1 (mayor) = {sp.nsimplify(R['d1_exact'])} ~ {float(sp.N(R['d1_exact'],30)):.6f}, mult={top_mult}")
        print(f"    d_2 (2do mayor) = {sp.nsimplify(R['d2_exact'])} ~ {float(sp.N(R['d2_exact'],30)):.6f}")
        print(f"    d_2 es INEQUIVOCAMENTE el 2do mayor (d_1 simple, d_2!=d_1)?  {d2_distinct}")
        ok_h = ok_h and d2_distinct

        # cross-check float vs exacto del propio d_2
        d2_fe = abs(float(sp.N(R["d2_exact"], 30)) - float(R["d2_float"]))
        print(f"    |d_2(exacto) - d_2(numpy float)| = {d2_fe:.2e}  (paridad de metodos d_2)")
        ok_h = ok_h and (d2_fe < 1e-9)

        # --- Comparacion en 3 precisiones ---
        print("  [rho + d_2  vs  B(n)  en TRES precisiones]")
        print(f"    EXACTO :  rho+d_2 = {sp.nsimplify(R['s_exact'])}"
              f"   B(n) = {sp.nsimplify(R['b_exact'])}")
        print(f"              B - (rho+d_2) = {sp.nsimplify(R['margin_exact'])}"
              f"   ( >0 y (rho+d2)<B por is_negative: {R['violates_exact']} )")
        print(f"    float64:  rho+d_2 = {R['s_f']:.15f}   B(n) = {R['b_f']:.15f}"
              f"   ( < ? {R['violates_f']} )")
        print(f"    mp(50) :  rho+d_2 = {mp.nstr(R['s_mp'], 30)}")
        print(f"              B(n)     = {mp.nstr(R['b_mp'], 30)}")
        print(f"              B-(rho+d2)= {mp.nstr(R['b_mp'] - R['s_mp'], 30)}"
              f"   ( < ? {R['violates_mp']} )")

        three_agree = R["violates_exact"] and R["violates_mp"] and R["violates_f"]
        print(f"    LAS TRES precisiones dan rho+d_2 < B(n)?  {three_agree}")

        node_ok = ok_h and three_agree
        print(f"  >>> {name}: hipotesis+espectro OK y viola la cota en 3 precisiones:  {node_ok}")
        all_ok = all_ok and ok_h
        all_violate = all_violate and three_agree

    # --- Auditoria del extremal reclamado: K_n - e alcanza B(n) EXACTO ---
    print(f"\n{'='*78}")
    print("### AUDITORIA del grafo extremal reclamado por la conjetura: K_n - e")
    print(f"{'='*78}")
    print("  La conjetura dice: igualdad rho+d_2 = B(n) sii G = K_n - e.")
    print("  Verificamos rho+d_2(K_n - e) == B(n) EXACTAMENTE (con el MISMO 2do metodo).")
    extremal_ok = True
    for n in (5, 7, 9, 11):
        H = nx.complete_graph(n)
        H.remove_edge(0, 1)
        rhoH, _ = rho_via_bfs_dicts(H)
        DH, _ = distance_matrix_int(H)
        valsH = d2_exact_eigenvals(DH)
        sH = sp.simplify(rhoH + valsH[1])
        bH = B_exact(n)
        eq = sp.simplify(sH - bH) == 0
        extremal_ok = extremal_ok and eq
        print(f"  K_{n}-e:  rho={rhoH}={float(rhoH):.4f}  d_2={sp.nsimplify(valsH[1])} "
              f"~{float(sp.N(valsH[1],30)):.6f}")
        print(f"          rho+d_2 = {sp.nsimplify(sH)} = {float(sH):.6f}"
              f"   B({n}) = {sp.nsimplify(bH)} = {float(bH):.6f}   IGUALES? {eq}")

    # --- Auditoria del signo del radical de B(n) ---
    print(f"\n{'='*78}")
    print("### AUDITORIA del signo del radical en B(n)")
    print(f"{'='*78}")
    # con MENOS: B(n) < n/(n-1) (la parte del radical resta). Con MAS seria absurdo.
    n = 5
    b_minus = B_exact(5)                                  # correcto
    b_plus = sp.Rational(5, 4) + (sp.Integer(4) + sp.sqrt(16 + 8)) / 2  # variante equivocada
    print(f"  B(5) con  -sqrt : {sp.nsimplify(b_minus)} = {float(b_minus):.6f}  "
          f"(< n/(n-1)={float(sp.Rational(5,4)):.4f}? {float(b_minus) < 1.25})")
    print(f"  B(5) con  +sqrt : {sp.nsimplify(b_plus)} = {float(b_plus):.6f}  "
          f"(absurdo como cota inferior de rho+d_2; se descarta)")
    sign_ok = (sp.simplify(b_minus - (sp.Rational(13,4) - sp.sqrt(6))) == 0)
    print(f"  B(5) == 13/4 - sqrt(6) (forma cerrada del doc)?  {sign_ok}")

    # --- F_2 no isomorfo a K_5 ni K_5-e (chequeo dedicado, adversarial) ---
    print(f"\n{'='*78}")
    print("### AUDITORIA dedicada: F_2 (grafo de la amistad) vs K_5 y K_5 - e")
    print(f"{'='*78}")
    F2 = K1_join_2Kr_A(2)
    K5 = nx.complete_graph(5)
    K5e = nx.complete_graph(5); K5e.remove_edge(0, 1)
    iso_K5 = nx.is_isomorphic(F2, K5)
    iso_K5e = nx.is_isomorphic(F2, K5e)
    deg_seq_F2 = sorted((d for _, d in F2.degree()), reverse=True)
    deg_seq_K5 = sorted((d for _, d in K5.degree()), reverse=True)
    deg_seq_K5e = sorted((d for _, d in K5e.degree()), reverse=True)
    print(f"  F_2:    aristas={F2.number_of_edges()}, grados={deg_seq_F2}")
    print(f"  K_5:    aristas={K5.number_of_edges()}, grados={deg_seq_K5}   iso con F_2? {iso_K5}")
    print(f"  K_5-e:  aristas={K5e.number_of_edges()}, grados={deg_seq_K5e}   iso con F_2? {iso_K5e}")
    f2_admissible = (not iso_K5) and (not iso_K5e)
    print(f"  F_2 admisible (no en {{K_5, K_5-e}})?  {f2_admissible}")

    # ----------------------------------------------------------------------
    # VEREDICTO
    # ----------------------------------------------------------------------
    print(f"\n{'='*78}")
    print("VEREDICTO")
    print(f"{'='*78}")
    print(f"  Todas las hipotesis + espectros OK (F_2, K1v2K3, K1v2K5):   {all_ok}")
    print(f"  Los 3 grafos violan la cota en float64/mp50/exacto:         {all_violate}")
    print(f"  K_n - e alcanza B(n) EXACTO (extremal reclamado, n=5..11):  {extremal_ok}")
    print(f"  Signo del radical en B(n) correcto (menos):                 {sign_ok}")
    print(f"  F_2 admisible (no isomorfo a K_5 ni K_5-e):                 {f2_admissible}")
    verdict = all_ok and all_violate and extremal_ok and sign_ok and f2_admissible
    print(f"\n  >>> REFUTACION VERIFICADA INDEPENDIENTEMENTE:  {verdict}")
    if verdict:
        print("  >>> PASS: la refutacion se sostiene bajo un 2do metodo y sobrevive")
        print("      la auditoria adversarial. K_n - e NO minimiza rho+d_2 => la")
        print("      Conjetura 1 de Jia-Song es FALSA (contraejemplo minimo F_2, n=5).")
    else:
        print("  >>> FAIL: se encontro una inconsistencia; revisar arriba.")
    return 0 if verdict else 1


if __name__ == "__main__":
    sys.exit(main())

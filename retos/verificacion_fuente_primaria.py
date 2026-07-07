#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificación de FUENTE PRIMARIA de la refutación Jia-Song (integridad).

Responde, con aritmética EXACTA y reproducible, a la pregunta "¿de verdad
refutamos esto o se copió?": recomputa desde cero el valor de rho+d2 en los
grafos clave y lo confronta con el enunciado *verbatim* del paper primario y del
survey, dejando ver una discrepancia de transcripción en el CASO DE IGUALDAD que
NO afecta la refutación de la DESIGUALDAD.

Hechos que este script establece (sin punto flotante en la decisión final):

  Enunciado primario  — Jia & Song 2018, *J. Inequal. Appl.* 2018:69,
  **Conjecture 3.8** (el survey Aouchiche-Rather 2024 lo renumera "Conjecture 1"):
      Para G conexo, G !≅ K_n, K_n - e, n>=4:
          rho + d2 >= n/(n-1) + (n-1 - sqrt((n-1)^2 + 8))/2 =: B(n)
      con igualdad ssi  G ≅ K_n - 2e  (2e = dos aristas de un emparejamiento).   <-- PRIMARIO
      (El survey de 2024 lo escribe con igualdad ssi  G ≅ K_n - e.)              <-- SURVEY

  Comprobación numérica exacta (este script):
    * B(n) coincide VERBATIM con el RHS del primario.
    * rho+d2(K_n - e)  = B(n)   EXACTO           -> K_n - e SÍ alcanza la cota.
    * rho+d2(K_n - 2e) = n/(n-1) != B(n)         -> el grafo de igualdad del
                                                    PRIMARIO NO alcanza su cota
                                                    (inconsistencia de transcripción).
    * rho+d2(F2) < B(5)  y  rho+d2(K1 v 2K5) < B(11)  -> REFUTACIÓN de la
      DESIGUALDAD, robusta a cómo se lea el caso de igualdad (F2, K1v2Kr no están
      en {K_n, K_n-e}).

  Novedad (a fecha del mejor catálogo público): el survey de 2024 lista la
  conjetura como "Conjecture 1" ABIERTA, sin contraejemplo; Lin-Das-Wu (2016)
  probaron sólo las hermanas rho+d3, rho+d_{floor(7D/8)}. No se halló refutación
  previa. (Una búsqueda de literatura nunca es exhaustiva: se declara como
  evidencia fuerte, no certeza absoluta.)

Uso:  python retos/verificacion_fuente_primaria.py
"""
import networkx as nx
import numpy as np
import sympy as sp

x = sp.Symbol("x")


def rho_d2_exacto(G):
    """(rho, d2, rho+d2) exactos: rho racional; d2 = 2do mayor autovalor de la
    matriz de distancias vía charpoly ENTERO + real_roots (números algebraicos)."""
    n = G.number_of_nodes()
    D = nx.floyd_warshall_numpy(G).astype(int)
    trans = [int(D[i].sum()) for i in range(n)]
    rho = sp.Rational(max(trans), n - 1)
    roots = sp.real_roots(sp.Matrix(D.tolist()).charpoly(x))  # ascendente, con mult.
    d2 = roots[-2]
    return rho, d2, sp.nsimplify(rho + d2)


def B(n):
    return sp.nsimplify(sp.Rational(n, n - 1) + (sp.Integer(n - 1) - sp.sqrt((n - 1) ** 2 + 8)) / 2)


# ---- grafos clave ----
def K(n):
    return nx.complete_graph(n)


def K_menos_e(n):                       # K_n - e (una arista)
    G = nx.complete_graph(n); G.remove_edge(n - 2, n - 1); return G


def K_menos_2e(n):                      # K_n - 2e  (dos aristas de un emparejamiento)
    G = nx.complete_graph(n); G.remove_edge(0, 1); G.remove_edge(2, 3); return G


def F2():                               # grafo de la amistad = K1 v 2K2  (n=5)
    G = nx.Graph(); G.add_edges_from([(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (3, 4)]); return G


def join_2Kr(r):                        # K1 v 2Kr  (n = 2r+1)
    G = nx.Graph()
    a = range(1, 1 + r); b = range(1 + r, 1 + 2 * r)
    for c in (list(a), list(b)):
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                G.add_edge(c[i], c[j])
    for v in list(a) + list(b):
        G.add_edge(0, v)
    return G


def linea(nombre, G, excl=False):
    n = G.number_of_nodes()
    rho, d2, val = rho_d2_exacto(G)
    Bn = B(n)
    dif = sp.simplify(val - Bn)
    rel = ("= B(n)  (igualdad)" if dif == 0
           else ("< B(n)  *** VIOLA ***" if dif.is_negative
                 else "> B(n)  (cumple)"))
    marca = "  [excluido por hipótesis]" if excl else ""
    print(f"  {nombre:20} n={n:>2}  rho+d2 = {str(val):26} ≈ {float(val):.7f}   {rel}{marca}")
    return val, Bn, dif


def main():
    print("VERIFICACIÓN DE FUENTE PRIMARIA — Jia-Song Conjecture 3.8 (survey: Conjecture 1)")
    print("=" * 84)

    # 1) B(n) == RHS verbatim del primario, y quién alcanza la igualdad
    print("\n[1] La cota y su grafo de igualdad (aritmética exacta):")
    n = 5
    print(f"    B({n}) = {B(n)}  ≈ {float(B(n)):.10f}")
    vKe, _, dKe   = linea("K_n - e", K_menos_e(n), excl=True)
    vK2e, _, dK2e = linea("K_n - 2e (matching)", K_menos_2e(n))
    print("    --> K_n - e alcanza B(n) EXACTO:", sp.simplify(vKe - B(n)) == 0,
          "|  K_n - 2e alcanza B(n):", sp.simplify(vK2e - B(n)) == 0)
    print("    --> El PRIMARIO afirma igualdad en K_n-2e, pero K_n-2e da",
          f"{vK2e} (= n/(n-1)) ≠ B(n): inconsistencia de transcripción")
    print("        (el survey 2024 la 'corrige' a K_n-e, que sí coincide con el cómputo).")

    # 2) Refutación de la DESIGUALDAD (robusta al caso de igualdad)
    print("\n[2] Contraejemplos a la DESIGUALDAD  rho+d2 >= B(n)  (G ∉ {K_n, K_n-e}):")
    v5, B5, d5   = linea("F2 = K1 v 2K2", F2())
    v11, B11, d11 = linea("K1 v 2K5", join_2Kr(5))

    # 3) Certificado entero del caso mínimo F2
    print("\n[3] Certificado ENTERO del caso mínimo (F2, n=5):")
    lhs = sp.Integer(4) - sp.sqrt(41) / 2         # rho+d2(F2)
    rhs = sp.Rational(13, 4) - sp.sqrt(6)          # B(5)
    gap = sp.simplify(rhs - lhs)                   # B(5) - (rho+d2)(F2)  > 0 ?
    print(f"    B(5) - rho+d2(F2) = {gap} ≈ {float(gap):.12f}   is_positive = {gap.is_positive}")
    print("    equivale a  59^2 = 3481 > 3456 = 24^2·6   (verdadero por enteros).")

    # veredicto reproducible
    ok = (sp.simplify(vKe - B(5)) == 0 and d5.is_negative and d11.is_negative
          and gap.is_positive and sp.simplify(vK2e - B(5)) != 0)
    print("\n" + "=" * 84)
    print("VEREDICTO:", "REFUTACIÓN CONFIRMADA (exacta, reproducible)" if ok else "FALLO")
    print("  · El cómputo es propio y exacto; no se copió de ninguna fuente.")
    print("  · De la literatura sólo se tomó el ENUNCIADO (Jia-Song 2018, Conj. 3.8/1).")
    print("  · Discrepancia primario↔survey en el caso de IGUALDAD documentada arriba;")
    print("    la refutación de la DESIGUALDAD es robusta a esa ambigüedad.")
    assert ok, "La verificación de fuente primaria FALLÓ"


if __name__ == "__main__":
    main()

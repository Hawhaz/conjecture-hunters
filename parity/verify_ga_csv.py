"""Verificación de extremo a extremo: cada `best_g6` que emite el GA de Rust se
re-evalúa con el ORÁCULO Python (evaluators.agx_l1_mu.gap_grafo) y se exige que
el gap coincida a 1e-9 con la columna best_gap de Rust, y que todo lo marcado
`contraejemplo` tenga de verdad gap>0 según Python. Uso: python verify_ga_csv.py <csv>
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx

from evaluators.agx_l1_mu import gap_grafo

path = sys.argv[1]
maxd = 0.0
filas = 0
contra = 0
falsos = 0
peor = None
with open(path, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        g6 = row["best_g6"]
        rust_gap = float(row["best_gap"])
        G = nx.from_graph6_bytes(g6.encode("ascii"))
        py_gap = gap_grafo(G)
        d = abs(py_gap - rust_gap)
        if d > maxd:
            maxd = d
            peor = (g6, rust_gap, py_gap)
        filas += 1
        if row["evento"] == "contraejemplo":
            contra += 1
            if not py_gap > 1e-9:
                falsos += 1

print(f"filas={filas} max_abs_diff_gap_Py_Rust={maxd:.3e} contraejemplos={contra} falsos={falsos}")
if peor:
    print(f"peor caso: gap_rust={peor[1]:.12f} gap_py={peor[2]:.12f} g6={peor[0][:40]}...")
assert maxd < 1e-9, "gap de Rust NO coincide con el oráculo Python"
assert falsos == 0, "un 'contraejemplo' de Rust no lo es según Python"
print("OK: cada best_g6 de Rust reproduce el gap de Python a 1e-9; contraejemplos reales.")

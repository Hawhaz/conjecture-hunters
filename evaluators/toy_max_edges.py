"""Evaluador del TOY (§8): grafo conexo, n = 20, grado máximo ≤ 3, maximizar aristas.

Óptimo = 30 (existe 3-regular con 20 vértices). Fitness = m si es válido, −1e9 si no.
Valida el LOOP (OpenEvolve + LLM + sandbox), no la búsqueda.
"""
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from evaluators.agx_l1_mu import SCORE_RECHAZO, ejecutar_y_validar

N_TOY, GRADO_MAX, OPTIMO = 20, 3, 30


def evaluate(program_path, timeout_s=30):
    try:
        res = ejecutar_y_validar(program_path, timeout_s=timeout_s)
        if res.get("error"):
            return {"combined_score": SCORE_RECHAZO, "error": res["error"]}
        G = res["G"]
        if G.number_of_nodes() != N_TOY:
            return {"combined_score": SCORE_RECHAZO,
                    "error": f"toy exige n={N_TOY}; llegó n={G.number_of_nodes()}"}
        grado_max = max(d for _, d in G.degree())
        if grado_max > GRADO_MAX:
            return {"combined_score": SCORE_RECHAZO,
                    "error": f"grado máximo {grado_max} > {GRADO_MAX}"}
        m = G.number_of_edges()
        return {"combined_score": float(m), "m": float(m)}
    except Exception as e:
        return {"combined_score": SCORE_RECHAZO,
                "error": f"error_interno_toy: {type(e).__name__}: {e}"}

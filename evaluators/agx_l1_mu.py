"""Evaluador de la conjetura de calibración CAL-1 (§2).

    λ₁(G) + μ(G) ≥ √(n−1) + 1      (AutoGraphiX / Aouchiche–Hansen; REFUTADA, Wagner 2021)

    gap(G)  = (√(n−1) + 1) − (λ₁ + μ)
    gap > 0 ⇔ contraejemplo        fitness = gap (se maximiza)

CONGELADO tras verde (§0): el código evolucionado JAMÁS modifica este archivo.

Sandbox (§7): AST check ANTES de ejecutar (allowlist de imports), subprocess con
timeout 30 s, RAM capada ~2 GB (setrlimit, solo POSIX), stdout truncado a 1 MB,
cwd temporal. Rechazo → {"combined_score": -1e9, "error": "<motivo>"} y el
orquestador sigue vivo: evaluate() jamás propaga excepciones.
"""
import ast
import math
import os
import subprocess
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx

from common.invariantes import A_de_grafo, lam1_fast, mu_fast, validar

SCORE_RECHAZO = -1e9
MAX_STDOUT = 1_048_576  # 1 MB
RAM_BYTES = 2 * 1024**3  # ~2 GB
MODULOS_PERMITIDOS = {"math", "random", "itertools", "heapq", "collections", "numpy"}
NOMBRES_PROHIBIDOS = {"open", "eval", "exec", "__import__", "compile", "input", "breakpoint"}


def cota(n):
    """Cota de la conjetura: √(n−1) + 1."""
    return math.sqrt(n - 1) + 1.0


def gap_grafo(G):
    """gap(G) sobre un networkx.Graph ya validado (conexo, simple)."""
    n = G.number_of_nodes()
    return cota(n) - (lam1_fast(A_de_grafo(G)) + mu_fast(G))


# ------------------------------------------------------------------ sandbox (§7)

def _chequeo_ast(fuente):
    """None si el programa pasa; str con el motivo si se rechaza.

    Corre SIEMPRE antes de ejecutar. Allowlist de imports: math, random,
    itertools, heapq, collections, numpy. Nombres prohibidos: open, eval,
    exec, __import__ (y variantes peligrosas).
    """
    try:
        arbol = ast.parse(fuente)
    except SyntaxError as e:
        return f"ast_sintaxis_invalida: {e.msg} (línea {e.lineno})"
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                raiz = alias.name.split(".")[0]
                if raiz not in MODULOS_PERMITIDOS:
                    return f"ast_import_prohibido: {raiz}"
        elif isinstance(nodo, ast.ImportFrom):
            raiz = (nodo.module or "").split(".")[0]
            if nodo.level or raiz not in MODULOS_PERMITIDOS:
                return f"ast_import_prohibido: {raiz or 'import relativo'}"
        elif isinstance(nodo, ast.Name) and nodo.id in NOMBRES_PROHIBIDOS:
            return f"ast_nombre_prohibido: {nodo.id}"
        elif isinstance(nodo, ast.Attribute) and nodo.attr in NOMBRES_PROHIBIDOS:
            return f"ast_nombre_prohibido: .{nodo.attr}"
    return None


def _limites_recursos():
    """RAM ~2 GB vía setrlimit; solo POSIX (en Windows este cap no aplica)."""
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (RAM_BYTES, RAM_BYTES))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except Exception:
        pass


def ejecutar_y_validar(program_path, timeout_s=30):
    """Ejecuta el programa en sandbox y valida su stdout.

    → {"error": str} en rechazo, o {"A": ndarray, "G": Graph, "n": int} si es válido.
    """
    try:
        with open(program_path, encoding="utf-8", errors="replace") as f:
            fuente = f.read()
    except OSError as e:
        return {"error": f"io_lectura: {e}"}

    motivo = _chequeo_ast(fuente)
    if motivo:
        return {"error": motivo}

    kwargs = {}
    if os.name == "posix":
        kwargs["preexec_fn"] = _limites_recursos
        kwargs["start_new_session"] = True
    with tempfile.TemporaryDirectory(prefix="sandbox_agx_") as tmp:
        try:
            proc = subprocess.run(
                [sys.executable, os.path.abspath(program_path)],
                capture_output=True,
                timeout=timeout_s,
                cwd=tmp,
                **kwargs,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"timeout: el programa superó {timeout_s} s"}
        except Exception as e:
            return {"error": f"subprocess: {type(e).__name__}: {e}"}

    if proc.returncode != 0:
        detalle = proc.stderr.decode("utf-8", errors="replace")[:500]
        return {"error": f"exit_code={proc.returncode}: {detalle}"}

    stdout = proc.stdout[:MAX_STDOUT].decode("utf-8", errors="replace")
    res = validar(stdout)
    if not res["ok"]:
        return {"error": res["error"]}
    return {"A": res["A"], "G": res["G"], "n": res["n"]}


def evaluate(program_path, timeout_s=30):
    """Contrato §7: SIEMPRE devuelve dict; rechazo → combined_score -1e9 + error."""
    try:
        res = ejecutar_y_validar(program_path, timeout_s=timeout_s)
        if res.get("error"):
            return {"combined_score": SCORE_RECHAZO, "error": res["error"]}
        G, A, n = res["G"], res["A"], res["n"]
        lam1 = lam1_fast(A)
        mu = mu_fast(G)
        gap = cota(n) - (lam1 + mu)
        g6 = nx.to_graph6_bytes(G, header=False).decode("ascii").strip()
        return {"combined_score": gap, "gap": gap, "n": n, "lam1": lam1, "mu": mu, "g6": g6}
    except Exception as e:  # el orquestador sigue vivo pase lo que pase
        return {
            "combined_score": SCORE_RECHAZO,
            "error": f"error_interno_evaluate: {type(e).__name__}: {e}",
        }

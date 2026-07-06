"""Nivel 2 — sandbox y programas adversariales (§7).

Contrato de evaluate(program_path) -> dict:
  - AST check ANTES de ejecutar (allowlist: math, random, itertools, heapq,
    collections, numpy; prohibidos os/sys/subprocess/socket/shutil/pathlib,
    open/eval/exec/__import__).
  - timeout 30 s por defecto, stdout truncado a 1 MB, cwd temporal.
  - Rechazo -> {"combined_score": -1e9, "error": "<motivo>"} y el orquestador
    SIGUE VIVO: evaluate jamás propaga una excepción.
"""
import inspect
from pathlib import Path

import pytest

from evaluators.agx_l1_mu import evaluate

FIX = Path(__file__).resolve().parent / "fixtures"
ADV = FIX / "adversarial"

ADVERSARIALES = [
    "a_basura.py",
    "b_timeout.py",
    "c_desconexo.py",
    "d_import_os.py",
    "e_flood.py",
    "f_vacio.py",
    "g_lazo_multi.py",
    "h_ids_fuera.py",
]


def test_timeout_por_defecto_es_30s():
    assert inspect.signature(evaluate).parameters["timeout_s"].default == 30


@pytest.mark.parametrize("nombre", ADVERSARIALES)
def test_adversarial_rechazado_sin_excepcion(nombre):
    kw = {"timeout_s": 6} if nombre == "b_timeout.py" else {}
    r = evaluate(str(ADV / nombre), **kw)  # si lanza, el test truena: contrato roto
    assert r["combined_score"] == -1e9
    assert isinstance(r.get("error"), str) and r["error"].strip() != ""


def test_import_os_bloqueado_por_ast_antes_de_ejecutar():
    r = evaluate(str(ADV / "d_import_os.py"))
    assert r["combined_score"] == -1e9
    assert "import" in r["error"].lower() or "ast" in r["error"].lower()
    assert not Path("hack.txt").exists(), "el ataque llegó a ejecutarse: el AST check no corrió antes"


def test_timeout_reporta_timeout():
    r = evaluate(str(ADV / "b_timeout.py"), timeout_s=6)
    assert "timeout" in r["error"].lower()


def test_desconexo_reporta_desconexo():
    r = evaluate(str(ADV / "c_desconexo.py"))
    assert "desconex" in r["error"].lower()


def test_programa_valido_c5():
    """Control positivo: C5 -> gap = -1 exacto (§4). El sandbox deja pasar lo bueno."""
    r = evaluate(str(FIX / "programa_valido_c5.py"))
    assert r.get("error") in (None, "")
    assert r["combined_score"] == pytest.approx(-1.0, abs=1e-9)
    assert r["n"] == 5 and r["mu"] == 2


def test_programa_valido_numpy_estrella():
    """Control positivo con numpy (import permitido): K_{1,9} -> gap = 0 exacto."""
    r = evaluate(str(FIX / "programa_valido_numpy.py"))
    assert r.get("error") in (None, "")
    assert r["combined_score"] == pytest.approx(0.0, abs=1e-9)
    assert r["n"] == 10


INLINE_PROHIBIDOS = [
    ("import os\nprint('0 1')\nprint('1 2')\nprint('2 0')", "os"),
    ("import sys\nprint('0 1')", "sys"),
    ("import subprocess", "subprocess"),
    ("import socket", "socket"),
    ("import shutil", "shutil"),
    ("import pathlib", "pathlib"),
    ("from os import path", "os (from)"),
    ("x = open('f.txt', 'w')", "open"),
    ("eval('1+1')", "eval"),
    ("exec('x = 1')", "exec"),
    ("__import__('os')", "__import__"),
]


@pytest.mark.parametrize("codigo,quien", INLINE_PROHIBIDOS, ids=[q for _, q in INLINE_PROHIBIDOS])
def test_ast_bloquea_prohibidos(tmp_path, codigo, quien):
    p = tmp_path / "malo.py"
    p.write_text(codigo, encoding="utf-8")
    r = evaluate(str(p))
    assert r["combined_score"] == -1e9
    assert isinstance(r.get("error"), str) and r["error"]


def test_imports_permitidos_pasan(tmp_path):
    p = tmp_path / "bueno.py"
    p.write_text(
        "import math, random, itertools, heapq, collections\n"
        "import numpy\n"
        "n = 5\n"
        "for i in range(n):\n"
        "    print(i, (i + 1) % n)\n",
        encoding="utf-8",
    )
    r = evaluate(str(p))
    assert r.get("error") in (None, "")
    assert r["combined_score"] == pytest.approx(-1.0, abs=1e-9)


def test_sintaxis_invalida_rechazada(tmp_path):
    p = tmp_path / "roto.py"
    p.write_text("def f(:\n    pass", encoding="utf-8")
    r = evaluate(str(p))
    assert r["combined_score"] == -1e9 and r["error"]


def test_orquestador_sobrevive_toda_la_bateria():
    """Las 8 adversariales seguidas en el MISMO proceso: cero excepciones no controladas."""
    for nombre in ADVERSARIALES:
        kw = {"timeout_s": 6} if nombre == "b_timeout.py" else {}
        r = evaluate(str(ADV / nombre), **kw)
        assert r["combined_score"] == -1e9 and r["error"]

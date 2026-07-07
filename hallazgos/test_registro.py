# -*- coding: utf-8 -*-
"""Tests del registro durable de hallazgos. Garantiza que el dato NUNCA se pierde,
que el certificado actualiza el estado, que un fallo de certificado no tira el dato,
y que se generan informe + alerta. Redirige el almacén a un tmp por test."""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro as r  # noqa: E402


def _set(tmp):
    os.environ["CONJ_HALLAZGOS_DIR"] = str(tmp)


def test_durabilidad_y_carga(tmp_path):
    _set(tmp_path)
    rec = r.registrar_hallazgo("lin_p4", "D?{", 0.5, n=5, alertar=False)
    assert rec["estado"] == "candidato"
    todos = r.cargar_todos()
    assert any(x["id"] == rec["id"] and x["g6"] == "D?{" for x in todos)
    assert glob.glob(os.path.join(str(tmp_path), "shards", "*.jsonl"))  # en disco


def test_certificado_actualiza_estado(tmp_path):
    _set(tmp_path)
    rec = r.registrar_hallazgo("c", "D?{", 0.5, n=5, alertar=False,
                               certificar_fn=lambda g6: {"ok": True, "detalle": "exacto"})
    assert rec["estado"] == "certificado"
    latest = {x["id"]: x for x in r.cargar_todos()}[rec["id"]]
    assert latest["estado"] == "certificado"


def test_cert_error_no_pierde_dato(tmp_path):
    _set(tmp_path)

    def boom(g6):
        raise ValueError("cae el certificado")

    rec = r.registrar_hallazgo("c", "E?{", 0.5, n=6, alertar=False, certificar_fn=boom)
    assert rec["estado"] == "cert_error"
    assert any(x["id"] == rec["id"] for x in r.cargar_todos())  # dato guardado pese al error


def test_informe_y_alerta(tmp_path):
    _set(tmp_path)
    rec = r.registrar_hallazgo("bollobas", "F?A?o", 0.11, n=7, alertar=True)
    assert glob.glob(os.path.join(str(tmp_path), "HIT_*.md"))            # informe .md
    alertas = os.path.join(str(tmp_path), "ALERTAS.md")
    assert os.path.exists(alertas)
    with open(alertas, encoding="utf-8") as f:
        assert rec["id"] in f.read()                                    # fila en ALERTAS.md


def test_dedup_ultimo_gana(tmp_path):
    _set(tmp_path)
    r.registrar_hallazgo("c", "D?{", 0.5, n=5, alertar=False)
    r.registrar_hallazgo("c", "D?{", 0.7, n=5, alertar=False)           # mismo id
    got = {x["id"]: x for x in r.cargar_todos()}
    assert got[r._hit_id("c", "D?{")]["gap"] == 0.7                     # último gana

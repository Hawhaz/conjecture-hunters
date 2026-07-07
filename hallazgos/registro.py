#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REGISTRO DURABLE DE HALLAZGOS — a prueba de fallos, para decenas de miles de
instancias en paralelo. Diseño: "el dato NUNCA se pierde".

Cuando cualquier instancia (CPU o GPU) encuentra un candidato a contraejemplo:
  1) se ESCRIBE A DISCO PRIMERO (append + flush + os.fsync) en un shard propio del
     proceso -> aunque el proceso muera un microsegundo después, el hallazgo ya está.
  2) se CERTIFICA exacto (si se pasa certificar_fn) y se re-graba el estado.
  3) se genera un INFORME .md por hallazgo (con g6 + cómo reproducirlo).
  4) se DISPARA ALERTA: banner ruidoso + fila en ALERTAS.md + webhook opcional
     (env CONJ_ALERT_WEBHOOK).

Shards por proceso (`shards/ledger_<host>_<pid>.jsonl`) => sin contención de locks
con miles de instancias; `cargar_todos()`/`resumen()` los funden (último gana por id).
Ninguna excepción de certificado/alerta puede tirar el registro del dato.

Config: CONJ_HALLAZGOS_DIR (default <repo>/hallazgos) — redirigible para tests.

Uso:
  from hallazgos.registro import registrar_hallazgo
  registrar_hallazgo("lin_p4", g6, gap, n=..., certificar_fn=...)
  python hallazgos/registro.py --resumen      # ver todo lo registrado
  python hallazgos/registro.py --demo         # graba un hallazgo de prueba
"""
import argparse
import datetime
import hashlib
import json
import os
import socket
import urllib.request

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _base():
    return os.environ.get("CONJ_HALLAZGOS_DIR", os.path.join(_REPO, "hallazgos"))

def _shards_dir():
    return os.path.join(_base(), "shards")

def _alertas_md():
    return os.path.join(_base(), "ALERTAS.md")

def _ensure():
    os.makedirs(_shards_dir(), exist_ok=True)

def _shard_path():
    return os.path.join(_shards_dir(), f"ledger_{socket.gethostname()}_{os.getpid()}.jsonl")

def _hit_id(conjetura, g6):
    return hashlib.sha1(f"{conjetura}|{g6}".encode()).hexdigest()[:16]

def _slug(s):
    return "".join(c if c.isalnum() else "_" for c in str(s))[:30]


def _append_fsync(path, rec):
    """Append atómico y DURABLE: escribe una línea JSON y fuerza a disco."""
    line = json.dumps(rec, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def registrar_hallazgo(conjetura, g6, gap, n=None, meta=None,
                       certificar_fn=None, alertar=True):
    """Graba un candidato a contraejemplo de forma DURABLE antes de nada más.
    Devuelve el registro. NUNCA lanza por fallos de certificado/alerta/informe."""
    _ensure()
    rec = {
        "id": _hit_id(conjetura, g6),
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "conjetura": conjetura, "n": n, "g6": g6, "gap": float(gap),
        "estado": "candidato", "host": socket.gethostname(), "pid": os.getpid(),
        "meta": meta or {},
    }
    # (1) DURABILIDAD PRIMERO
    _append_fsync(_shard_path(), rec)
    # (2) certificado exacto (best-effort)
    if certificar_fn is not None:
        try:
            cert = certificar_fn(g6)
            rec["certificado"] = cert
            rec["estado"] = "certificado" if cert.get("ok") else "cert_no_confirma"
        except Exception as e:  # el fallo del cert NO pierde el dato
            rec["certificado"] = {"ok": None, "error": f"{type(e).__name__}: {e}"}
            rec["estado"] = "cert_error"
        _append_fsync(_shard_path(), rec)
    # (3) informe por hallazgo
    try:
        _escribir_informe(rec)
    except Exception:
        pass
    # (4) alerta
    if alertar:
        try:
            _alertar(rec)
        except Exception:
            pass
    return rec


def _escribir_informe(rec):
    p = os.path.join(_base(), f"HIT_{_slug(rec['conjetura'])}_{rec['id']}.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"# HALLAZGO — {rec['conjetura']}\n\n")
        f.write(f"- **id**: `{rec['id']}`\n- **timestamp**: {rec['ts']}\n")
        f.write(f"- **host/pid**: {rec['host']}/{rec['pid']}\n")
        f.write(f"- **n**: {rec['n']}\n- **g6**: `{rec['g6']}`\n")
        f.write(f"- **gap**: {rec['gap']:+.10f}\n- **estado**: {rec['estado']}\n")
        if rec.get("certificado") is not None:
            f.write(f"- **certificado**: `{json.dumps(rec['certificado'], ensure_ascii=False)}`\n")
        if rec.get("meta"):
            f.write(f"- **meta**: `{json.dumps(rec['meta'], ensure_ascii=False)}`\n")
        f.write("\n## Reproducir\n\n```python\n")
        f.write("import networkx as nx, numpy as np\n")
        f.write(f"G = nx.from_graph6_bytes({rec['g6']!r}.encode())\n")
        f.write("# recomputa el invariante de la conjetura sobre G y confirma gap>0\n")
        f.write("```\n")


def _alertar(rec):
    print("\n" + "=" * 72
          + f"\n*** HALLAZGO [{rec['estado']}] ***  {rec['conjetura']}  "
          f"n={rec['n']}  gap={rec['gap']:+.6f}"
          f"\n    g6={rec['g6']}   id={rec['id']}\n" + "=" * 72 + "\n", flush=True)
    _ensure()
    nuevo = not os.path.exists(_alertas_md())
    with open(_alertas_md(), "a", encoding="utf-8") as f:
        if nuevo:
            f.write("# ALERTAS de hallazgos (contraejemplos)\n\n"
                    "| ts | conjetura | n | gap | estado | g6 | id |\n"
                    "|----|-----------|---|-----|--------|----|----|\n")
        f.write(f"| {rec['ts']} | {rec['conjetura']} | {rec['n']} | "
                f"{rec['gap']:+.6f} | {rec['estado']} | `{rec['g6']}` | {rec['id']} |\n")
        f.flush()
        os.fsync(f.fileno())
    url = os.environ.get("CONJ_ALERT_WEBHOOK")
    if url:
        try:
            data = json.dumps(rec).encode()
            req = urllib.request.Request(url, data=data,
                                        headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # el webhook es best-effort; el dato ya está en disco


def cargar_todos():
    """Funde todos los shards; último registro gana por id."""
    latest = {}
    d = _shards_dir()
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            try:
                with open(os.path.join(d, name), encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            r = json.loads(line)
                            latest[r["id"]] = r
            except Exception:
                continue
    return list(latest.values())


def resumen():
    hits = cargar_todos()
    print(f"HALLAZGOS registrados: {len(hits)}")
    for r in sorted(hits, key=lambda r: r.get("gap", 0), reverse=True):
        print(f"  [{r['estado']:16}] {r['conjetura']:24} n={r['n']} "
              f"gap={r['gap']:+.6f}  g6={r['g6']}  id={r['id']}")
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        registrar_hallazgo("demo_conjetura", "D?{", +0.0123, n=5,
                           meta={"nota": "hallazgo de prueba"})
    resumen()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scorecard de CAPACIDAD del sistema caza-conjeturas: una sola metrica-set
re-ejecutable para saber si CADA cambio nos mejora o nos regresiona.

Mide, con tiempos: (1) PARIDAD del evaluador Rust vs oraculo (correccion),
(2) THROUGHPUT del evaluador (evals/seg), (3) descubrimiento CAL-1 y CAL-2 por el
orquestador (¿certifica? gap, n, tiempo), (4) reto SOTA CAL-3 n=203 (¿certificado
exacto?), (5) refutacion de la Conjetura 1 de Jia-Song (¿refuta exacto? min-n),
(6) mejora (cota corregida, ¿corre?). Emite JSON versionado + tabla; `--compare`
muestra deltas contra una corrida previa.

Uso:
  python benchmarks/scorecard.py                 # corre todo, guarda + imprime
  python benchmarks/scorecard.py --compare benchmarks/scorecard_latest.json
  python benchmarks/scorecard.py --rapido        # omite CAL-2 (mas lento)
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUSCADOR = os.path.join(REPO, "buscador_rs", "target", "release", "buscador_rs.exe")
HIST = os.path.join(REPO, "benchmarks", "history")
LATEST = os.path.join(REPO, "benchmarks", "scorecard_latest.json")


def run(cmd, cwd=REPO, timeout=600, stdin=None):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, input=stdin, encoding="utf-8", errors="replace")
        return (p.stdout or "") + "\n" + (p.stderr or ""), p.returncode, time.time() - t0
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 124, time.time() - t0
    except Exception as e:
        return f"ERROR {type(e).__name__}: {e}", 1, time.time() - t0


def py(script, *args, timeout=600):
    return run([sys.executable, os.path.join(REPO, script), *args], timeout=timeout)


def fnum(pat, txt, default=None):
    m = re.search(pat, txt)
    return float(m.group(1)) if m else default


# ------------------------------------------------------------- metricas
def m_paridad():
    if not os.path.isfile(BUSCADOR):
        return {"status": "skip", "nota": "sin binario Rust (compilar buscador_rs)"}
    out, rc, s = run([BUSCADOR, "paridad", "--corpus",
                      os.path.join(REPO, "parity", "parity_corpus.csv")])
    mm = re.search(r"g6_mismatch=(\d+) mu_mismatch=(\d+) int_mismatch=(\d+) flips=(\d+)", out)
    difs = [float(x) for x in re.findall(r"max_abs_diff\s+\S+\s*=\s*([\d.eE+-]+)", out)]
    ok = ("OK" in out) and mm and all(int(g) == 0 for g in mm.groups())
    return {"status": "ok" if ok else "fail",
            "max_abs_diff": max(difs) if difs else None,
            "flips": int(mm.group(4)) if mm else None,
            "seconds": round(s, 2)}


def m_throughput():
    if not os.path.isfile(BUSCADOR):
        return {"status": "skip", "nota": "sin binario Rust"}
    # lista de g6 desde el corpus de paridad (columna 0), primeras 3000 filas
    corpus = os.path.join(REPO, "parity", "parity_corpus.csv")
    g6s = []
    try:
        with open(corpus, encoding="utf-8") as f:
            next(f)
            for line in f:
                g6s.append(line.split(",", 1)[0])
                if len(g6s) >= 3000:
                    break
    except Exception as e:
        return {"status": "fail", "nota": str(e)}
    tmp = tempfile.NamedTemporaryFile("w", suffix=".g6", delete=False, encoding="ascii")
    tmp.write("\n".join(g6s) + "\n"); tmp.close()
    try:
        out, rc, s = run([BUSCADOR, "evaluar", "--eval", "cal1", "--corpus", tmp.name])
        eps = fnum(r"evals?/?_?per_?sec[=:]?\s*([\d.]+)", out)
        if eps is None and s > 0:
            eps = len(g6s) / s  # fallback: filas/tiempo total (incluye arranque)
        return {"status": "ok" if rc == 0 else "fail",
                "evals_per_sec": round(eps, 1) if eps else None,
                "n_grafos": len(g6s), "seconds": round(s, 2)}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def m_orquestador(conj):
    out, rc, s = py("orquestador/orquestar.py", "--conjeturas", conj, "--iters", "120",
                    "--llm", "mock", "--islas", "5", "--semilla", "7",
                    "--out", os.path.join(tempfile.gettempdir(), f"sc_{conj}.csv"),
                    timeout=300)
    cert = ("cert=True" in out) or ("OK-CERT" in out)
    gap = fnum(r"best_gap=([\-\d.]+)", out)
    n = fnum(r"n=(\d+)\s+celdas", out)
    return {"status": "ok" if rc == 0 else "fail",
            "certifica": bool(cert), "best_gap": gap, "n": int(n) if n else None,
            "seconds": round(s, 2)}


def m_cal3():
    out, rc, s = py("retos/cal3_n203.py", timeout=300)
    cert = "certificado=True" in out
    margen = fnum(r"margen=([\d.eE+-]+)", out)
    contra = fnum(r"CONTRAEJEMPLOS en la familia:\s*(\d+)", out)
    return {"status": "ok" if (rc == 0 and cert) else "fail",
            "certificado_n203": bool(cert), "margen": margen,
            "contraejemplos_familia": int(contra) if contra else None,
            "seconds": round(s, 2)}


def m_jia_song():
    out, rc, s = py("retos/refutacion_jia_song.py", timeout=300)
    refuta = "REFUTACION CONFIRMADA EXACTAMENTE" in out
    todos = "para todo r en [2,30]: True" in out
    return {"status": "ok" if (rc == 0 and refuta) else "fail",
            "refuta_exacto": bool(refuta), "familia_r_2_30": bool(todos),
            "min_n": 5 if refuta else None, "seconds": round(s, 2)}


def m_mejora():
    if not os.path.isfile(os.path.join(REPO, "retos", "mejora_jia_song.py")):
        return {"status": "skip", "nota": "mejora_jia_song.py no presente aun"}
    out, rc, s = py("retos/mejora_jia_song.py", timeout=300)
    return {"status": "ok" if rc == 0 else "fail",
            "corre": rc == 0, "seconds": round(s, 2)}


METRICAS = [
    ("paridad_1e9", m_paridad),
    ("throughput_evaluador", m_throughput),
    ("cal1_descubrimiento", lambda: m_orquestador("cal1")),
    ("cal2_descubrimiento", lambda: m_orquestador("cal2")),
    ("cal3_reto_n203", m_cal3),
    ("jia_song_refutacion", m_jia_song),
    ("conjetura_mejorada", m_mejora),
]


def git_hash():
    out, rc, _ = run(["git", "rev-parse", "--short", "HEAD"])
    return out.strip().splitlines()[0] if rc == 0 and out.strip() else "?"


def correr(rapido=False):
    res = {}
    for nombre, fn in METRICAS:
        if rapido and nombre == "cal2_descubrimiento":
            res[nombre] = {"status": "skip", "nota": "--rapido"}
            continue
        print(f"  [scorecard] {nombre} ...", flush=True)
        res[nombre] = fn()
    return {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "git": git_hash(),
        "metricas": res,
    }


def imprimir(sc, prev=None):
    print("\n=== SCORECARD DEL SISTEMA CAZA-CONJETURAS ===")
    print(f"timestamp={sc['timestamp']}  commit={sc['git']}\n")
    print(f"{'metrica':26} {'status':>6}  {'clave':<46} {'seg':>7} {'vs prev':>10}")
    for nombre, m in sc["metricas"].items():
        clave = ", ".join(f"{k}={v}" for k, v in m.items()
                          if k not in ("status", "seconds", "nota"))[:46]
        seg = m.get("seconds", "")
        delta = ""
        if prev and nombre in prev.get("metricas", {}):
            ps = prev["metricas"][nombre].get("seconds")
            if isinstance(ps, (int, float)) and isinstance(seg, (int, float)) and ps:
                d = seg - ps
                delta = f"{d:+.2f}s"
        print(f"{nombre:26} {m['status']:>6}  {clave:<46} {str(seg):>7} {delta:>10}")
    oks = sum(1 for m in sc["metricas"].values() if m["status"] == "ok")
    print(f"\n  {oks}/{len(sc['metricas'])} metricas OK")
    if prev:
        print("  (deltas de tiempo vs corrida previa; regresiones de STATUS abajo)")
        for nombre, m in sc["metricas"].items():
            pm = prev.get("metricas", {}).get(nombre, {})
            if pm.get("status") == "ok" and m["status"] != "ok":
                print(f"  !! REGRESION: {nombre} paso de ok -> {m['status']}")
            if pm.get("status") not in (None, "ok") and m["status"] == "ok":
                print(f"  ++ MEJORA: {nombre} paso de {pm.get('status')} -> ok")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", default=None, help="JSON de scorecard previo")
    ap.add_argument("--rapido", action="store_true")
    args = ap.parse_args()

    prev = None
    ref = args.compare or (LATEST if os.path.isfile(LATEST) else None)
    if ref and os.path.isfile(ref):
        try:
            prev = json.load(open(ref, encoding="utf-8"))
        except Exception:
            prev = None

    sc = correr(rapido=args.rapido)
    imprimir(sc, prev)

    os.makedirs(HIST, exist_ok=True)
    ts = sc["timestamp"].replace(":", "").replace("-", "")
    with open(os.path.join(HIST, f"scorecard_{ts}.json"), "w", encoding="utf-8") as f:
        json.dump(sc, f, indent=2, ensure_ascii=False)
    with open(LATEST, "w", encoding="utf-8") as f:
        json.dump(sc, f, indent=2, ensure_ascii=False)
    print(f"\n  guardado: benchmarks/scorecard_latest.json (+ history/scorecard_{ts}.json)")


if __name__ == "__main__":
    main()

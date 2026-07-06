"""Benchmark apples-to-apples: motor Rust (buscador_rs) vs. oráculo Python.

Genera una lista FIJA de ~2000 grafos g6 conexos (n ∈ [10,120], semilla fija),
la escribe a un archivo temporal (fuera del repo), mide cuántos gaps CAL-1 por
segundo calcula Python (`evaluators.agx_l1_mu.gap_grafo`) sobre TODA la lista,
luego invoca `buscador_rs/src/bin/bench.rs` en modo `--corpus` sobre el MISMO
archivo y parsea su evals_per_sec. Imprime la razón Rust/Python (SPEEDUP).

El archivo temporal se borra siempre al final (éxito o excepción) — no debe
quedar basura ni en el repo ni en /tmp.

Uso:
    python parity/bench_vs_python.py
"""
import os
import random
import re
import subprocess
import sys
import tempfile
import time

# Consola Windows en cp1252 no puede imprimir acentos/em-dash: forzamos UTF-8
# en stdout/stderr para que los prints con tildes no revienten con
# UnicodeEncodeError (no afecta la lógica, solo la salida de texto).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import networkx as nx  # noqa: E402

from evaluators.agx_l1_mu import gap_grafo  # noqa: E402

# ------------------------------------------------------------- config fija
SEMILLA = 20260706
N_OBJETIVO = 2000
N_MIN, N_MAX = 10, 120

# PATH extra para el linker self-contained (dlltool) del toolchain windows-gnu
# — solo hace falta si `cargo build` necesita (re)compilar; el binario YA
# compilado corre standalone sin este PATH (dlltool es solo build-time).
_DLLTOOL_BIN = (
    r"C:\Users\123\.rustup\toolchains\stable-x86_64-pc-windows-gnu"
    r"\lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained"
)


# ------------------------------------------------------ (1) generar corpus
def generar_g6_fijo(objetivo=N_OBJETIVO, n_min=N_MIN, n_max=N_MAX, semilla=SEMILLA):
    """~`objetivo` grafos g6 conexos, simples, con n repartido en [n_min,n_max].

    Determinista dada `semilla` (random.Random propio, no global) — mismo
    corpus en cada corrida, igual que parity/build_corpus.py::fuente_d.
    """
    rng = random.Random(semilla)
    ns = list(range(n_min, n_max + 1))
    vistos = set()
    lineas = []
    intentos = 0
    intentos_max = objetivo * 50
    while len(lineas) < objetivo and intentos < intentos_max:
        intentos += 1
        n = rng.choice(ns)
        # p por encima del umbral de conexidad ln(n)/n, con algo de dispersión.
        base = (2.0 + rng.random() * 6.0) / n
        p = min(0.95, max(base, rng.uniform(0.05, 0.6)))
        semilla_g = rng.randrange(1, 2**31 - 1)
        g = nx.gnp_random_graph(n, p, seed=semilla_g)
        if g.number_of_nodes() < 3 or not nx.is_connected(g):
            continue
        g6 = nx.to_graph6_bytes(g, header=False).decode("ascii").strip()
        if g6 in vistos:
            continue
        vistos.add(g6)
        lineas.append(g6)
    if len(lineas) < objetivo:
        print(
            f"[aviso] solo se generaron {len(lineas)}/{objetivo} grafos únicos "
            f"tras {intentos} intentos (se continúa igual)."
        )
    return lineas


# ------------------------------------------------------- (2) timing Python
def bench_python(g6_lineas):
    """Tiempo total (s) de computar gap_grafo sobre TODOS los g6, una pasada."""
    grafos = [nx.from_graph6_bytes(s.encode("ascii")) for s in g6_lineas]
    t0 = time.perf_counter()
    acc = 0.0
    for g in grafos:
        acc += gap_grafo(g)
    dt = time.perf_counter() - t0
    return dt, acc


# --------------------------------------------------------- (3) timing Rust
def _bench_bin_path():
    exe = "bench.exe" if os.name == "nt" else "bench"
    return os.path.join(_RAIZ, "buscador_rs", "target", "release", exe)


def _asegurar_binario_compilado():
    """Compila `bench` en --release si el binario no existe todavía.

    Antepone el PATH del linker self-contained (dlltool) SOLO para este
    subprocess de compilación — el binario ya compilado no lo necesita.
    """
    exe = _bench_bin_path()
    if os.path.exists(exe):
        return exe
    env = dict(os.environ)
    env["PATH"] = _DLLTOOL_BIN + os.pathsep + env.get("PATH", "")
    cwd = os.path.join(_RAIZ, "buscador_rs")
    print("[build] bench.exe no existe, compilando (cargo build --release --bin bench)...")
    subprocess.run(
        ["cargo", "build", "--release", "--bin", "bench"],
        cwd=cwd,
        env=env,
        check=True,
    )
    if not os.path.exists(exe):
        raise RuntimeError(f"cargo build no produjo {exe}")
    return exe


_RE_EVALS = re.compile(r"^evals_per_sec=([0-9.eE+-]+)\s*$", re.MULTILINE)
_RE_COUNT = re.compile(r"^count=(\d+)\s*$", re.MULTILINE)
_RE_SECONDS = re.compile(r"^total_seconds=([0-9.eE+-]+)\s*$", re.MULTILINE)


def bench_rust(corpus_path):
    """Invoca `bench --corpus <corpus_path>` y parsea evals_per_sec/count/seconds."""
    exe = _asegurar_binario_compilado()
    proc = subprocess.run(
        [exe, "--corpus", corpus_path],
        capture_output=True,
        text=True,
        check=True,
    )
    out = proc.stdout
    m_evals = _RE_EVALS.search(out)
    m_count = _RE_COUNT.search(out)
    m_secs = _RE_SECONDS.search(out)
    if not (m_evals and m_count and m_secs):
        raise RuntimeError(f"no pude parsear salida de {exe}:\n{out}\n{proc.stderr}")
    return {
        "evals_per_sec": float(m_evals.group(1)),
        "count": int(m_count.group(1)),
        "total_seconds": float(m_secs.group(1)),
        "raw_stdout": out,
        "raw_stderr": proc.stderr,
    }


# ------------------------------------------------------------------- main
def main():
    print(f"[corpus] generando ~{N_OBJETIVO} grafos g6 conexos, n en [{N_MIN},{N_MAX}], semilla={SEMILLA}...")
    g6_lineas = generar_g6_fijo()
    n_reales = len(g6_lineas)
    print(f"[corpus] {n_reales} grafos únicos generados")

    tmp_dir = tempfile.mkdtemp(prefix="bench_vs_python_")
    tmp_path = os.path.join(tmp_dir, "corpus_2000.g6")
    try:
        with open(tmp_path, "w", encoding="ascii") as f:
            f.write("\n".join(g6_lineas) + "\n")
        print(f"[corpus] escrito en scratch temporal: {tmp_path}")

        print("[python] evaluando CAL-1 (gap_grafo) sobre todos los grafos...")
        py_seconds, py_checksum = bench_python(g6_lineas)
        py_evals_per_sec = n_reales / py_seconds
        print(f"python_evals_per_sec={py_evals_per_sec:.6f}")
        print(f"[python] {n_reales} grafos en {py_seconds:.4f}s  (checksum={py_checksum:.6f})")

        print("[rust] invocando bench.exe --corpus sobre el MISMO archivo...")
        rust = bench_rust(tmp_path)
        print(f"rust_evals_per_sec={rust['evals_per_sec']:.6f}")
        print(
            f"[rust] {rust['count']} grafos en {rust['total_seconds']:.4f}s "
            f"(evals/sec={rust['evals_per_sec']:.2f})"
        )

        if rust["count"] != n_reales:
            print(
                f"[aviso] count Rust ({rust['count']}) != grafos generados ({n_reales}) "
                "— revisar líneas vacías/parseo del corpus."
            )

        speedup = rust["evals_per_sec"] / py_evals_per_sec
        print()
        print("=== RESULTADO ===")
        print(f"grafos evaluados        : {n_reales}  (n en [{N_MIN},{N_MAX}], semilla={SEMILLA})")
        print(f"python evals/sec (CAL-1): {py_evals_per_sec:,.2f}")
        print(f"rust   evals/sec (CAL-1): {rust['evals_per_sec']:,.2f}")
        print(f"SPEEDUP rust/python     : {speedup:,.2f}x")
        print(f"Rust is {speedup:,.1f}x faster than the Python evaluator on {n_reales} graphs.")
    finally:
        # Limpieza SIEMPRE: no debe quedar basura ni en el repo ni en /tmp.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError as e:
            print(f"[aviso] no pude limpiar {tmp_dir}: {e}")


if __name__ == "__main__":
    main()

//! Suite de benchmarks de `buscador_rs` (std only — sin criterion/rand, ver
//! CLAUDE.md §Directiva Rust: el toolchain windows-gnu rompe con crates que
//! arrastran windows-sys/getrandom vía dlltool).
//!
//! Auto-detectado como bin (`cargo run --release --bin bench`), no requiere
//! tocar Cargo.toml.
//!
//! Modos:
//!   bench                      → tabla EVAL THROUGHPUT (n∈{20,40,80,150,300},
//!                                 cal1/cal2/cal3) + GA THROUGHPUT (run_multilane)
//!   bench --corpus <file.g6>   → evalúa cal1 sobre TODOS los g6 del archivo una
//!                                 vez; imprime count/segundos/evals_per_sec.
//!                                 Este es el modo "apples-to-apples" que invoca
//!                                 `parity/bench_vs_python.py` para comparar contra
//!                                 el oráculo Python sobre el MISMO archivo.
//!
//! Generación de grafos aleatorios conexos: G(n,p) casero (rng.chance) +
//! reintento hasta conexo, usando SOLO `buscador_rs::rng::Rng` (xoshiro256++,
//! sin dependencia externa de aleatoriedad).

use std::env;
use std::fs;
use std::time::Instant;

use buscador_rs::evaluators::{cal1, cal2, cal3};
use buscador_rs::ga::{self, Config, Eval};
use buscador_rs::graph::Graph;
use buscador_rs::rng::Rng;

// --------------------------------------------------------------- utilidades

/// Genera un grafo G(n,p) conexo reintentando con p creciente si hace falta.
/// p inicial por encima del umbral de conexidad (~ln(n)/n) para minimizar
/// reintentos; si tras `max_tries` sigue inconexo, sube p y reintenta.
fn random_connected_gnp(n: usize, rng: &mut Rng) -> Graph {
    if n <= 1 {
        return Graph::empty(n.max(1));
    }
    let umbral = (n as f64).ln() / (n as f64);
    let mut p = (umbral * 2.5).clamp(0.05, 0.9);
    loop {
        let mut g = Graph::empty(n);
        for u in 0..n {
            for v in (u + 1)..n {
                if rng.chance(p) {
                    g.add_edge(u, v);
                }
            }
        }
        if g.is_connected() {
            return g;
        }
        p = (p * 1.3).min(0.98);
    }
}

/// Mediana de un vector de f64 (ordena una copia; asume no vacío).
fn mediana(vals: &mut [f64]) -> f64 {
    vals.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let m = vals.len() / 2;
    if vals.len().is_multiple_of(2) {
        (vals[m - 1] + vals[m]) / 2.0
    } else {
        vals[m]
    }
}

// --------------------------------------------------------- modo --corpus

/// Lee un archivo newline-delimited de g6, decodifica cada línea, evalúa CAL-1
/// sobre TODOS una vez, e imprime count/segundos/evals_per_sec. Formato de
/// salida parseable línea por línea por `parity/bench_vs_python.py`.
fn modo_corpus(path: &str) {
    let raw = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("[bench] no pude leer corpus {path}: {e}");
        std::process::exit(1);
    });
    let g6s: Vec<&str> = raw.lines().map(|l| l.trim()).filter(|l| !l.is_empty()).collect();
    let n_total = g6s.len();
    if n_total == 0 {
        eprintln!("[bench] corpus vacío: {path}");
        std::process::exit(1);
    }

    // Decodificación fuera del cronómetro (solo medimos el costo de evaluar).
    let grafos: Vec<Graph> = g6s
        .iter()
        .map(|s| {
            Graph::from_graph6(s).unwrap_or_else(|e| {
                eprintln!("[bench] g6 inválido {s:?}: {e}");
                std::process::exit(1);
            })
        })
        .collect();

    let t0 = Instant::now();
    let mut acc = 0.0f64; // evita que el optimizador elimine el trabajo
    for g in &grafos {
        acc += cal1(g).gap;
    }
    let elapsed = t0.elapsed().as_secs_f64();
    let evals_per_sec = n_total as f64 / elapsed;

    // Salida parseable (clave=valor) + línea humana.
    println!("corpus={path}");
    println!("count={n_total}");
    println!("total_seconds={elapsed:.9}");
    println!("evals_per_sec={evals_per_sec:.6}");
    println!("checksum={acc:.6}"); // solo para descartar dead-code-elim, no semántico
    eprintln!(
        "[bench] --corpus: {n_total} grafos, cal1 total={elapsed:.4}s, evals/sec={evals_per_sec:.2}"
    );
}

// ---------------------------------------------------- modo tabla EVAL

const NS_EVAL: [usize; 5] = [20, 40, 80, 150, 300];
const GRAFOS_POR_N: usize = 200;
const REPETICIONES: usize = 3;

fn modo_eval_throughput() {
    println!("=== EVAL THROUGHPUT (evals/sec por conjetura y n) ===");
    println!(
        "{:>5} {:>10} {:>14} {:>14} {:>14}",
        "n", "grafos", "cal1_ev/s", "cal2_ev/s", "cal3_ev/s"
    );

    for &n in NS_EVAL.iter() {
        // Corpus de grafos aleatorios conexos, generado UNA vez por n (fuera
        // del cronómetro): mismo conjunto de grafos para las 3 conjeturas.
        let mut rng = Rng::seed(0xC0FFEE_u64 ^ (n as u64));
        let grafos: Vec<Graph> = (0..GRAFOS_POR_N).map(|_| random_connected_gnp(n, &mut rng)).collect();

        let mut cal1_rates = Vec::with_capacity(REPETICIONES);
        let mut cal2_rates = Vec::with_capacity(REPETICIONES);
        let mut cal3_rates = Vec::with_capacity(REPETICIONES);

        for _ in 0..REPETICIONES {
            let mut acc = 0.0f64;
            let t0 = Instant::now();
            for g in &grafos {
                acc += cal1(g).gap;
            }
            let dt = t0.elapsed().as_secs_f64();
            cal1_rates.push(grafos.len() as f64 / dt);
            std::hint::black_box(acc);

            let mut acc = 0.0f64;
            let t0 = Instant::now();
            for g in &grafos {
                acc += cal2(g).gap;
            }
            let dt = t0.elapsed().as_secs_f64();
            cal2_rates.push(grafos.len() as f64 / dt);
            std::hint::black_box(acc);

            let mut acc = 0.0f64;
            let t0 = Instant::now();
            for g in &grafos {
                acc += cal3(g).gap;
            }
            let dt = t0.elapsed().as_secs_f64();
            cal3_rates.push(grafos.len() as f64 / dt);
            std::hint::black_box(acc);
        }

        let c1 = mediana(&mut cal1_rates);
        let c2 = mediana(&mut cal2_rates);
        let c3 = mediana(&mut cal3_rates);
        println!(
            "{:>5} {:>10} {:>14.1} {:>14.1} {:>14.1}",
            n,
            grafos.len(),
            c1,
            c2,
            c3
        );
    }
    println!();
}

// ------------------------------------------------------- modo GA

fn modo_ga_throughput() {
    println!("=== GA THROUGHPUT (run_multilane) ===");
    let cfg = Config {
        runs: 8,
        gens: 200,
        pop: 100,
        elite: 5,
        semilla_base: 20260706,
        amcs_depth: 1,
        amcs_level: 0,
        sin_seeds: true,
        eval: Eval::Cal1,
    };
    let hilos = rayon::current_num_threads();
    eprintln!(
        "[bench] GA config: runs={} gens={} pop={} elite={} amcs_depth={} amcs_level={} sin_seeds={} hilos={}",
        cfg.runs, cfg.gens, cfg.pop, cfg.elite, cfg.amcs_depth, cfg.amcs_level, cfg.sin_seeds, hilos
    );

    let t0 = Instant::now();
    let lanes = ga::run_multilane(&cfg);
    let elapsed = t0.elapsed().as_secs_f64();

    // generaciones*población EVALUADAS realmente ejecutadas: cada carril
    // recorre 1 fitness-eval de la población inicial (cfg.pop) + 1 fitness-eval
    // de la nueva población por cada generación efectivamente corrida (puede
    // terminar antes si encuentra contraejemplo). Sumamos filas reales (rows)
    // +1 (población inicial) por carril, cada una representando pop evals.
    let generaciones_reales: usize = lanes.iter().map(|l| l.rows.len()).sum();
    let evals_totales = (generaciones_reales + lanes.len()) as f64 * cfg.pop as f64;
    let evals_per_sec = evals_totales / elapsed;
    let exitos = lanes.iter().filter(|l| l.exito).count();

    println!(
        "{:>10} {:>10} {:>10} {:>14} {:>16} {:>18}",
        "lanes", "hilos", "gens_max", "wall_s", "gens_reales", "gens*pop/sec"
    );
    println!(
        "{:>10} {:>10} {:>10} {:>14.4} {:>16} {:>18.1}",
        cfg.runs, hilos, cfg.gens, elapsed, generaciones_reales, evals_per_sec
    );
    println!(
        "[resumen] carriles_exitosos={exitos}/{} evals_totales={evals_totales:.0} wall={elapsed:.4}s",
        cfg.runs
    );
    println!();
}

// -------------------------------------------------------------- main

// ---------------------------------------------- modo PARALLEL BATCH

/// Serial vs rayon sobre un lote fijo: mide el multiplicador de núcleos para el
/// escenario de verificación masiva / loop LLM (barrer muchos candidatos).
fn modo_parallel_throughput() {
    println!("=== PARALLEL BATCH THROUGHPUT (serial vs rayon, cal1) ===");
    let mut rng = Rng::seed(0x0BA7C4);
    let batch: Vec<Graph> = (0..4000)
        .map(|_| {
            let n = 30 + rng.below(60); // n ∈ [30, 89]
            random_connected_gnp(n, &mut rng)
        })
        .collect();
    let hilos = rayon::current_num_threads();

    // serial
    let t0 = Instant::now();
    let mut acc = 0.0f64;
    for g in &batch {
        acc += cal1(g).gap;
    }
    let serial = batch.len() as f64 / t0.elapsed().as_secs_f64();
    std::hint::black_box(acc);

    // paralelo (rayon)
    let t0 = Instant::now();
    let res = buscador_rs::batch::eval_batch(&batch, Eval::Cal1);
    let par = batch.len() as f64 / t0.elapsed().as_secs_f64();
    std::hint::black_box(res.iter().sum::<f64>());

    println!(
        "{:>8} {:>6} {:>16} {:>16} {:>10}",
        "batch", "hilos", "serial_ev/s", "paralelo_ev/s", "speedup"
    );
    println!(
        "{:>8} {:>6} {:>16.1} {:>16.1} {:>9.2}x",
        batch.len(),
        hilos,
        serial,
        par,
        par / serial
    );
    println!();
}

fn print_help() {
    println!(
        "bench — suite de benchmarks de buscador_rs (std only)\n\n\
         Uso:\n\
         \x20 cargo run --release --bin bench\n\
         \x20     tabla EVAL THROUGHPUT (n=20,40,80,150,300; cal1/cal2/cal3)\n\
         \x20     + GA THROUGHPUT (run_multilane, runs=8 gens=200 pop=100)\n\n\
         \x20 cargo run --release --bin bench -- --corpus <archivo.g6>\n\
         \x20     evalúa cal1 sobre TODOS los g6 (uno por línea) del archivo,\n\
         \x20     UNA sola pasada; imprime count/total_seconds/evals_per_sec.\n\
         \x20     Formato usado por parity/bench_vs_python.py para el apples-\n\
         \x20     to-apples Rust-vs-Python sobre el MISMO archivo.\n"
    );
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("-h") || args.first().map(String::as_str) == Some("--help") {
        print_help();
        return;
    }
    if args.first().map(String::as_str) == Some("--corpus") {
        let path = args.get(1).unwrap_or_else(|| {
            eprintln!("[bench] --corpus requiere una ruta");
            std::process::exit(2);
        });
        modo_corpus(path);
        return;
    }

    eprintln!("[bench] hilos rayon disponibles = {}", rayon::current_num_threads());
    modo_eval_throughput();
    modo_ga_throughput();
    modo_parallel_throughput();

    // Nota de escalado / cuello de botella: CAL-1 y CAL-2 hacen UNA
    // descomposición espectral densa O(n^3) (faer::self_adjoint_eigenvalues)
    // sobre la matriz de adyacencia; CAL-1 suma además el matching máximo
    // (blossom O(V^3) en el peor caso, rápido en la práctica para grafos
    // dispersos). CAL-3 hace BFS todos-pares O(n^2) MÁS una segunda
    // descomposición espectral O(n^3) sobre la matriz de DISTANCIAS (densa,
    // n^2 entradas) — por eso normalmente escala peor que cal1/cal2 al crecer
    // n: la caída de evals/sec de cal3 relativa a cal1/cal2 en la tabla de
    // arriba es la firma de "el cuello de botella es el eigendecomp, no el
    // matching ni el BFS".
    println!("[nota] ver comentario en main() de bench.rs sobre el cuello de botella (eigendecomp O(n^3)).");
}

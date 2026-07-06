//! CLI de buscador_rs: GA multi-carril paralelo (rayon) que emite el MISMO CSV
//! que `calibracion/ga_graphs.py` (corrida,gen,best_gap,best_g6,n,evento,epoch).
//!
//! Uso:
//!   buscador_rs [--runs 20] [--gens 1000] [--pop 200] [--elite 10]
//!               [--semilla-base 20260705] [--amcs-depth 3] [--amcs-level 2]
//!               [--sin-seeds] [--eval cal1|cal2|cal3] [--out RUTA.csv]

use std::fs;
use std::io::Write;
use std::path::Path;
use std::time::Instant;

use buscador_rs::ga::{self, Config, Eval};

fn main() {
    let mut cfg = Config::default();
    let mut out = String::from("ga_log_rs.csv");

    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut i = 0;
    while i < args.len() {
        let a = args[i].as_str();
        let next = |i: &mut usize| -> String {
            *i += 1;
            args.get(*i).cloned().unwrap_or_else(|| {
                eprintln!("falta valor para {a}");
                std::process::exit(2);
            })
        };
        match a {
            "--runs" => cfg.runs = next(&mut i).parse().expect("runs"),
            "--gens" => cfg.gens = next(&mut i).parse().expect("gens"),
            "--pop" => cfg.pop = next(&mut i).parse().expect("pop"),
            "--elite" => cfg.elite = next(&mut i).parse().expect("elite"),
            "--semilla-base" => cfg.semilla_base = next(&mut i).parse().expect("semilla-base"),
            "--amcs-depth" => cfg.amcs_depth = next(&mut i).parse().expect("amcs-depth"),
            "--amcs-level" => cfg.amcs_level = next(&mut i).parse().expect("amcs-level"),
            "--sin-seeds" => cfg.sin_seeds = true,
            "--eval" => {
                let v = next(&mut i);
                cfg.eval = Eval::parse(&v).unwrap_or_else(|| {
                    eprintln!("--eval inválido: {v} (usa cal1|cal2|cal3)");
                    std::process::exit(2);
                });
            }
            "--out" => out = next(&mut i),
            "-h" | "--help" => {
                print_help();
                return;
            }
            other => {
                eprintln!("argumento desconocido: {other}");
                std::process::exit(2);
            }
        }
        i += 1;
    }

    // Guardas de configuración (evitan corridas degeneradas/silenciosas).
    if cfg.pop < 3 {
        eprintln!("--pop debe ser >= 3 (el torneo toma k=3 distintos)");
        std::process::exit(2);
    }
    if cfg.elite >= cfg.pop {
        eprintln!("--elite ({}) debe ser < --pop ({})", cfg.elite, cfg.pop);
        std::process::exit(2);
    }
    if cfg.runs == 0 || cfg.gens == 0 {
        eprintln!("--runs y --gens deben ser >= 1");
        std::process::exit(2);
    }

    let hilos = rayon::current_num_threads();
    eprintln!(
        "[buscador_rs] eval={} runs={} gens={} pop={} elite={} seeds={} hilos={}",
        cfg.eval.nombre(),
        cfg.runs,
        cfg.gens,
        cfg.pop,
        cfg.elite,
        if cfg.sin_seeds { "no(árboles)" } else { "sí(familias §9)" },
        hilos,
    );

    let t0 = Instant::now();
    let lanes = ga::run_multilane(&cfg);
    let elapsed = t0.elapsed().as_secs_f64();

    // Escribir CSV (mismo esquema que ga_graphs.py).
    if let Some(parent) = Path::new(&out).parent() {
        if !parent.as_os_str().is_empty() {
            let _ = fs::create_dir_all(parent);
        }
    }
    let mut f = fs::File::create(&out).unwrap_or_else(|e| {
        eprintln!("no pude crear {out}: {e}");
        std::process::exit(1);
    });
    writeln!(f, "corrida,gen,best_gap,best_g6,n,evento,epoch").unwrap();
    let mut total_rows = 0usize;
    for lane in &lanes {
        for r in &lane.rows {
            writeln!(
                f,
                "{},{},{:.10},{},{},{},{}",
                r.corrida, r.generacion, r.best_gap, r.best_g6, r.n, r.evento, r.epoch
            )
            .unwrap();
            total_rows += 1;
        }
    }

    // Resumen.
    let exitos = lanes.iter().filter(|l| l.exito).count();
    let mejor_gap = lanes.iter().map(|l| l.best_gap).fold(f64::NEG_INFINITY, f64::max);
    let primer_gen = lanes.iter().filter_map(|l| l.gen_hit).min();
    let min_n_ce = lanes
        .iter()
        .filter(|l| l.exito)
        .map(|l| l.best_n)
        .min();
    let mejor_g6 = lanes
        .iter()
        .max_by(|a, b| a.best_gap.partial_cmp(&b.best_gap).unwrap())
        .map(|l| l.best_g6.clone())
        .unwrap_or_default();

    eprintln!("[buscador_rs] --- resumen ---");
    eprintln!("  carriles con contraejemplo : {exitos}/{}", cfg.runs);
    eprintln!("  mejor gap global           : {mejor_gap:.10}");
    if let Some(g) = primer_gen {
        eprintln!("  primera gen con gap>0      : {g}");
    }
    if let Some(nn) = min_n_ce {
        eprintln!("  n mínimo entre contraej.   : {nn}");
    }
    eprintln!("  mejor g6                   : {mejor_g6}");
    eprintln!("  filas CSV                  : {total_rows}");
    eprintln!("  tiempo                     : {elapsed:.2}s");
    eprintln!("  salida                     : {out}");
}

fn print_help() {
    println!(
        "buscador_rs — GA multi-carril caza-contraejemplos (Rust)\n\n\
         --runs N           carriles/corridas paralelas (def 20)\n\
         --gens N           generaciones máx por carril (def 1000)\n\
         --pop N            tamaño de población (def 200)\n\
         --elite N          elitismo (def 10)\n\
         --semilla-base N   semilla base; carril r usa base+r (def 20260705)\n\
         --amcs-depth N     profundidad AMCS baseline (def 3)\n\
         --amcs-level N     nivel AMCS baseline (def 2)\n\
         --sin-seeds        población inicial de árboles aleatorios (estrés)\n\
         --eval cal1|cal2|cal3   conjetura objetivo (def cal1)\n\
         --out RUTA.csv     archivo de salida (def ga_log_rs.csv)\n"
    );
}

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
    // Subcomando de QA: buscador_rs paridad --corpus X.csv
    {
        let raw: Vec<String> = std::env::args().skip(1).collect();
        if raw.first().map(String::as_str) == Some("paridad") {
            return subcomando_paridad(&raw[1..]);
        }
        if raw.first().map(String::as_str) == Some("evaluar") {
            return subcomando_evaluar(&raw[1..]);
        }
    }

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
    if let Some(parent) = Path::new(&out).parent()
        && !parent.as_os_str().is_empty()
    {
        let _ = fs::create_dir_all(parent);
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

fn subcomando_paridad(args: &[String]) {
    let mut corpus = String::from("../parity/parity_corpus.csv");
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--corpus" {
            i += 1;
            if let Some(v) = args.get(i) {
                corpus = v.clone();
            }
        }
        i += 1;
    }
    match buscador_rs::paritycheck::check_corpus(&corpus) {
        Ok(rep) => {
            eprintln!("[paridad] corpus={corpus} filas={}", rep.filas);
            for (k, v) in &rep.max {
                eprintln!("[paridad] max_abs_diff {k:8} = {v:.3e}");
            }
            eprintln!(
                "[paridad] g6_mismatch={} mu_mismatch={} int_mismatch={} flips={}",
                rep.g6_mismatch, rep.mu_mismatch, rep.int_mismatch, rep.flips
            );
            if let Some(m) = &rep.peor_mismatch {
                eprintln!("[paridad] mismatch: {m}");
            }
            if let Some(f) = &rep.peor_flip {
                eprintln!("[paridad] FLIP: {f}");
            }
            if rep.ok(1e-9) {
                eprintln!("[paridad] OK: todo < 1e-9, 0 mismatches, 0 flips");
            } else {
                eprintln!("[paridad] FALLA");
                std::process::exit(1);
            }
        }
        Err(e) => {
            eprintln!("[paridad] error: {e}");
            std::process::exit(1);
        }
    }
}

/// Subcomando para el orquestador: lee g6 (--corpus o stdin), evalúa en LOTE
/// PARALELO y emite `g6,n,gap,contraejemplo`. Es el interfaz rápido que el loop
/// Python invoca por subprocess (sin PyO3, sin riesgo dlltool).
fn subcomando_evaluar(args: &[String]) {
    use std::io::Read;
    let mut eval = Eval::Cal1;
    let mut corpus: Option<String> = None;
    let mut umbral = 1e-9f64;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--eval" => {
                i += 1;
                if let Some(v) = args.get(i) {
                    eval = Eval::parse(v).unwrap_or_else(|| {
                        eprintln!("--eval inválido: {v} (cal1|cal2|cal3)");
                        std::process::exit(2);
                    });
                }
            }
            "--corpus" => {
                i += 1;
                corpus = args.get(i).cloned();
            }
            "--umbral" => {
                i += 1;
                if let Some(v) = args.get(i) {
                    umbral = v.parse().unwrap_or(umbral);
                }
            }
            _ => {}
        }
        i += 1;
    }

    let raw = match &corpus {
        Some(p) => fs::read_to_string(p).unwrap_or_else(|e| {
            eprintln!("[evaluar] no pude leer {p}: {e}");
            std::process::exit(1);
        }),
        None => {
            let mut s = String::new();
            std::io::stdin().read_to_string(&mut s).ok();
            s
        }
    };

    let mut etiquetas: Vec<String> = Vec::new();
    let mut grafos: Vec<buscador_rs::graph::Graph> = Vec::new();
    for linea in raw.lines() {
        let s = linea.trim();
        if s.is_empty() {
            continue;
        }
        match buscador_rs::graph::Graph::from_graph6(s) {
            Ok(g) => {
                etiquetas.push(s.to_string());
                grafos.push(g);
            }
            Err(_) => eprintln!("[evaluar] g6 inválido ignorado: {s}"),
        }
    }

    let gaps = buscador_rs::batch::eval_batch(&grafos, eval);
    println!("g6,n,gap,contraejemplo");
    let mut n_contra = 0usize;
    for ((s, g), gap) in etiquetas.iter().zip(&grafos).zip(&gaps) {
        let contra = *gap > umbral;
        if contra {
            n_contra += 1;
        }
        println!("{s},{},{gap:.12},{contra}", g.n);
    }
    eprintln!(
        "[evaluar] eval={} grafos={} contraejemplos={} hilos={}",
        eval.nombre(),
        grafos.len(),
        n_contra,
        rayon::current_num_threads()
    );
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

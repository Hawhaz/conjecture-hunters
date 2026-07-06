//! PARIDAD contra el oráculo Python. Lee `parity/parity_corpus.csv` (miles de g6
//! con sus invariantes calculados por numpy/scipy/networkx) y exige que el motor
//! Rust reproduzca cada columna a 1e-9 (μ, diam, k EXACTOS; g6 round-trip exacto).

use buscador_rs::evaluators::{cal1, cal2, cal3};
use buscador_rs::graph::Graph;
use std::path::PathBuf;

fn corpus_path() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("..");
    p.push("parity");
    p.push("parity_corpus.csv");
    p
}

fn track(map: &mut std::collections::BTreeMap<&'static str, f64>, key: &'static str, a: f64, b: f64) {
    let d = (a - b).abs();
    let e = map.entry(key).or_insert(0.0);
    if d > *e {
        *e = d;
    }
}

#[test]
fn parity_corpus_1e9() {
    let path = corpus_path();
    let mut rdr = csv::Reader::from_path(&path)
        .unwrap_or_else(|e| panic!("no pude abrir {}: {e}", path.display()));

    const TOL: f64 = 1e-9;
    let mut maxd: std::collections::BTreeMap<&'static str, f64> = Default::default();
    let mut rows = 0usize;
    let mut g6_mismatch: Vec<String> = Vec::new();
    let mut mu_mismatch: Vec<String> = Vec::new();
    let mut int_mismatch: Vec<String> = Vec::new();

    for result in rdr.records() {
        let rec = result.expect("fila CSV");
        let g6 = rec[0].to_string();
        let n: usize = rec[1].parse().unwrap();
        let py_lam1: f64 = rec[2].parse().unwrap();
        let py_mu: usize = rec[3].parse().unwrap();
        let py_gap1: f64 = rec[4].parse().unwrap();
        let py_lam2: f64 = rec[5].parse().unwrap();
        let py_hc: f64 = rec[6].parse().unwrap();
        let py_gap2: f64 = rec[7].parse().unwrap();
        let py_pi: f64 = rec[8].parse().unwrap();
        let py_diam: usize = rec[9].parse().unwrap();
        let py_k: usize = rec[10].parse().unwrap();
        let py_delta_k: f64 = rec[11].parse().unwrap();
        let py_gap3: f64 = rec[12].parse().unwrap();

        let g = Graph::from_graph6(&g6).expect("decode g6");
        assert_eq!(g.n, n, "n mismatch g6={g6}");
        if g.to_graph6() != g6 {
            g6_mismatch.push(g6.clone());
        }

        let c1 = cal1(&g);
        let c2 = cal2(&g);
        let c3 = cal3(&g);

        if c1.mu != py_mu {
            mu_mismatch.push(format!("g6={g6} rust={} py={py_mu}", c1.mu));
        }
        if c3.diam != py_diam || c3.k != py_k {
            int_mismatch.push(format!(
                "g6={g6} diam(r={},p={py_diam}) k(r={},p={py_k})",
                c3.diam, c3.k
            ));
        }

        track(&mut maxd, "lam1", c1.lam1, py_lam1);
        track(&mut maxd, "gap1", c1.gap, py_gap1);
        track(&mut maxd, "lam2", c2.lam2, py_lam2);
        track(&mut maxd, "hc", c2.hc, py_hc);
        track(&mut maxd, "gap2", c2.gap, py_gap2);
        track(&mut maxd, "pi", c3.pi, py_pi);
        track(&mut maxd, "delta_k", c3.delta_k, py_delta_k);
        track(&mut maxd, "gap3", c3.gap, py_gap3);
        rows += 1;
    }

    eprintln!("[paridad] filas={rows}");
    for (k, v) in &maxd {
        eprintln!("[paridad] max|Δ {k:8}| = {v:.3e}");
    }
    eprintln!(
        "[paridad] g6_mismatch={} mu_mismatch={} int_mismatch={}",
        g6_mismatch.len(),
        mu_mismatch.len(),
        int_mismatch.len()
    );
    for s in g6_mismatch.iter().take(5) {
        eprintln!("  g6≠ {s}");
    }
    for s in mu_mismatch.iter().take(5) {
        eprintln!("  μ≠ {s}");
    }
    for s in int_mismatch.iter().take(5) {
        eprintln!("  int≠ {s}");
    }

    assert!(rows > 3000, "corpus demasiado chico: {rows}");
    assert!(g6_mismatch.is_empty(), "graph6 no round-trip ({} casos)", g6_mismatch.len());
    assert!(mu_mismatch.is_empty(), "μ difiere de Python ({} casos)", mu_mismatch.len());
    assert!(int_mismatch.is_empty(), "diam/k enteros difieren ({} casos)", int_mismatch.len());
    for (key, v) in &maxd {
        assert!(*v <= TOL, "columna {key} excede 1e-9: {v:.3e}");
    }
}

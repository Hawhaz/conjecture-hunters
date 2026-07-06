//! Fixtures de contraejemplos PUBLICADOS (§6): confirman los evaluadores Rust
//! CAL-1/2/3 contra la realidad publicada, con los mismos valores que el oráculo
//! Python. A = Wagner/AMCS (λ₁+μ), B = S15+S19 (λ₂≤Hc), C = S191+P7+P5 (π+∂⌊2D/3⌋).

use buscador_rs::evaluators::{cal1, cal2, cal3};
use buscador_rs::graph::Graph;
use std::fs;
use std::path::PathBuf;

fn leer_g6(rel: &str) -> Graph {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("..");
    p.push("tests");
    p.push("fixtures");
    p.push(rel);
    let s = fs::read_to_string(&p).unwrap_or_else(|e| panic!("no pude leer {}: {e}", p.display()));
    Graph::from_graph6(s.trim()).expect("decode g6 fixture")
}

#[test]
fn fixture_a_cal1() {
    let g = leer_g6("fixture_l1mu.g6");
    let c = cal1(&g);
    assert_eq!(g.n, 18, "A: n");
    assert!(c.gap > 1e-9, "A no refuta CAL-1: gap={}", c.gap);
    assert!((c.gap - 0.021810091691572886).abs() < 1e-9, "A gap={}", c.gap);
}

#[test]
fn fixture_b_cal2() {
    let g = leer_g6("fixture_c4_estrellas.g6");
    let c = cal2(&g);
    assert_eq!(g.n, 35, "B: n");
    assert!(c.gap > 1e-9, "B no refuta CAL-2: gap={}", c.gap);
    assert!((c.gap - 0.0795010866096848).abs() < 1e-9, "B gap={}", c.gap);
}

#[test]
fn fixture_c_cal3() {
    let g = leer_g6("fixture_c2_203.g6");
    let c = cal3(&g);
    assert_eq!(g.n, 203, "C: n");
    assert_eq!(c.diam, 12, "C: diámetro");
    assert_eq!(c.k, 8, "C: k=⌊2D/3⌋");
    assert!(c.gap > 1e-9, "C no refuta CAL-3: gap={}", c.gap);
    assert!((c.gap - 0.00028496269907973826).abs() < 1e-9, "C gap={}", c.gap);
}

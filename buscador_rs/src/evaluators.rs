//! Evaluadores de las conjeturas de calibración. gap>0 ⇔ contraejemplo.
//!
//! CAL-1  λ₁ + μ ≥ √(n−1)+1        gap = (√(n−1)+1) − (λ₁ + μ)
//! CAL-2  λ₂ ≤ Hc                   gap = λ₂ − Hc,  Hc = Σ_{uv∈E} 2/(d_u+d_v)
//! CAL-3  π + ∂_⌊2D/3⌋ > 0 (n≥4)    gap = −(π + ∂_k),  k = ⌊2D/3⌋
//!
//! Cada `calN` devuelve TODOS los sub-invariantes para que `tests/parity.rs`
//! localice cualquier discrepancia con Python columna por columna.

use crate::graph::Graph;
use crate::invariants::{all_pairs_distances, diameter, maximum_matching, proximity};
use crate::spectral::{adjacency_eigenvalues_asc, distance_eigenvalues_asc};

#[derive(Clone, Copy, Debug)]
pub struct Cal1 {
    pub lam1: f64,
    pub mu: usize,
    pub gap: f64,
}

#[derive(Clone, Copy, Debug)]
pub struct Cal2 {
    pub lam2: f64,
    pub hc: f64,
    pub gap: f64,
}

#[derive(Clone, Copy, Debug)]
pub struct Cal3 {
    pub pi: f64,
    pub diam: usize,
    pub k: usize,
    pub delta_k: f64,
    pub gap: f64,
}

/// Cota de CAL-1: √(n−1) + 1.
#[inline]
pub fn cota(n: usize) -> f64 {
    ((n as f64) - 1.0).sqrt() + 1.0
}

pub fn cal1(g: &Graph) -> Cal1 {
    let ev = adjacency_eigenvalues_asc(g);
    let lam1 = ev[g.n - 1];
    let mu = maximum_matching(g);
    let gap = cota(g.n) - (lam1 + mu as f64);
    Cal1 { lam1, mu, gap }
}

pub fn cal2(g: &Graph) -> Cal2 {
    let ev = adjacency_eigenvalues_asc(g);
    let lam2 = ev[g.n - 2];
    let hc: f64 = g
        .edges()
        .iter()
        .map(|&(u, v)| 2.0 / ((g.degree(u) + g.degree(v)) as f64))
        .sum();
    let gap = lam2 - hc;
    Cal2 { lam2, hc, gap }
}

pub fn cal3(g: &Graph) -> Cal3 {
    let dist = all_pairs_distances(g);
    let diam = diameter(&dist);
    let k = (2 * diam) / 3;
    let ev = distance_eigenvalues_asc(&dist, g.n); // ascendente
    // Python: delta_desc = sort(desc); delta_k = delta_desc[k-1].
    // Semántica de índice negativo de Python: k==0 → delta_desc[-1] = el MENOR.
    let idx_desc = if k == 0 { g.n - 1 } else { k - 1 };
    let delta_k = ev[g.n - 1 - idx_desc];
    let pi = proximity(&dist, g.n);
    let gap = -(pi + delta_k);
    Cal3 { pi, diam, k, delta_k, gap }
}

/// gap CAL-1 sobre un grafo ya validado (conexo, simple). Fitness del GA.
#[inline]
pub fn gap_cal1(g: &Graph) -> f64 {
    cal1(g).gap
}

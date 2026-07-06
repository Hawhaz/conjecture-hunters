//! Invariantes espectrales vía faer (descomposición self-adjoint, densa, f64).
//!
//! Paridad con `numpy.linalg.eigvalsh`: ambos calculan el espectro de una matriz
//! simétrica real por tridiagonalización + QR/divide-and-conquer; para matrices
//! 0/1 (adyacencia) o de distancias enteras el acuerdo es ~1e-12, muy por debajo
//! del 1e-9 exigido. `self_adjoint_eigenvalues` devuelve los valores en orden
//! ASCENDENTE, igual que `eigvalsh`.

use crate::graph::Graph;
use faer::{Mat, Side};

/// Espectro de la matriz de ADYACENCIA en orden ascendente (largo n).
pub fn adjacency_eigenvalues_asc(g: &Graph) -> Vec<f64> {
    let n = g.n;
    let a = Mat::from_fn(n, n, |i, j| if g.has_edge(i, j) { 1.0f64 } else { 0.0 });
    let ev = a
        .as_ref()
        .self_adjoint_eigenvalues(Side::Lower)
        .expect("eig adyacencia");
    (0..n).map(|i| ev[i]).collect()
}

/// λ₁ = mayor eigenvalor de adyacencia (último del vector ascendente).
pub fn lam1(g: &Graph) -> f64 {
    let ev = adjacency_eigenvalues_asc(g);
    ev[g.n - 1]
}

/// λ₂ = segundo mayor eigenvalor de adyacencia.
pub fn lam2(g: &Graph) -> f64 {
    let ev = adjacency_eigenvalues_asc(g);
    ev[g.n - 2]
}

/// Espectro de la matriz de DISTANCIAS (dist[i][j] enteros) en orden ascendente.
pub fn distance_eigenvalues_asc(dist: &[Vec<usize>], n: usize) -> Vec<f64> {
    let a = Mat::from_fn(n, n, |i, j| dist[i][j] as f64);
    let ev = a
        .as_ref()
        .self_adjoint_eigenvalues(Side::Lower)
        .expect("eig distancias");
    (0..n).map(|i| ev[i]).collect()
}

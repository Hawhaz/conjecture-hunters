//! buscador_rs — motor de búsqueda caza-contraejemplos (port Rust del stack Python).
//!
//! Núcleo de PARIDAD (este archivo y sus módulos base): grafo simple + codec
//! graph6, invariantes espectrales (λ₁, λ₂, espectro de distancias vía faer),
//! matching máximo (blossom de Edmonds), distancias/π/diámetro por BFS, y los
//! evaluadores CAL-1/CAL-2/CAL-3. La paridad contra el oráculo Python (miles de
//! g6, tolerancia 1e-9) se valida en `tests/parity.rs`.
//!
//! Capa de BÚSQUEDA (operadores, seeds, AMCS, GA multi-carril con rayon) y la
//! CLI se apilan encima sin tocar el núcleo.
#![allow(dead_code)]

/// Franja de orden del GA (§9): n ∈ [10, 40].
pub const N_MIN: usize = 10;
pub const N_MAX: usize = 40;
/// Fitness de rechazo (grafo inválido/fuera de franja).
pub const MUY_MALO: f64 = -1e9;
/// Umbral de positividad (§4): las estrellas dan gap=0 EXACTO; sin umbral el
/// ruido de eigvalsh (~1e-15) daría falsos contraejemplos.
pub const TOL_POS: f64 = 1e-9;

pub mod rng;
pub mod graph;
pub mod spectral;
pub mod invariants;
pub mod evaluators;
pub mod paritycheck;
pub mod batch;
pub mod operators;
pub mod seeds;
pub mod amcs;
pub mod ga;

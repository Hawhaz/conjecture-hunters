//! Evaluación por LOTES en paralelo (rayon). Cada eval CAL-1/2/3 es independiente
//! y sin estado compartido → paralelismo trivial. Sirve al futuro loop LLM y a la
//! verificación masiva: multiplica el throughput por el número de núcleos SIN
//! tocar la exactitud (devuelve exactamente los mismos valores que la versión
//! serial; solo cambia la velocidad).

use crate::ga::{Eval, gap_of};
use crate::graph::Graph;
use rayon::prelude::*;

/// gap del evaluador `e` sobre un lote de grafos, en paralelo.
pub fn eval_batch(graphs: &[Graph], e: Eval) -> Vec<f64> {
    graphs.par_iter().map(|g| gap_of(g, e)).collect()
}

/// Índices de los grafos del lote que son contraejemplos (gap > umbral), en
/// paralelo. Útil para barrer millones de candidatos del loop LLM y quedarse
/// solo con los positivos antes de pasarlos al certificado exacto.
pub fn contraejemplos(graphs: &[Graph], e: Eval, umbral: f64) -> Vec<usize> {
    graphs
        .par_iter()
        .enumerate()
        .filter_map(|(i, g)| if gap_of(g, e) > umbral { Some(i) } else { None })
        .collect()
}

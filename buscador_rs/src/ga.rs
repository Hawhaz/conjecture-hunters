//! GA multi-carril paralelo (§9) con rayon. Cada carril (corrida) es
//! independiente con su propia semilla → paralelismo trivial y perfecto: 20+
//! carriles a la vez. Port de la dinámica de `calibracion/ga_graphs.py`.
//!
//! Fitness = gap del evaluador elegido (CAL-1 por defecto). n ∈ [10, 40]. La
//! paridad se valida a nivel EVALUADOR (tests/parity.rs), no de trayectoria RNG.

use crate::evaluators::{cal1, cal2, cal3};
use crate::graph::Graph;
use crate::rng::Rng;
use crate::{amcs, operators, seeds};
use crate::{MUY_MALO, N_MAX, N_MIN, TOL_POS};
use rayon::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Eval {
    Cal1,
    Cal2,
    Cal3,
}

impl Eval {
    pub fn nombre(&self) -> &'static str {
        match self {
            Eval::Cal1 => "cal1",
            Eval::Cal2 => "cal2",
            Eval::Cal3 => "cal3",
        }
    }
    pub fn parse(s: &str) -> Option<Eval> {
        match s.to_ascii_lowercase().as_str() {
            "cal1" | "1" => Some(Eval::Cal1),
            "cal2" | "2" => Some(Eval::Cal2),
            "cal3" | "3" => Some(Eval::Cal3),
            _ => None,
        }
    }
}

#[inline]
pub fn gap_of(g: &Graph, e: Eval) -> f64 {
    match e {
        Eval::Cal1 => cal1(g).gap,
        Eval::Cal2 => cal2(g).gap,
        Eval::Cal3 => cal3(g).gap,
    }
}

#[inline]
pub fn fitness(g: &Graph, e: Eval) -> f64 {
    if g.n < N_MIN || g.n > N_MAX || !g.is_connected() {
        MUY_MALO
    } else {
        gap_of(g, e)
    }
}

fn ahora() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0)
}

fn argmax(fits: &[f64]) -> usize {
    (0..fits.len())
        .max_by(|&a, &b| fits[a].partial_cmp(&fits[b]).unwrap())
        .unwrap()
}

fn torneo<'a>(pob: &'a [Graph], fits: &[f64], rng: &mut Rng) -> &'a Graph {
    let idxs = rng.sample_distinct(pob.len(), 3);
    let best = *idxs
        .iter()
        .max_by(|&&a, &&b| fits[a].partial_cmp(&fits[b]).unwrap())
        .unwrap();
    &pob[best]
}

#[derive(Clone)]
pub struct Row {
    pub corrida: usize,
    pub generacion: usize,
    pub best_gap: f64,
    pub best_g6: String,
    pub n: usize,
    pub evento: &'static str,
    pub epoch: u64,
}

pub struct LaneResult {
    pub rows: Vec<Row>,
    pub exito: bool,
    pub best_gap: f64,
    pub best_g6: String,
    pub best_n: usize,
    pub gen_hit: Option<usize>,
}

#[derive(Clone, Copy)]
pub struct Config {
    pub runs: usize,
    pub gens: usize,
    pub pop: usize,
    pub elite: usize,
    pub semilla_base: u64,
    pub amcs_depth: usize,
    pub amcs_level: usize,
    pub sin_seeds: bool,
    pub eval: Eval,
}

impl Default for Config {
    fn default() -> Self {
        Config {
            runs: 20,
            gens: 1000,
            pop: 200,
            elite: 10,
            semilla_base: 20260705,
            amcs_depth: 3,
            amcs_level: 2,
            sin_seeds: false,
            eval: Eval::Cal1,
        }
    }
}

pub fn corrida(id: usize, semilla: u64, cfg: &Config) -> LaneResult {
    let eval = cfg.eval;
    let mut rng = Rng::seed(semilla);

    let mut pob: Vec<Graph> = Vec::with_capacity(cfg.pop);
    if cfg.sin_seeds {
        for _ in 0..cfg.pop - 1 {
            let n = rng.range_incl(N_MIN, N_MAX);
            pob.push(operators::random_tree(n, &mut rng));
        }
    } else {
        for _ in 0..cfg.pop - 1 {
            pob.push(seeds::semilla_estructural(&mut rng));
        }
    }
    // organismo baseline AMCS obligatorio (§9)
    let inicial = operators::random_tree(5, &mut rng);
    let score = |g: &Graph| gap_of(g, eval);
    let base = amcs::amcs(
        &score,
        inicial,
        cfg.amcs_depth,
        cfg.amcs_level,
        true,
        &mut rng,
        N_MAX,
        TOL_POS,
    );
    pob.push(base);

    let mut fits: Vec<f64> = pob.iter().map(|g| fitness(g, eval)).collect();
    let mut rows: Vec<Row> = Vec::new();

    for generacion in 0..cfg.gens {
        let bi = argmax(&fits);
        let best_gap = fits[bi];
        let best_g6 = pob[bi].to_graph6();
        let best_n = pob[bi].n;
        let evento = if best_gap > TOL_POS { "contraejemplo" } else { "gen" };
        rows.push(Row {
            corrida: id,
            generacion,
            best_gap,
            best_g6: best_g6.clone(),
            n: best_n,
            evento,
            epoch: ahora(),
        });
        if best_gap > TOL_POS {
            return LaneResult {
                rows,
                exito: true,
                best_gap,
                best_g6,
                best_n,
                gen_hit: Some(generacion),
            };
        }

        let mut orden: Vec<usize> = (0..pob.len()).collect();
        orden.sort_by(|&a, &b| fits[b].partial_cmp(&fits[a]).unwrap());
        let mut nueva: Vec<Graph> = orden.iter().take(cfg.elite).map(|&i| pob[i].clone()).collect();
        while nueva.len() < cfg.pop {
            if rng.chance(0.3) {
                let a = torneo(&pob, &fits, &mut rng).clone();
                let b = torneo(&pob, &fits, &mut rng).clone();
                nueva.push(operators::cruza(&a, &b, &mut rng));
            } else {
                let p = torneo(&pob, &fits, &mut rng).clone();
                nueva.push(operators::mutar(&p, &mut rng));
            }
        }
        pob = nueva;
        fits = pob.iter().map(|g| fitness(g, eval)).collect();
    }

    let bi = argmax(&fits);
    LaneResult {
        rows,
        exito: false,
        best_gap: fits[bi],
        best_g6: pob[bi].to_graph6(),
        best_n: pob[bi].n,
        gen_hit: None,
    }
}

/// Corre todos los carriles EN PARALELO (rayon). Cada carril es independiente.
pub fn run_multilane(cfg: &Config) -> Vec<LaneResult> {
    (0..cfg.runs)
        .into_par_iter()
        .map(|r| corrida(r, cfg.semilla_base + r as u64, cfg))
        .collect()
}

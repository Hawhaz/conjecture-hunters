//! Chequeo de paridad reutilizable sobre un CSV corpus (mismo esquema que
//! `parity/parity_corpus.csv`: g6,n,lam1,mu,gap1,lam2,hc,gap2,pi,diam,k,delta_k,gap3).
//! Lo usan la CLI (`buscador_rs paridad --corpus X.csv`), `tests/parity.rs` y las
//! auditorías de estrés con corpus frescos. Además de Δ por columna, detecta
//! FLIPS: casos donde la clasificación contraejemplo (gap>TOL) difiere Py vs Rust
//! — lo único que de verdad puede meter "basura" en una caza.

use crate::TOL_POS;
use crate::evaluators::{cal1, cal2, cal3};
use crate::graph::Graph;
use std::collections::BTreeMap;

pub struct Report {
    pub filas: usize,
    pub max: BTreeMap<&'static str, f64>,
    pub g6_mismatch: usize,
    pub mu_mismatch: usize,
    pub int_mismatch: usize,
    pub flips: usize,
    pub peor_flip: Option<String>,
    pub peor_mismatch: Option<String>,
}

impl Report {
    pub fn ok(&self, tol: f64) -> bool {
        self.g6_mismatch == 0
            && self.mu_mismatch == 0
            && self.int_mismatch == 0
            && self.flips == 0
            && self.max.values().all(|&v| v <= tol)
    }
}

fn upd(m: &mut BTreeMap<&'static str, f64>, k: &'static str, a: f64, b: f64) {
    let d = (a - b).abs();
    let e = m.entry(k).or_insert(0.0);
    if d > *e {
        *e = d;
    }
}

pub fn check_corpus(path: &str) -> Result<Report, String> {
    let mut rdr = csv::Reader::from_path(path).map_err(|e| format!("abrir {path}: {e}"))?;
    let mut rep = Report {
        filas: 0,
        max: BTreeMap::new(),
        g6_mismatch: 0,
        mu_mismatch: 0,
        int_mismatch: 0,
        flips: 0,
        peor_flip: None,
        peor_mismatch: None,
    };

    for result in rdr.records() {
        let rec = result.map_err(|e| format!("fila CSV: {e}"))?;
        if rec.len() < 13 {
            return Err(format!("esperaba 13 columnas, hay {}", rec.len()));
        }
        let g6 = rec[0].to_string();
        let n: usize = rec[1].parse().map_err(|e| format!("n: {e}"))?;
        let mu: usize = rec[3].parse().map_err(|e| format!("mu: {e}"))?;
        let lam1: f64 = rec[2].parse().map_err(|e| format!("lam1: {e}"))?;
        let gap1: f64 = rec[4].parse().map_err(|e| format!("gap1: {e}"))?;
        let lam2: f64 = rec[5].parse().map_err(|e| format!("lam2: {e}"))?;
        let hc: f64 = rec[6].parse().map_err(|e| format!("hc: {e}"))?;
        let gap2: f64 = rec[7].parse().map_err(|e| format!("gap2: {e}"))?;
        let pi: f64 = rec[8].parse().map_err(|e| format!("pi: {e}"))?;
        let diam: usize = rec[9].parse().map_err(|e| format!("diam: {e}"))?;
        let k: usize = rec[10].parse().map_err(|e| format!("k: {e}"))?;
        let delta_k: f64 = rec[11].parse().map_err(|e| format!("delta_k: {e}"))?;
        let gap3: f64 = rec[12].parse().map_err(|e| format!("gap3: {e}"))?;

        let g = Graph::from_graph6(&g6)?;
        if g.n != n {
            return Err(format!("n desalineado: g6 dice {}, CSV dice {n} ({g6})", g.n));
        }
        if g.to_graph6() != g6 {
            rep.g6_mismatch += 1;
        }

        let c1 = cal1(&g);
        let c2 = cal2(&g);
        let c3 = cal3(&g);

        if c1.mu != mu {
            rep.mu_mismatch += 1;
            if rep.peor_mismatch.is_none() {
                rep.peor_mismatch = Some(format!("mu g6={g6} rust={} py={mu}", c1.mu));
            }
        }
        if c3.diam != diam || c3.k != k {
            rep.int_mismatch += 1;
            if rep.peor_mismatch.is_none() {
                rep.peor_mismatch =
                    Some(format!("diam/k g6={g6} rust=({},{}) py=({diam},{k})", c3.diam, c3.k));
            }
        }

        upd(&mut rep.max, "lam1", c1.lam1, lam1);
        upd(&mut rep.max, "gap1", c1.gap, gap1);
        upd(&mut rep.max, "lam2", c2.lam2, lam2);
        upd(&mut rep.max, "hc", c2.hc, hc);
        upd(&mut rep.max, "gap2", c2.gap, gap2);
        upd(&mut rep.max, "pi", c3.pi, pi);
        upd(&mut rep.max, "delta_k", c3.delta_k, delta_k);
        upd(&mut rep.max, "gap3", c3.gap, gap3);

        // FLIP: la clasificación de contraejemplo (gap>TOL_POS) debe coincidir.
        for (etq, rg, pg) in [("gap1", c1.gap, gap1), ("gap2", c2.gap, gap2), ("gap3", c3.gap, gap3)] {
            if (rg > TOL_POS) != (pg > TOL_POS) {
                rep.flips += 1;
                if rep.peor_flip.is_none() {
                    rep.peor_flip = Some(format!("{etq} g6={g6} rust={rg:.12} py={pg:.12}"));
                }
            }
        }
        rep.filas += 1;
    }
    Ok(rep)
}

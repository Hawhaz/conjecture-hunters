//! Seeds estructurales (§9): las familias donde históricamente MUEREN estas
//! conjeturas (evidencia 2021–2023). Port de `calibracion/ga_graphs.py`.
//! Con seeds, el GA cruza gap>0 ya en la generación 0 para CAL-1.

use crate::graph::Graph;
use crate::operators::{complete, cycle, path, star};
use crate::rng::Rng;
use crate::{N_MAX, N_MIN};

/// Estrella K_{1,n-1} (n vértices).
fn f_estrella(_rng: &mut Rng, n: usize) -> Graph {
    star(n)
}

/// Camino P_n.
fn f_camino(_rng: &mut Rng, n: usize) -> Graph {
    path(n)
}

/// Cometa: estrella + cola pendiente.
fn f_cometa(rng: &mut Rng, n: usize) -> Graph {
    let t = rng.range_incl(2, n - 4);
    let mut g = star(n - t);
    let mut prev = 0usize;
    for _ in 0..t {
        let nv = g.push_vertex();
        g.add_edge(prev, nv);
        prev = nv;
    }
    g
}

/// Cometa de doble cola DTC(n, p, q).
fn f_dtc(rng: &mut Rng, n: usize) -> Graph {
    let p = rng.range_incl(1, ((n - 6) / 2).max(1));
    let q = rng.range_incl(1, (n - 6 - p).max(1));
    let mut g = star(n - p - q);
    let mut prev = 0usize;
    for _ in 0..p {
        let nv = g.push_vertex();
        g.add_edge(prev, nv);
        prev = nv;
    }
    prev = 0;
    for _ in 0..q {
        let nv = g.push_vertex();
        g.add_edge(prev, nv);
        prev = nv;
    }
    g
}

/// Lollipop: K_g + camino pendiente.
fn f_lollipop(rng: &mut Rng, n: usize) -> Graph {
    let g_sz = rng.range_incl(3, (n / 2).max(3));
    let mut g = complete(g_sz);
    let mut prev = g_sz - 1;
    for _ in 0..(n - g_sz) {
        let nv = g.push_vertex();
        g.add_edge(prev, nv);
        prev = nv;
    }
    g
}

/// Turnip: ciclo impar g + hojas colgadas de un vértice.
fn f_turnip(rng: &mut Rng, n: usize) -> Graph {
    let tope = n.min(12);
    let impares: Vec<usize> = (3..tope).step_by(2).collect();
    let g_sz = if impares.is_empty() { 3 } else { *rng.choose(&impares) };
    let mut g = cycle(g_sz);
    for _ in 0..(n - g_sz) {
        let nv = g.push_vertex();
        g.add_edge(0, nv);
    }
    g
}

/// Kite: K_ω + camino pendiente.
fn f_kite(rng: &mut Rng, n: usize) -> Graph {
    let w = rng.range_incl(3, 8usize.min(n - 2));
    let mut g = complete(w);
    let mut prev = 0usize;
    for _ in 0..(n - w) {
        let nv = g.push_vertex();
        g.add_edge(prev, nv);
        prev = nv;
    }
    g
}

/// Dos estrellas T(2,b): centros de dos estrellas unidos a un vértice nuevo.
fn f_dos_estrellas(rng: &mut Rng, n: usize) -> Graph {
    let a = rng.range_incl(3, n - 5);
    let b = n - 1 - a;
    // primera estrella: centro 0, hojas 1..a-1 (a vértices)
    let mut g = star(a);
    // segunda estrella: centro `a`, hojas a+1..a+b-1 (b vértices)
    let centro2 = g.push_vertex(); // = a
    for _ in 1..b {
        let nv = g.push_vertex();
        g.add_edge(centro2, nv);
    }
    // vértice nuevo que une ambos centros
    let nuevo = g.push_vertex(); // = a + b = n - 1
    g.add_edge(0, nuevo);
    g.add_edge(centro2, nuevo);
    g
}

/// Peine 1: espina P_k con una hoja por vértice.
fn f_peine1(_rng: &mut Rng, n: usize) -> Graph {
    let k = n / 2;
    let mut g = path(k);
    for v in 0..k {
        if g.n < n {
            let nv = g.push_vertex();
            g.add_edge(v, nv);
        }
    }
    g
}

/// Peine 2: espina P_k con pata de largo 2 por vértice.
fn f_peine2(_rng: &mut Rng, n: usize) -> Graph {
    let k = (n / 3).max(2);
    let mut g = path(k);
    for v in 0..k {
        if g.n + 1 < n {
            let a = g.push_vertex();
            g.add_edge(v, a);
            let b = g.push_vertex();
            g.add_edge(a, b);
        }
    }
    g
}

type Familia = fn(&mut Rng, usize) -> Graph;
const FAMILIAS: [Familia; 10] = [
    f_estrella,
    f_camino,
    f_cometa,
    f_dtc,
    f_lollipop,
    f_turnip,
    f_kite,
    f_dos_estrellas,
    f_peine1,
    f_peine2,
];

/// Un individuo semilla: familia aleatoria con n ∈ [N_MIN, N_MAX]; si por algún
/// borde saliera inconexo, cae a un camino P_n (siempre conexo).
pub fn semilla_estructural(rng: &mut Rng) -> Graph {
    let n = rng.range_incl(N_MIN, N_MAX);
    let fam = FAMILIAS[rng.below(FAMILIAS.len())];
    let g = fam(rng, n);
    if g.n >= 3 && g.is_connected() {
        g
    } else {
        path(n)
    }
}

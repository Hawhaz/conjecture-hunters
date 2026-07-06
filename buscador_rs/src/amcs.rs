//! AMCS baseline (Vito–Stefanus 2023, arXiv 2306.07956), port de
//! `calibracion/amcs_baseline.py`. Es el "organismo baseline" obligatorio del GA
//! (§9): el estado del arte es el punto de partida de la población, no el rival.
//!
//! Movimientos NMCS: agregar hoja / subdividir arista / (grafos conexos) agregar
//! arista del complemento. AMCS: poda aleatoria + profundidad/nivel adaptativos
//! al estancarse. score>umbral ⇔ contraejemplo.

use crate::graph::Graph;
use crate::rng::Rng;

type Score<'a> = &'a dyn Fn(&Graph) -> f64;

fn agregar_hoja_aleatoria(g: &mut Graph, rng: &mut Rng) {
    let b = rng.below(g.n);
    let nv = g.push_vertex();
    g.add_edge(b, nv);
}

fn agregar_hoja(g: &mut Graph, v: usize) {
    let nv = g.push_vertex();
    g.add_edge(v, nv);
}

fn subdividir_aleatoria(g: &mut Graph, rng: &mut Rng) {
    let es = g.edges();
    if es.is_empty() {
        return;
    }
    let &(u, v) = rng.choose(&es);
    g.remove_edge(u, v);
    let w = g.push_vertex();
    g.add_edge(u, w);
    g.add_edge(w, v);
}

fn subdividir(g: &mut Graph, u: usize, v: usize) {
    g.remove_edge(u, v);
    let w = g.push_vertex();
    g.add_edge(u, w);
    g.add_edge(w, v);
}

/// Devuelve true si eliminó algo.
fn quitar_hoja_aleatoria(g: &mut Graph, rng: &mut Rng) -> bool {
    let hojas: Vec<usize> = (0..g.n).filter(|&v| g.degree(v) == 1).collect();
    if hojas.is_empty() {
        return false;
    }
    let v = *rng.choose(&hojas);
    g.remove_vertex(v);
    true
}

/// Contrae un vértice de grado 2 (o quita una hoja si no hay).
fn quitar_subdivision(g: &mut Graph, rng: &mut Rng) -> bool {
    let deg2: Vec<usize> = (0..g.n).filter(|&v| g.degree(v) == 2).collect();
    if deg2.is_empty() {
        return quitar_hoja_aleatoria(g, rng);
    }
    let v = *rng.choose(&deg2);
    let a = g.adj[v][0];
    let b = g.adj[v][1];
    g.remove_vertex(v);
    // reindexar a,b tras compactar etiquetas > v
    let a2 = if a > v { a - 1 } else { a };
    let b2 = if b > v { b - 1 } else { b };
    g.add_edge(a2, b2); // si ya existía, no-op (grafo simple), igual que en Sage
    true
}

// ------------------------------------------------------ NMCS (nmcs.sage)

fn nmcs_arboles(g: &Graph, depth: usize, level: usize, score: Score, rng: &mut Rng, es_padre: bool) -> Graph {
    let mut mejor = g.clone();
    let mut mejor_score = score(g);
    if level == 0 {
        let mut h = g.clone();
        for _ in 0..depth {
            if rng.chance(0.5) {
                agregar_hoja_aleatoria(&mut h, rng);
            } else {
                subdividir_aleatoria(&mut h, rng);
            }
        }
        if score(&h) > mejor_score {
            mejor = h;
        }
    } else {
        let mut cands: Vec<(u8, usize, usize)> = (0..g.n).map(|v| (0u8, v, 0)).collect();
        for (u, v) in g.edges() {
            cands.push((1, u, v));
        }
        for (t, a, b) in cands {
            let mut h = g.clone();
            if t == 0 {
                agregar_hoja(&mut h, a);
            } else {
                subdividir(&mut h, a, b);
            }
            let h2 = nmcs_arboles(&h, depth, level - 1, score, rng, false);
            let s = score(&h2);
            if s > mejor_score {
                mejor = h2;
                mejor_score = s;
                if g.n > 20 && es_padre {
                    break;
                }
            }
        }
    }
    mejor
}

fn nmcs_grafos_conexos(g: &Graph, depth: usize, level: usize, score: Score, rng: &mut Rng, es_padre: bool) -> Graph {
    let mut mejor = g.clone();
    let mut mejor_score = score(g);
    if level == 0 {
        let mut h = g.clone();
        for _ in 0..depth {
            let r = rng.f64();
            let no_aristas = h.non_edges();
            if r < 0.5 && !no_aristas.is_empty() {
                let &(u, v) = rng.choose(&no_aristas);
                h.add_edge(u, v);
            } else if r < 0.8 {
                agregar_hoja_aleatoria(&mut h, rng);
            } else {
                subdividir_aleatoria(&mut h, rng);
            }
        }
        if score(&h) > mejor_score {
            mejor = h;
        }
    } else {
        let mut cands: Vec<(u8, usize, usize)> = (0..g.n).map(|v| (0u8, v, 0)).collect();
        for (u, v) in g.edges() {
            cands.push((1, u, v));
        }
        for (u, v) in g.non_edges() {
            cands.push((2, u, v));
        }
        for (t, a, b) in cands {
            let mut h = g.clone();
            match t {
                0 => agregar_hoja(&mut h, a),
                1 => subdividir(&mut h, a, b),
                _ => h.add_edge(a, b),
            }
            let h2 = nmcs_grafos_conexos(&h, depth, level - 1, score, rng, false);
            let s = score(&h2);
            if s > mejor_score {
                mejor = h2;
                mejor_score = s;
                if g.n > 20 && es_padre {
                    break;
                }
            }
        }
    }
    mejor
}

// ------------------------------------------------------ AMCS (amcs.sage)

/// AMCS fiel al repo. `max_n` (extensión nuestra): cota superior de orden para
/// usarlo como baseline del GA con n ∈ [10, 40]. Devuelve el mejor grafo.
pub fn amcs(
    score: Score,
    inicial: Graph,
    max_depth: usize,
    max_level: usize,
    solo_arboles: bool,
    rng: &mut Rng,
    max_n: usize,
    umbral: f64,
) -> Graph {
    let score_capado = |g: &Graph| -> f64 {
        if g.n > max_n {
            f64::NEG_INFINITY
        } else {
            score(g)
        }
    };

    let mut depth = 0usize;
    let mut level = 1usize;
    let min_orden = inicial.n;
    let mut actual = inicial;

    while score_capado(&actual) <= umbral && level <= max_level {
        let mut siguiente = actual.clone();
        while siguiente.n > min_orden {
            if rng.f64() < depth as f64 / (depth as f64 + 1.0) {
                let ok = if rng.chance(0.5) {
                    quitar_hoja_aleatoria(&mut siguiente, rng)
                } else {
                    quitar_subdivision(&mut siguiente, rng)
                };
                if !ok {
                    break;
                }
            } else {
                break;
            }
        }
        let cand = if solo_arboles {
            nmcs_arboles(&siguiente, depth, level, &score_capado, rng, true)
        } else {
            nmcs_grafos_conexos(&siguiente, depth, level, &score_capado, rng, true)
        };
        if score_capado(&cand) > score_capado(&actual) {
            actual = cand;
            depth = 0;
            level = 1;
        } else if depth < max_depth {
            depth += 1;
        } else {
            depth = 0;
            level += 1;
        }
    }
    actual
}

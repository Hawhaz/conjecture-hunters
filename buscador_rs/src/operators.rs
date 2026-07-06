//! Operadores de mutación estructural (§9) + cruza con reparación de conexidad +
//! árbol etiquetado aleatorio (Prüfer). Port de `calibracion/ga_graphs.py`.

use crate::graph::Graph;
use crate::rng::Rng;
use crate::{N_MAX, N_MIN};

// ---------------------------------------------------------- constructores base

/// Estrella con `m` vértices: centro 0, hojas 1..m-1 (= K_{1,m-1}).
pub fn star(m: usize) -> Graph {
    let mut g = Graph::empty(m);
    for v in 1..m {
        g.add_edge(0, v);
    }
    g
}

/// Camino P_m: 0-1-...-(m-1).
pub fn path(m: usize) -> Graph {
    let mut g = Graph::empty(m);
    for v in 1..m {
        g.add_edge(v - 1, v);
    }
    g
}

/// Grafo completo K_m.
pub fn complete(m: usize) -> Graph {
    let mut g = Graph::empty(m);
    for u in 0..m {
        for v in (u + 1)..m {
            g.add_edge(u, v);
        }
    }
    g
}

/// Ciclo C_m.
pub fn cycle(m: usize) -> Graph {
    let mut g = path(m);
    if m >= 3 {
        g.add_edge(0, m - 1);
    }
    g
}

/// Árbol etiquetado aleatorio de orden n (decodificación de Prüfer).
pub fn random_tree(n: usize, rng: &mut Rng) -> Graph {
    if n <= 1 {
        return Graph::empty(n.max(1));
    }
    if n == 2 {
        return Graph::from_edges(2, &[(0, 1)]);
    }
    let seq: Vec<usize> = (0..n - 2).map(|_| rng.below(n)).collect();
    let mut degree = vec![1usize; n];
    for &x in &seq {
        degree[x] += 1;
    }
    let mut g = Graph::empty(n);
    let mut ptr = 0usize;
    while degree[ptr] != 1 {
        ptr += 1;
    }
    let mut leaf = ptr;
    for &v in &seq {
        g.add_edge(leaf, v);
        degree[leaf] -= 1;
        degree[v] -= 1;
        if degree[v] == 1 && v < ptr {
            leaf = v;
        } else {
            ptr += 1;
            while ptr < n && degree[ptr] != 1 {
                ptr += 1;
            }
            leaf = ptr;
        }
    }
    let restantes: Vec<usize> = (0..n).filter(|&i| degree[i] == 1).collect();
    if restantes.len() == 2 {
        g.add_edge(restantes[0], restantes[1]);
    }
    g
}

// ------------------------------------------------------------------ operadores

pub fn op_add_edge(g: &mut Graph, rng: &mut Rng) {
    let ne = g.non_edges();
    if !ne.is_empty() {
        let &(u, v) = rng.choose(&ne);
        g.add_edge(u, v);
    }
}

pub fn op_remove_edge_conexo(g: &mut Graph, rng: &mut Rng) {
    let mut edges = g.edges();
    rng.shuffle(&mut edges);
    for &(u, v) in edges.iter().take(8) {
        g.remove_edge(u, v);
        if g.is_connected() {
            return;
        }
        g.add_edge(u, v);
    }
}

pub fn op_rewire(g: &mut Graph, rng: &mut Rng) {
    op_remove_edge_conexo(g, rng);
    op_add_edge(g, rng);
}

pub fn op_graft_camino(g: &mut Graph, rng: &mut Rng) {
    let largo = rng.range_incl(1, 4);
    let mut base = rng.below(g.n);
    let steps = largo.min(N_MAX.saturating_sub(g.n));
    for _ in 0..steps {
        let nv = g.push_vertex();
        g.add_edge(base, nv);
        base = nv;
    }
}

pub fn op_hoja(g: &mut Graph, rng: &mut Rng) {
    if g.n < N_MAX {
        let b = rng.below(g.n);
        let nv = g.push_vertex();
        g.add_edge(b, nv);
    }
}

pub fn op_subdividir(g: &mut Graph, rng: &mut Rng) {
    if g.n < N_MAX {
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
}

pub fn op_podar_hoja(g: &mut Graph, rng: &mut Rng) {
    let hojas: Vec<usize> = (0..g.n).filter(|&v| g.degree(v) == 1).collect();
    if !hojas.is_empty() && g.n > N_MIN {
        let v = *rng.choose(&hojas);
        g.remove_vertex(v);
    }
}

type Op = fn(&mut Graph, &mut Rng);
const OPERADORES: [Op; 7] = [
    op_add_edge,
    op_remove_edge_conexo,
    op_rewire,
    op_graft_camino,
    op_hoja,
    op_subdividir,
    op_podar_hoja,
];

/// Aplica un operador aleatorio; si el resultado no es conexo o n<3, devuelve el original.
pub fn mutar(g: &Graph, rng: &mut Rng) -> Graph {
    let mut h = g.clone();
    let op = OPERADORES[rng.below(OPERADORES.len())];
    op(&mut h, rng);
    if h.n >= 3 && h.is_connected() {
        h
    } else {
        g.clone()
    }
}

/// Cruza: unión parcial de listas de aristas + reparación de conexidad (§9).
pub fn cruza(p1: &Graph, p2: &Graph, rng: &mut Rng) -> Graph {
    let n = p1.n.max(p2.n);
    let mut h = Graph::empty(n);
    for (u, v) in p1.edges() {
        h.add_edge(u, v);
    }
    for (u, v) in p2.edges() {
        if rng.chance(0.5) {
            h.add_edge(u, v);
        }
    }
    loop {
        let comps = h.components();
        if comps.len() <= 1 {
            break;
        }
        let ai = rng.below(comps.len());
        let mut bi = rng.below(comps.len());
        while bi == ai {
            bi = rng.below(comps.len());
        }
        let a = *rng.choose(&comps[ai]);
        let b = *rng.choose(&comps[bi]);
        h.add_edge(a, b);
    }
    h
}

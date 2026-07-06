//! Invariantes combinatorios: matching máximo (blossom de Edmonds) + métricas de
//! distancia (todos-pares por BFS, diámetro, proximidad π).
//!
//! `maximum_matching` es una cardinalidad ENTERA: cualquier algoritmo de matching
//! máximo correcto da el MISMO valor que `networkx.max_weight_matching(...,
//! maxcardinality=True)`, sin ambigüedad de punto flotante. El blossom aquí es el
//! clásico O(V^3) (e-maxx), validado contra Python sobre todo el atlas n<=7.

use crate::graph::Graph;

const NIL: usize = usize::MAX;

fn lca(base: &[usize], mate: &[usize], p: &[usize], n: usize, a0: usize, b0: usize) -> usize {
    let mut used = vec![false; n];
    let mut a = a0;
    loop {
        a = base[a];
        used[a] = true;
        if mate[a] == NIL {
            break;
        }
        a = p[mate[a]];
    }
    let mut b = b0;
    loop {
        b = base[b];
        if used[b] {
            return b;
        }
        b = p[mate[b]];
    }
}

fn mark_path(
    blossom: &mut [bool],
    base: &[usize],
    mate: &[usize],
    p: &mut [usize],
    v0: usize,
    b: usize,
    child0: usize,
) {
    let mut v = v0;
    let mut child = child0;
    while base[v] != b {
        blossom[base[v]] = true;
        blossom[base[mate[v]]] = true;
        p[v] = child;
        child = mate[v];
        v = p[mate[v]];
    }
}

/// Número de emparejamiento μ (cardinalidad del matching máximo) en grafo general.
pub fn maximum_matching(g: &Graph) -> usize {
    let n = g.n;
    let mut mate = vec![NIL; n];
    let mut p = vec![NIL; n];
    let mut base = vec![0usize; n];
    let mut used = vec![false; n];
    let mut blossom = vec![false; n];
    let mut q: std::collections::VecDeque<usize> = std::collections::VecDeque::new();

    for root in 0..n {
        if mate[root] != NIL {
            continue;
        }
        for i in 0..n {
            p[i] = NIL;
            used[i] = false;
            base[i] = i;
        }
        used[root] = true;
        q.clear();
        q.push_back(root);
        let mut found = NIL;

        'bfs: while let Some(v) = q.pop_front() {
            for k in 0..g.adj[v].len() {
                let to = g.adj[v][k];
                if base[v] == base[to] || mate[v] == to {
                    continue;
                }
                if to == root || (mate[to] != NIL && p[mate[to]] != NIL) {
                    let cur_base = lca(&base, &mate, &p, n, v, to);
                    for x in blossom.iter_mut() {
                        *x = false;
                    }
                    mark_path(&mut blossom, &base, &mate, &mut p, v, cur_base, to);
                    mark_path(&mut blossom, &base, &mate, &mut p, to, cur_base, v);
                    for i in 0..n {
                        if blossom[base[i]] {
                            base[i] = cur_base;
                            if !used[i] {
                                used[i] = true;
                                q.push_back(i);
                            }
                        }
                    }
                } else if p[to] == NIL {
                    p[to] = v;
                    if mate[to] == NIL {
                        found = to;
                        break 'bfs;
                    } else {
                        used[mate[to]] = true;
                        q.push_back(mate[to]);
                    }
                }
            }
        }

        if found != NIL {
            let mut u = found;
            while u != NIL {
                let pv = p[u];
                let ppv = mate[pv];
                mate[u] = pv;
                mate[pv] = u;
                u = ppv;
            }
        }
    }

    (0..n).filter(|&v| mate[v] != NIL).count() / 2
}

/// Distancias todos-pares por BFS (dist[i][j]); usize::MAX si inalcanzable.
pub fn all_pairs_distances(g: &Graph) -> Vec<Vec<usize>> {
    (0..g.n).map(|s| g.bfs_dist(s)).collect()
}

/// Diámetro = mayor distancia finita.
pub fn diameter(dist: &[Vec<usize>]) -> usize {
    let mut d = 0usize;
    for row in dist {
        for &x in row {
            if x != usize::MAX && x > d {
                d = x;
            }
        }
    }
    d
}

/// Transmisión t(v) = Σ_u d(v,u) (suma de la fila v).
pub fn transmissions(dist: &[Vec<usize>]) -> Vec<usize> {
    dist.iter()
        .map(|row| row.iter().map(|&x| if x == usize::MAX { 0 } else { x }).sum())
        .collect()
}

/// Proximidad π = min_v t(v) / (n-1).
pub fn proximity(dist: &[Vec<usize>], n: usize) -> f64 {
    let min_t = transmissions(dist).into_iter().min().unwrap_or(0);
    min_t as f64 / (n - 1) as f64
}

/// Lejanía ρ = max_v t(v) / (n-1).
pub fn remoteness(dist: &[Vec<usize>], n: usize) -> f64 {
    let max_t = transmissions(dist).into_iter().max().unwrap_or(0);
    max_t as f64 / (n - 1) as f64
}

//! Grafo simple no dirigido + codec graph6 (formato McKay) + BFS/conexidad.
//!
//! Nodos etiquetados 0..n-1. Listas de adyacencia ORDENADAS (invariante que usan
//! `has_edge` por búsqueda binaria y el codec graph6, que recorre el triángulo
//! superior en orden de columnas — el mismo orden que `networkx.to_graph6_bytes`).

use std::collections::VecDeque;

#[derive(Clone, Debug)]
pub struct Graph {
    pub n: usize,
    pub adj: Vec<Vec<usize>>, // listas de adyacencia ordenadas; grafo simple
}

impl Graph {
    pub fn empty(n: usize) -> Self {
        Graph { n, adj: vec![Vec::new(); n] }
    }

    pub fn from_edges(n: usize, edges: &[(usize, usize)]) -> Self {
        let mut g = Graph::empty(n);
        for &(u, v) in edges {
            g.add_edge(u, v);
        }
        g
    }

    #[inline]
    pub fn has_edge(&self, u: usize, v: usize) -> bool {
        self.adj[u].binary_search(&v).is_ok()
    }

    pub fn add_edge(&mut self, u: usize, v: usize) {
        if u == v || u >= self.n || v >= self.n {
            return;
        }
        if let Err(pos) = self.adj[u].binary_search(&v) {
            self.adj[u].insert(pos, v);
        }
        if let Err(pos) = self.adj[v].binary_search(&u) {
            self.adj[v].insert(pos, u);
        }
    }

    pub fn remove_edge(&mut self, u: usize, v: usize) {
        if let Ok(pos) = self.adj[u].binary_search(&v) {
            self.adj[u].remove(pos);
        }
        if let Ok(pos) = self.adj[v].binary_search(&u) {
            self.adj[v].remove(pos);
        }
    }

    #[inline]
    pub fn degree(&self, v: usize) -> usize {
        self.adj[v].len()
    }

    pub fn num_edges(&self) -> usize {
        self.adj.iter().map(|a| a.len()).sum::<usize>() / 2
    }

    /// Aristas (u, v) con u < v, en orden lexicográfico.
    pub fn edges(&self) -> Vec<(usize, usize)> {
        let mut e = Vec::with_capacity(self.num_edges());
        for u in 0..self.n {
            for &v in &self.adj[u] {
                if u < v {
                    e.push((u, v));
                }
            }
        }
        e
    }

    /// Pares NO adyacentes (u, v) con u < v.
    pub fn non_edges(&self) -> Vec<(usize, usize)> {
        let mut ne = Vec::new();
        for u in 0..self.n {
            for v in (u + 1)..self.n {
                if !self.has_edge(u, v) {
                    ne.push((u, v));
                }
            }
        }
        ne
    }

    pub fn is_connected(&self) -> bool {
        if self.n == 0 {
            return false;
        }
        let mut seen = vec![false; self.n];
        let mut q = VecDeque::new();
        seen[0] = true;
        q.push_back(0);
        let mut cnt = 1usize;
        while let Some(x) = q.pop_front() {
            for &y in &self.adj[x] {
                if !seen[y] {
                    seen[y] = true;
                    cnt += 1;
                    q.push_back(y);
                }
            }
        }
        cnt == self.n
    }

    /// Distancias BFS desde `src`; usize::MAX si inalcanzable.
    pub fn bfs_dist(&self, src: usize) -> Vec<usize> {
        let mut d = vec![usize::MAX; self.n];
        let mut q = VecDeque::new();
        d[src] = 0;
        q.push_back(src);
        while let Some(x) = q.pop_front() {
            let dx = d[x];
            for &y in &self.adj[x] {
                if d[y] == usize::MAX {
                    d[y] = dx + 1;
                    q.push_back(y);
                }
            }
        }
        d
    }

    /// Agrega un vértice aislado nuevo con índice n; devuelve su índice.
    pub fn push_vertex(&mut self) -> usize {
        let v = self.n;
        self.adj.push(Vec::new());
        self.n += 1;
        v
    }

    /// Elimina el vértice `v` compactando etiquetas a 0..n-2 (mantiene el orden).
    pub fn remove_vertex(&mut self, v: usize) {
        if v >= self.n {
            return;
        }
        self.adj.remove(v);
        self.n -= 1;
        for lst in self.adj.iter_mut() {
            lst.retain(|&x| x != v);
            for x in lst.iter_mut() {
                if *x > v {
                    *x -= 1;
                }
            }
        }
    }

    /// Componentes conexas (BFS) como listas de vértices.
    pub fn components(&self) -> Vec<Vec<usize>> {
        let mut comp = vec![usize::MAX; self.n];
        let mut out: Vec<Vec<usize>> = Vec::new();
        for s in 0..self.n {
            if comp[s] != usize::MAX {
                continue;
            }
            let id = out.len();
            let mut bucket = Vec::new();
            let mut q = VecDeque::new();
            comp[s] = id;
            q.push_back(s);
            while let Some(x) = q.pop_front() {
                bucket.push(x);
                for &y in &self.adj[x] {
                    if comp[y] == usize::MAX {
                        comp[y] = id;
                        q.push_back(y);
                    }
                }
            }
            out.push(bucket);
        }
        out
    }

    // ---------------------------------------------------------------- graph6

    /// Decodifica una cadena graph6 SIN header a `Graph`. Soporta las tres
    /// formas de N(n): 1 byte (n<=62), 126 + 3 bytes (n<=258047) y 126,126 + 6
    /// bytes. Orden de bits: triángulo superior por columnas (0,1)(0,2)(1,2)...
    pub fn from_graph6(s: &str) -> Result<Graph, String> {
        let bytes: Vec<u8> = s.trim().bytes().collect();
        if bytes.is_empty() {
            return Err("g6 vacío".into());
        }
        let (n, idx) = if bytes[0] == 126 {
            if bytes.len() >= 2 && bytes[1] == 126 {
                if bytes.len() < 8 {
                    return Err("g6 corto (forma 126,126)".into());
                }
                let mut val: u64 = 0;
                for i in 0..6 {
                    val = (val << 6) | ((bytes[2 + i] as u64).wrapping_sub(63) & 0x3f);
                }
                (val as usize, 8usize)
            } else {
                if bytes.len() < 4 {
                    return Err("g6 corto (forma 126)".into());
                }
                let mut val: u64 = 0;
                for i in 0..3 {
                    val = (val << 6) | ((bytes[1 + i] as u64).wrapping_sub(63) & 0x3f);
                }
                (val as usize, 4usize)
            }
        } else {
            ((bytes[0] as usize).wrapping_sub(63), 1usize)
        };

        let data = &bytes[idx..];
        let mut g = Graph::empty(n);
        let mut bitpos = 0usize;
        for j in 1..n {
            for i in 0..j {
                let byte_index = bitpos / 6;
                let bit_index = 5 - (bitpos % 6);
                if byte_index >= data.len() {
                    return Err(format!("g6 datos insuficientes (n={n})"));
                }
                let sixbits = (data[byte_index] as i32 - 63) as u8;
                if (sixbits >> bit_index) & 1 == 1 {
                    g.add_edge(i, j);
                }
                bitpos += 1;
            }
        }
        Ok(g)
    }

    /// Codifica a graph6 SIN header. Debe coincidir byte a byte con
    /// `networkx.to_graph6_bytes(G, header=False)` para nodos 0..n-1 en orden.
    pub fn to_graph6(&self) -> String {
        let n = self.n;
        let mut out: Vec<u8> = Vec::new();
        if n <= 62 {
            out.push(n as u8 + 63);
        } else if n <= 258047 {
            out.push(126);
            let v = n as u32;
            out.push(((v >> 12) & 0x3f) as u8 + 63);
            out.push(((v >> 6) & 0x3f) as u8 + 63);
            out.push((v & 0x3f) as u8 + 63);
        } else {
            out.push(126);
            out.push(126);
            let v = n as u64;
            for shift in [30u32, 24, 18, 12, 6, 0] {
                out.push(((v >> shift) & 0x3f) as u8 + 63);
            }
        }
        let mut cur: u8 = 0;
        let mut nb: u8 = 0;
        for j in 1..n {
            for i in 0..j {
                cur = (cur << 1) | if self.has_edge(i, j) { 1 } else { 0 };
                nb += 1;
                if nb == 6 {
                    out.push(cur + 63);
                    cur = 0;
                    nb = 0;
                }
            }
        }
        if nb > 0 {
            cur <<= 6 - nb; // padding de ceros a la derecha del último grupo
            out.push(cur + 63);
        }
        String::from_utf8(out).expect("graph6 es ASCII imprimible")
    }
}

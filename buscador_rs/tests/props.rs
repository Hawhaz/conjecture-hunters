//! Suite de propiedades / invarianza del motor `buscador_rs` — independiente de la
//! paridad Python (`parity.rs`) y de los fixtures publicados (`fixtures.rs`). Aquí
//! probamos LEYES MATEMÁTICAS que el código debe cumplir por sí mismo:
//!
//!   1) Invarianza bajo permutación de vértices (el detector clásico de bugs de
//!      índice): renombrar los vértices NO puede cambiar ningún invariante.
//!   2) Round-trip graph6 (`from_graph6 ∘ to_graph6 == id`) e idempotencia del
//!      codificador.
//!   3) μ (matching máximo, blossom de Edmonds) contra una fuerza bruta exacta
//!      independiente escrita aquí inline (n ≤ 12), incluyendo ciclos impares
//!      (blossoms), Petersen y completos.
//!   4) Formas cerradas exactas de docs/PAQUETE_1 §4 y docs/PAQUETE_2 §1.
//!
//! Sin dependencias nuevas (el toolchain windows-gnu se rompe con crates que
//! arrastran windows-sys/getrandom vía dlltool): solo `std` y el `Rng` del crate.

use buscador_rs::evaluators::{cal1, cal2, cal3, cota};
use buscador_rs::graph::Graph;
use buscador_rs::invariants::{
    all_pairs_distances, diameter, maximum_matching, proximity, remoteness,
};
use buscador_rs::rng::Rng;
use buscador_rs::spectral::{lam1, lam2};
use buscador_rs::operators::{complete, cycle, path, random_tree, star};

const TOL: f64 = 1e-9;

// --------------------------------------------------------------- helpers

fn approx(a: f64, b: f64) -> bool {
    (a - b).abs() < TOL
}

/// Grafo CONEXO aleatorio: árbol de Prüfer (garantiza conexidad y alcanza cualquier
/// n) + un número aleatorio de aristas extra. Cubre desde árboles (dispersos) hasta
/// casi-completos según `extra_frac`.
fn random_connected(rng: &mut Rng, n: usize, extra_frac: f64) -> Graph {
    let n = n.max(1);
    let mut g = random_tree(n, rng);
    if n >= 2 {
        // pares no adyacentes candidatos; agregamos ~extra_frac de ellos.
        let ne = g.non_edges();
        let target = ((ne.len() as f64) * extra_frac).round() as usize;
        // Fisher-Yates parcial sobre índices de `ne` para escoger `target` distintos.
        let mut idx: Vec<usize> = (0..ne.len()).collect();
        rng.shuffle(&mut idx);
        for &i in idx.iter().take(target) {
            let (u, v) = ne[i];
            g.add_edge(u, v);
        }
    }
    g
}

/// Reconstruye `g` con los vértices renombrados según la permutación `perm`
/// (perm[viejo] = nuevo). El grafo resultante es ISOMORFO al original.
fn relabel(g: &Graph, perm: &[usize]) -> Graph {
    let mut h = Graph::empty(g.n);
    for (u, v) in g.edges() {
        h.add_edge(perm[u], perm[v]);
    }
    h
}

/// Permutación aleatoria de 0..n (Fisher-Yates vía `Rng::shuffle`).
fn random_perm(rng: &mut Rng, n: usize) -> Vec<usize> {
    let mut p: Vec<usize> = (0..n).collect();
    rng.shuffle(&mut p);
    p
}

/// Conjunto de aristas canónico (u<v) para comparar grafos por igualdad estructural.
fn edge_set(g: &Graph) -> Vec<(usize, usize)> {
    let mut e = g.edges(); // ya vienen con u<v, lexicográficas
    e.sort_unstable();
    e
}

// -------------------------------------------- fuerza bruta exacta de μ (n ≤ 12)

/// Matching máximo EXACTO por búsqueda recursiva sobre el vértice de menor índice
/// aún libre (bitmask de vértices usados). Independiente del blossom del crate:
/// para cada vértice libre `v`, o bien lo dejamos sin emparejar, o lo emparejamos
/// con algún vecino libre `w`. Correcto para grafo general (no requiere
/// bipartición). Exponencial → solo n ≤ 12.
fn brute_matching(g: &Graph) -> usize {
    fn rec(g: &Graph, used: u32, first: usize) -> usize {
        // localizar el primer vértice libre desde `first`.
        let mut v = first;
        while v < g.n && (used >> v) & 1 == 1 {
            v += 1;
        }
        if v >= g.n {
            return 0;
        }
        // opción A: v queda sin emparejar.
        let mut best = rec(g, used | (1 << v), v + 1);
        // opción B: emparejar v con un vecino libre w (w>v basta: los w<v ya se
        // consideraron como "primer libre" en niveles previos, pero para grafo
        // general recorremos toda la adyacencia y filtramos libres).
        for &w in &g.adj[v] {
            if w != v && (used >> w) & 1 == 0 {
                let cand = 1 + rec(g, used | (1 << v) | (1 << w), v + 1);
                if cand > best {
                    best = cand;
                }
            }
        }
        best
    }
    assert!(g.n <= 12, "brute_matching solo para n<=12 (n={})", g.n);
    rec(g, 0, 0)
}

/// Grafo de Petersen (n=10), etiquetado estándar: pentágono exterior 0..4, pentagrama
/// interior 5..9, radios i—(i+5).
fn petersen() -> Graph {
    let mut e = Vec::new();
    for i in 0..5 {
        e.push((i, (i + 1) % 5)); // exterior C5
        e.push((5 + i, 5 + (i + 2) % 5)); // interior pentagrama
        e.push((i, 5 + i)); // radios
    }
    Graph::from_edges(10, &e)
}

/// K_{a,b} bipartito completo: parte A = 0..a, parte B = a..a+b.
fn complete_bipartite(a: usize, b: usize) -> Graph {
    let mut e = Vec::new();
    for u in 0..a {
        for v in 0..b {
            e.push((u, a + v));
        }
    }
    Graph::from_edges(a + b, &e)
}

// =====================================================================
// TEST 1 — Invarianza bajo permutación de vértices.
// =====================================================================

#[test]
fn t1_permutation_invariance() {
    let mut rng = Rng::seed(0x00C0_FFEE_1234_5678);
    let mut checked = 0usize;

    for _ in 0..500 {
        // n en [4, 22] para tener diámetro, k=⌊2D/3⌋ y espectro no triviales.
        let n = rng.range_incl(4, 22);
        // densidad variada: desde árbol (0.0) hasta bastante denso (0.7).
        let frac = rng.f64() * 0.7;
        let g = random_connected(&mut rng, n, frac);
        assert!(g.is_connected(), "generador produjo grafo desconexo n={n}");

        let perm = random_perm(&mut rng, g.n);
        let h = relabel(&g, &perm);

        // Mismo número de aristas y misma estructura salvo isomorfismo (sanity del relabel).
        assert_eq!(
            edge_set(&g).len(),
            edge_set(&h).len(),
            "relabel cambió #aristas g6={}",
            g.to_graph6()
        );

        // --- CAL-1: λ₁ (aprox), μ (EXACTO), gap1 (aprox) ---
        let a1 = cal1(&g);
        let b1 = cal1(&h);
        assert!(
            approx(a1.lam1, b1.lam1),
            "λ₁ no invariante: {} vs {} (g6={})",
            a1.lam1,
            b1.lam1,
            g.to_graph6()
        );
        assert_eq!(
            a1.mu,
            b1.mu,
            "μ no invariante: {} vs {} (g6={})",
            a1.mu,
            b1.mu,
            g.to_graph6()
        );
        assert!(
            approx(a1.gap, b1.gap),
            "gap1 no invariante: {} vs {} (g6={})",
            a1.gap,
            b1.gap,
            g.to_graph6()
        );

        // --- CAL-2: λ₂ (aprox), gap2 (aprox) ---
        let a2 = cal2(&g);
        let b2 = cal2(&h);
        assert!(
            approx(a2.lam2, b2.lam2),
            "λ₂ no invariante: {} vs {} (g6={})",
            a2.lam2,
            b2.lam2,
            g.to_graph6()
        );
        assert!(
            approx(a2.gap, b2.gap),
            "gap2 no invariante: {} vs {} (g6={})",
            a2.gap,
            b2.gap,
            g.to_graph6()
        );

        // --- CAL-3: π (aprox), diam (EXACTO), k (EXACTO), delta_k (aprox), gap3 (aprox) ---
        let a3 = cal3(&g);
        let b3 = cal3(&h);
        assert!(
            approx(a3.pi, b3.pi),
            "π no invariante: {} vs {} (g6={})",
            a3.pi,
            b3.pi,
            g.to_graph6()
        );
        assert_eq!(
            a3.diam,
            b3.diam,
            "diam no invariante: {} vs {} (g6={})",
            a3.diam,
            b3.diam,
            g.to_graph6()
        );
        assert_eq!(
            a3.k,
            b3.k,
            "k=⌊2D/3⌋ no invariante: {} vs {} (g6={})",
            a3.k,
            b3.k,
            g.to_graph6()
        );
        assert!(
            approx(a3.delta_k, b3.delta_k),
            "delta_k no invariante: {} vs {} (g6={})",
            a3.delta_k,
            b3.delta_k,
            g.to_graph6()
        );
        assert!(
            approx(a3.gap, b3.gap),
            "gap3 no invariante: {} vs {} (g6={})",
            a3.gap,
            b3.gap,
            g.to_graph6()
        );

        // --- funciones sueltas: lam1/lam2 (spectral) y proximity/remoteness invariantes ---
        assert!(approx(lam1(&g), lam1(&h)), "spectral::lam1 no invariante (g6={})", g.to_graph6());
        assert!(approx(lam2(&g), lam2(&h)), "spectral::lam2 no invariante (g6={})", g.to_graph6());
        let dg = all_pairs_distances(&g);
        let dh = all_pairs_distances(&h);
        // diameter(): invariante y consistente con cal3.diam.
        assert_eq!(
            diameter(&dg),
            diameter(&dh),
            "diameter() no invariante (g6={})",
            g.to_graph6()
        );
        assert_eq!(
            diameter(&dg),
            a3.diam,
            "diameter() ≠ cal3.diam (g6={})",
            g.to_graph6()
        );
        assert!(
            approx(proximity(&dg, g.n), proximity(&dh, h.n)),
            "proximity no invariante (g6={})",
            g.to_graph6()
        );
        assert!(
            approx(remoteness(&dg, g.n), remoteness(&dh, h.n)),
            "remoteness no invariante (g6={})",
            g.to_graph6()
        );

        checked += 1;
    }
    assert!(checked >= 500, "esperaba >=500 grafos, corrí {checked}");
}

// =====================================================================
// TEST 2 — Round-trip graph6 + idempotencia del codificador.
// =====================================================================

#[test]
fn t2_graph6_roundtrip() {
    let mut rng = Rng::seed(0x000A_11CE_BEEF_0002);
    let mut checked = 0usize;

    for _ in 0..2000 {
        // n variado hasta ~150 (cruza la frontera de 62 → forma 126,+3 bytes).
        // Sesgamos hacia n pequeño-medio pero permitimos grandes.
        let n = if rng.chance(0.15) {
            rng.range_incl(63, 150) // fuerza la codificación multibyte
        } else {
            rng.range_incl(1, 62)
        };
        let frac = rng.f64() * 0.6;
        let g = random_connected(&mut rng, n, frac);

        let s = g.to_graph6();
        let back = Graph::from_graph6(&s).expect("from_graph6 falló en round-trip");

        assert_eq!(back.n, g.n, "round-trip cambió n: {} -> {} (g6={s})", g.n, back.n);
        assert_eq!(
            edge_set(&back),
            edge_set(&g),
            "round-trip cambió el conjunto de aristas (n={}, g6={s})",
            g.n
        );

        // Idempotencia: re-codificar el decodificado da el MISMO string.
        let s2 = back.to_graph6();
        assert_eq!(s, s2, "to_graph6 no idempotente: {s} vs {s2}");

        checked += 1;
    }
    assert!(checked >= 2000, "esperaba >=2000 grafos, corrí {checked}");
}

// =====================================================================
// TEST 3 — μ (blossom) vs fuerza bruta exacta, n ≤ 12.
// =====================================================================

#[test]
fn t3_matching_vs_brute_force() {
    let mut rng = Rng::seed(0x00BA_DA55_0003);
    let mut checked = 0usize;

    // (a) Batería aleatoria: n ≤ 12, densidades variadas (incluye densos).
    for _ in 0..1000 {
        let n = rng.range_incl(1, 12);
        // frac alto con frecuencia para forzar grafos densos y muchos aumentos/blossoms.
        let frac = if rng.chance(0.4) { rng.f64() * 0.5 + 0.5 } else { rng.f64() };
        let g = random_connected(&mut rng, n, frac);
        let got = maximum_matching(&g);
        let exp = brute_matching(&g);
        assert_eq!(
            got,
            exp,
            "μ discrepa: blossom={got} brute={exp} (n={n}, g6={})",
            g.to_graph6()
        );
        checked += 1;
    }

    // (b) Casos estructurados que estresan blossoms y densidad:
    //     ciclos impares (odd cycles ⇒ blossoms), completos, Petersen.
    let mut structured: Vec<Graph> = Vec::new();
    for m in 3..=11 {
        structured.push(cycle(m)); // C_m: los impares fuerzan blossoms
        structured.push(complete(m)); // K_m: máxima densidad
        structured.push(path(m)); // P_m
        structured.push(star(m)); // K_{1,m-1}
    }
    // bipartitos pequeños dentro de n<=12
    structured.push(complete_bipartite(3, 3)); // K_{3,3}
    structured.push(complete_bipartite(2, 3)); // K_{2,3}
    structured.push(complete_bipartite(4, 4)); // K_{4,4}, n=8
    structured.push(complete_bipartite(5, 5)); // K_{5,5}, n=10
    structured.push(petersen()); // Petersen n=10

    for g in &structured {
        if g.n > 12 {
            continue;
        }
        let got = maximum_matching(g);
        let exp = brute_matching(g);
        assert_eq!(
            got,
            exp,
            "μ discrepa en caso estructurado: blossom={got} brute={exp} (n={}, g6={})",
            g.n,
            g.to_graph6()
        );
        checked += 1;
    }

    // Petersen explícito: μ debe ser 5 (matching perfecto) — chequeo doble.
    let p = petersen();
    assert_eq!(maximum_matching(&p), 5, "Petersen μ debe ser 5");
    assert_eq!(brute_matching(&p), 5, "Petersen brute μ debe ser 5");

    assert!(checked >= 1000, "esperaba >=1000 casos, corrí {checked}");
}

// =====================================================================
// TEST 4 — Formas cerradas exactas (PAQUETE_1 §4, PAQUETE_2 §1).
// =====================================================================

#[test]
fn t4_closed_forms() {
    // ---- K_n: λ₁ = n−1, μ = ⌊n/2⌋, π = ρ = 1 ----
    for n in 2..=15 {
        let k = complete(n);
        let c1 = cal1(&k);
        assert!(approx(c1.lam1, (n - 1) as f64), "K_{n} λ₁ = {} (esp {})", c1.lam1, n - 1);
        assert_eq!(c1.mu, n / 2, "K_{n} μ = {} (esp {})", c1.mu, n / 2);

        let d = all_pairs_distances(&k);
        // K_n con n>=2 tiene diámetro 1; π=ρ=1.
        assert!(approx(proximity(&d, n), 1.0), "K_{n} π = {} (esp 1)", proximity(&d, n));
        assert!(approx(remoteness(&d, n), 1.0), "K_{n} ρ = {} (esp 1)", remoteness(&d, n));
    }

    // ---- P_n: ρ = n/2 ----
    // t(extremo) = 1+2+...+(n-1) = n(n-1)/2 ⇒ ρ = t/(n-1) = n/2.
    for n in 2..=30 {
        let p = path(n);
        let d = all_pairs_distances(&p);
        assert!(
            approx(remoteness(&d, n), (n as f64) / 2.0),
            "P_{n} ρ = {} (esp {})",
            remoteness(&d, n),
            (n as f64) / 2.0
        );
    }

    // ---- C_n (n par): π = ρ = n² / (4(n−1)) ----
    for n in (4..=30).step_by(2) {
        let c = cycle(n);
        let d = all_pairs_distances(&c);
        let exp = (n * n) as f64 / (4.0 * (n as f64 - 1.0));
        assert!(
            approx(proximity(&d, n), exp),
            "C_{n} π = {} (esp {})",
            proximity(&d, n),
            exp
        );
        assert!(
            approx(remoteness(&d, n), exp),
            "C_{n} ρ = {} (esp {})",
            remoteness(&d, n),
            exp
        );
    }

    // ---- P_n, C_n (n impar): π = (n+1)/4 ----  (PAQUETE_2 §1)
    for n in (3..=29).step_by(2) {
        let exp = (n as f64 + 1.0) / 4.0;
        let pc = cycle(n);
        let dc = all_pairs_distances(&pc);
        assert!(
            approx(proximity(&dc, n), exp),
            "C_{n} (impar) π = {} (esp {})",
            proximity(&dc, n),
            exp
        );
        // P_n impar: el centro minimiza la transmisión y da la misma π (n+1)/4.
        let pp = path(n);
        let dp = all_pairs_distances(&pp);
        assert!(
            approx(proximity(&dp, n), exp),
            "P_{n} (impar) π = {} (esp {})",
            proximity(&dp, n),
            exp
        );
    }

    // ---- Estrella K_{1,n−1}: λ₁ = √(n−1), μ = 1, gap1 = 0 EXACTO ----
    // operators::star(m) construye K_{1,m-1} con m vértices.
    for n in 3..=50 {
        let s = star(n);
        let c1 = cal1(&s);
        assert!(
            approx(c1.lam1, ((n - 1) as f64).sqrt()),
            "K_1,{} λ₁ = {} (esp √{})",
            n - 1,
            c1.lam1,
            n - 1
        );
        assert_eq!(c1.mu, 1, "K_1,{} μ = {} (esp 1)", n - 1, c1.mu);
        // gap = cota(n) − (λ₁ + μ) = (√(n−1)+1) − (√(n−1)+1) = 0.
        assert!(approx(c1.gap, 0.0), "K_1,{} gap1 = {} (esp 0)", n - 1, c1.gap);
    }

    // ---- Petersen: λ₁ = 3, μ = 5 ----
    let pet = petersen();
    let cp = cal1(&pet);
    assert!(approx(cp.lam1, 3.0), "Petersen λ₁ = {} (esp 3)", cp.lam1);
    assert_eq!(cp.mu, 5, "Petersen μ = {} (esp 5)", cp.mu);

    // ---- Tabla CAL-1 §4: gaps exactos ----
    let sqrt2 = 2f64.sqrt();
    let sqrt3 = 3f64.sqrt();
    let sqrt5 = 5f64.sqrt();
    let sqrt6 = 6f64.sqrt();

    // K₃: gap = √2 + 1 − 3
    assert!(approx(cal1(&complete(3)).gap, sqrt2 + 1.0 - 3.0), "K₃ gap");
    // K₁₀: gap = 4 − 14 = −10
    assert!(approx(cal1(&complete(10)).gap, -10.0), "K₁₀ gap");
    // P₄: λ₁ = φ = (1+√5)/2, μ=2, gap = √3+1 − (φ+2)
    {
        let phi = (1.0 + sqrt5) / 2.0;
        let expected = sqrt3 + 1.0 - (phi + 2.0);
        assert!(approx(cal1(&path(4)).gap, expected), "P₄ gap");
    }
    // C₅: gap = 3 − 4 = −1
    assert!(approx(cal1(&cycle(5)).gap, -1.0), "C₅ gap");
    // C₆: gap = √5 + 1 − 5
    assert!(approx(cal1(&cycle(6)).gap, sqrt5 + 1.0 - 5.0), "C₆ gap");
    // K₂,₃: λ₁ = √6, μ = 2, gap = 3 − (√6 + 2)
    assert!(
        approx(cal1(&complete_bipartite(2, 3)).gap, 3.0 - (sqrt6 + 2.0)),
        "K₂,₃ gap"
    );
    // K₃,₃: λ₁ = 3, μ = 3, gap = √5 + 1 − 6
    assert!(
        approx(cal1(&complete_bipartite(3, 3)).gap, sqrt5 + 1.0 - 6.0),
        "K₃,₃ gap"
    );

    // sanity de la cota: cota(n) = √(n−1)+1
    assert!(approx(cota(5), 3.0), "cota(5) = √4 + 1 = 3");
    assert!(approx(cota(2), 2.0), "cota(2) = √1 + 1 = 2");
    assert!(approx(cota(10), 4.0), "cota(10) = √9 + 1 = 4");
}

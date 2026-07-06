# buscador_rs

Port a **Rust** del motor de BÚSQUEDA caza-contraejemplos (conjeturas de teoría
espectral de grafos). GA multi-carril paralelo (`rayon`), AMCS baseline,
operadores estructurales, seeds, BFS, matching (blossom de Edmonds) y espectro
(adyacencia y distancias) vía **faer**. Binario CLI que emite el **mismo CSV**
que `calibracion/ga_graphs.py`.

Motivación (directiva OTTY, 7-jul-2026): correr 20+ carriles en paralelo ~60×
más rápido. Python queda solo donde es estrictamente necesario: `evaluators/`
congelado (contrato pytest = oráculo de paridad), loop OpenEvolve/LLM (I/O-bound)
y el mock.

## Paridad (el contrato)

La trayectoria estocástica del GA **no** busca paridad con Python (imposible
entre el Mersenne Twister de `random` y un PRNG Rust). Lo que se valida es el
**evaluador**: para el MISMO grafo (g6), el `gap` de Rust == `gap` de Python a
**1e-9**. Oráculo: `parity/parity_corpus.csv` (3212 grafos: atlas n≤7,
formas cerradas del §4, ambos `ga_log*.csv`, ~1500 aleatorios n∈[4,300], y los
fixtures A/B/C), generado por numpy/scipy/networkx.

Resultado (`cargo test --release`):

```
parity_corpus_1e9 ... ok      # 3212 grafos
  max|Δ gap1|=2.8e-13  max|Δ gap2|=8.2e-12  max|Δ gap3|=1.3e-12
  max|Δ lam1|=2.8e-13  max|Δ lam2|=4.8e-13  max|Δ pi|=0.0 (exacto)
  g6_mismatch=0  mu_mismatch=0  int_mismatch=0
fixture_a_cal1 ... ok         # Wagner/AMCS n=18, gap=+0.021810…
fixture_b_cal2 ... ok         # S15+S19  n=35, gap=+0.079501…
fixture_c_cal3 ... ok         # S191+P7+P5 n=203, D=12, gap=+0.000285…
```

Además, cada `best_g6` que emite el GA se re-evalúa con el oráculo Python:
`python ../parity/verify_ga_csv.py ../calibracion/runs/ga_log_rs.csv`
→ `max_abs_diff_gap_Py_Rust ≈ 5e-11`, contraejemplos reales, 0 falsos.

Reejecutable sobre cualquier corpus con el subcomando `buscador_rs paridad
--corpus X.csv`: recomputa cada invariante y reporta max|Δ| por columna, los
mismatches de μ/diam/k, y **flips** de clasificación (¿contraejemplo sí/no
difiere Py vs Rust?); sale con código ≠ 0 si algo excede 1e-9. Endurecido con un
corpus de estrés fresco (4894 g6 nuevos, n≤295, TODAS las estrellas k≤200 y
completos m≤60 — los detectores de cero exacto): **0 flips, 0 mismatches**.
`cargo clippy` limpio; math CAL-1/2/3 auditada contra arXiv:2306.07956.

## Los tres evaluadores

| id | conjetura | gap (>0 ⇔ contraejemplo) |
|----|-----------|--------------------------|
| CAL-1 | λ₁ + μ ≥ √(n−1)+1 | `(√(n−1)+1) − (λ₁ + μ)` |
| CAL-2 | λ₂ ≤ Hc | `λ₂ − Hc`, `Hc = Σ_{uv∈E} 2/(d_u+d_v)` |
| CAL-3 | π + ∂_⌊2D/3⌋ > 0 | `−(π + ∂_k)`, `k = ⌊2D/3⌋` |

`λ₁,λ₂` = mayor/2º-mayor eigenvalor de adyacencia; `μ` = matching máximo;
`π` = proximidad; `∂_k` = k-ésimo mayor eigenvalor de la matriz de distancias.

## Rendimiento

Benchmark en 12 hilos (`cargo run --release --bin bench`), evaluador EXACTO:

| n | CAL-1 ev/s | CAL-2 ev/s | CAL-3 ev/s |
|---|-----------|-----------|-----------|
| 20 | 8 600 | 9 500 | 7 800 |
| 40 | 2 700 | 2 900 | 2 100 |
| 80 | 870 | 845 | 650 |
| 150 | 219 | 209 | 168 |
| 300 | 48 | 49 | 36 |

- **Rust vs Python** (mismo lote de 2000 g6, CAL-1): 1 618 vs 51 evals/sec →
  **31.5× más rápido** que `evaluators.agx_l1_mu.gap_grafo`.
- **Lote paralelo** (rayon, `batch::eval_batch`): 1 078 → 10 832 evals/sec =
  **10.0× en 12 núcleos** (casi lineal) → ~200× de throughput efectivo para el
  barrido masivo del futuro loop LLM.
- **GA multi-carril**: ~22 000 evals/sec (8 carriles, 12 hilos).
- Cuello de botella = la descomposición espectral densa O(n³) (faer), inherente
  al cálculo EXACTO; CAL-3 la paga dos veces (adyacencia + distancias). No es el
  matching ni el BFS.

## Certificado exacto (proof-grade) — `certificados/`

El umbral 1e-9 del hot path es seguro (margen ~1e8 sobre los fixtures), pero un
contraejemplo FINAL se certifica aparte con aritmética exacta / de precisión
arbitraria, independiente del f64: `python certificados/verify.py --fixtures`.

- n ≤ 40: polinomio característico ENTERO (sympy) + aislamiento de raíz por Sturm
  → cota inferior EXACTA de gap (A: `√17 − 447316/109067`; B: `357801/4500580`).
- n > 40: `mpmath` a 80 dígitos + cota a-posteriori de Weyl (‖Dx − θx‖) con
  separación de vecinos que fija el índice k (C, n=203: margen `+0.000284962699…`).

Cazador de falsos positivos de f64: K₅ bajo CAL-3 tiene gap EXACTAMENTE 0 (numpy
reporta +9e-16) → el certificado se NIEGA a certificar. Ese es su rol: la última
compuerta antes de declarar un contraejemplo.

## Build en Windows (toolchain `x86_64-pc-windows-gnu`) — ⚠️ leer

El MinGW *self-contained* de rustup trae `dlltool.exe` pero **no** `as.exe`, así
que cualquier crate que genere import libraries (`windows-sys`, `getrandom`)
rompe el build (`dlltool ... CreateProcess`). Solución adoptada: **evitar esos
crates**. Por eso las dependencias son mínimas (`faer` sin feature `rand`,
`rayon`, `csv`) y el PRNG y el parseo de args van hand-rolled (sin `rand`/`clap`).

`dlltool.exe` igual debe estar en el PATH para el enlazado final; se antepone su
directorio:

```bat
set "PATH=%USERPROFILE%\.rustup\toolchains\stable-x86_64-pc-windows-gnu\lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained;%PATH%"
cargo build --release
cargo test  --release
```

En **Linux** (los MI300X del evento) nada de esto aplica: `cargo build --release`
directo. La primera compilación baja/compila `gemm`+`faer` (~6 min, una vez;
luego queda en caché).

## Uso (CLI)

```bat
target\release\buscador_rs.exe --runs 20 --eval cal1 --out ..\calibracion\runs\ga_log_rs.csv
```

Flags: `--runs --gens --pop --elite --semilla-base --amcs-depth --amcs-level
--sin-seeds --eval {cal1|cal2|cal3} --out`. (`--help` para el detalle.)

- **Con seeds (familias §9):** cruza gap>0 en la generación 0 (como el
  `ga_log.csv` de Python).
- **`--sin-seeds` (árboles) + `--amcs-depth 1 --amcs-level 0`:** estrés de
  dinámica; el GA sube por mutación a lo largo de generaciones (curva del
  dashboard).

CSV emitido (idéntico a `ga_graphs.py`): `corrida,gen,best_gap,best_g6,n,evento,epoch`.

## Arquitectura

```
src/
  graph.rs        Grafo simple + codec graph6 (McKay) + BFS/conexidad/componentes
  spectral.rs     λ₁, λ₂, espectro de distancias (faer, self_adjoint_eigenvalues)
  invariants.rs   matching máximo (blossom Edmonds O(V³)) + distancias/π/diámetro
  evaluators.rs   CAL-1 / CAL-2 / CAL-3 (con todos los sub-invariantes)
  rng.rs          xoshiro256++ sembrado con splitmix64 (determinista, sin deps)
  paritycheck.rs  chequeo de paridad reutilizable (subcomando `paridad`, flips)
  batch.rs        evaluación por lotes en paralelo (rayon) — throughput ×núcleos
  operators.rs    7 operadores + cruza + árbol aleatorio (Prüfer) + constructores
  seeds.rs        10 familias estructurales (§9) donde mueren estas conjeturas
  amcs.rs         AMCS baseline (port de amcs_baseline.py)
  ga.rs           GA multi-carril paralelo (rayon) + fitness + torneo + CSV
  main.rs         CLI
tests/
  parity.rs       3212 g6 vs oráculo Python a 1e-9 (μ, diam, k exactos; g6 round-trip)
  fixtures.rs     A/B/C: contraejemplos publicados por CAL-1/2/3
  props.rs        invarianza por permutación, round-trip g6, μ vs fuerza bruta, formas cerradas
bin/
  bench.rs        suite de benchmarks (throughput, GA, serial vs paralelo)
(raíz del repo)
  certificados/   verify.py — certificado EXACTO proof-grade (sympy/mpmath)
```

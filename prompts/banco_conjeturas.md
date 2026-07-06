# banco_conjeturas.md — Banco de conjeturas de calibración (CAL-1/2/3)

> Fuente de verdad: `docs/PAQUETE_2_cards_portafolio.md` §2. Este archivo
> resume esas tres cards en el formato que necesita el mutador (desigualdad +
> fórmula de gap + pistas de movimientos), para que `ollama_cliente.py` pueda
> insertar el bloque correcto en `{conjetura}` según cuál carril esté corriendo.
> Los evaluadores en `evaluators/` son la fuente ejecutable; si algo aquí y el
> código de evaluación difieren, el código manda.

---

## CAL-1 · λ₁ + μ ≥ √(n−1) + 1

**Desigualdad publicada** (AutoGraphiX 2006 / Aouchiche–Hansen 2010, todo grafo
conexo, n ≥ 3): `λ₁(G) + μ(G) ≥ √(n−1) + 1`, donde `λ₁` es el mayor eigenvalor
de la matriz de adyacencia y `μ` es el tamaño del matching máximo.

**Fórmula de gap** (evaluador: `evaluators/agx_l1_mu.py::gap_grafo`):

```
gap(G) = (√(n−1) + 1) − (λ₁ + μ)        # gap > 0 ⇔ contraejemplo
```

**Pistas de movimiento**: refutada por Wagner 2021 y re-encontrada por AMCS
2023 (12 iteraciones, 46 s) partiendo de un ÁRBOL de orden 5. La familia
extremal es la **estrella pura** o el **cometa** (estrella + una cola corta):
en una estrella, `λ₁ = √(n-1)` crece igual de rápido que la cota misma,
mientras que `μ` se queda clavado en 1 (una estrella solo puede emparejar UNA
arista) — el gap se acerca a 0 según crece `n`, y una cola corta o una segunda
rama desbalanceada puede empujarlo a positivo. Movimientos que históricamente
suben este gap: `add_leaf` (crecer las hojas de la estrella), `densify_toward_family`
hacia "estrella pura", y `grow_double_tailed_comet` (separar la cola en dos
más cortas para intentar que `μ` no crezca al mismo ritmo que `λ₁`). Evita
`add_edge` entre hojas: cualquier arista hoja-hoja sube `μ` de inmediato y
generalmente EMPEORA el gap.

---

## CAL-2 · λ₂ ≤ Hc(G)

**Desigualdad publicada** (Favaron–Mahéo–Saclé 1993, Graffiti II, todo grafo):
`λ₂(G) ≤ Hc(G)`, donde `λ₂` es el segundo mayor eigenvalor de la matriz de
adyacencia y `Hc(G) = Σ_{uv∈E} 2/(d_u + d_v)` es el índice armónico.

**Fórmula de gap**:

```
gap(G) = λ₂(G) − Hc(G)                   # gap > 0 ⇔ contraejemplo
```

**Pistas de movimiento**: refutada por AMCS 2023 con el fixture de referencia
(ver `tests/fixtures/fixture_c4_estrellas.g6`, construido en
`calibracion/construir_fixtures_b_c.py::construir_B`): **los centros de dos
estrellas `S15` y `S19` unidos a un vértice nuevo** (n = 35, λ₂≈?, gap
verificado > 0 en la construcción). El mecanismo: una estrella sola tiene
`λ₂ = 0` (o negativo), pero DOS fuentes de grado alto conectadas producen un
segundo eigenvalor positivo grande, mientras `Hc` se mantiene bajo porque casi
todas las aristas siguen siendo centro-hoja de grado muy dispar (`2/(d_u+d_v)`
pequeño). Movimiento de cabecera: `two_stars_join` (exactamente esta
construcción). Complementa con `add_leaf` para desbalancear más los tamaños de
las dos estrellas si el gap inicial de la unión no alcanza.

---

## CAL-3 · π + ∂⌊2D/3⌋ > 0, n ≥ 4

**Desigualdad publicada** (Aouchiche–Hansen 2016, DAM 213:17–25): para todo
grafo conexo con n ≥ 4, `π(G) + ∂_{⌊2D/3⌋}(G) > 0`, donde `π = min_v t(v)/(n−1)`
(transmisión mínima normalizada) y `∂_i` es el i-ésimo mayor eigenvalor de la
matriz de distancias `D` (`D` mayúscula también denota el diámetro — cuidado
con la notación superpuesta del paper).

**Fórmula de gap**:

```
k = ⌊2·diam(G)/3⌋
gap(G) = −(π(G) + ∂_k(G))                # gap > 0 ⇔ contraejemplo
```

**Pistas de movimiento**: la MÁS DURA de las tres — refutada solo por AMCS
2023 (16.5 min; NMCS, NRPA y deep-RL fallaron en encontrarla). Fixture de
referencia exacto (ver `tests/fixtures/fixture_c2_203.g6`, construido en
`calibracion/construir_fixtures_b_c.py::construir_C`): **el centro de una
estrella `S191` unido a un extremo de un camino `P7` y a un extremo de un
camino `P5`** (n = 203, diámetro = 12, score ≈ 0.00028 — un margen MUY
angosto, así que espera muchas iteraciones cerca de 0 antes de cruzar). El
mecanismo: una estrella gigante minimiza `π` (casi todos los vértices están a
distancia 1 o 2 del resto), y las dos colas cortas asimétricas (7 y 5, no
iguales) mueven el diámetro y el eigenvalor `∂_k` de la matriz de distancias a
un punto donde la suma se vuelve positiva por un margen mínimo. Movimiento de
cabecera: **estrella gigante + `graft_pendant_path` dos veces con largos
DISTINTOS** (nunca dos colas iguales — la asimetría es parte de la receta
publicada). Este es el techo de referencia: si el sistema re-encuentra esta
familia, estamos al nivel de AMCS.

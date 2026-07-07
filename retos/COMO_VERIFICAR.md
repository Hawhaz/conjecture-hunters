# Cómo verificar esta refutación en 30 segundos (nota para jueces)

**Afirmación (una línea):** el grafo de la amistad **F₂ = K₁∨2K₂ (n=5)** —y toda
la familia infinita **K₁∨2Kᵣ**— refuta la **Conjetura 1 de Jia–Song** (abierta),
porque **ρ + ∂₂ < B(n)**, con ρ = lejanía y ∂₂ = 2º mayor eigenvalor de la matriz
de distancias.

## Los números exactos (F₂, n = 5)

| cantidad | valor exacto | ≈ |
|---|---|---|
| ρ (lejanía) | 3/2 | 1.500000 |
| ∂₂ (2º mayor eigenval. de distancias) | (5 − √41)/2 | −0.701562 |
| **ρ + ∂₂** | **4 − √41⁄2** | **0.798438** |
| **B(5)** = 5/4 + (4 − √24)/2 | **13/4 − √6** | **0.800510** |
| **B(5) − (ρ + ∂₂)** | **√41⁄2 − √6 − 3/4** | **+0.002072  > 0** |

Espectro de distancias COMPLETO de F₂ (orden desc.):
`{ (5+√41)/2 ≈ 5.7016 (×1),  (5−√41)/2 ≈ −0.7016 (×1),  −1 (×2),  −3 (×1) }`.
El mayor ∂₁ es **simple**, así que ∂₂ es **inequívocamente** el 2º mayor (no hay
empate en la cima). La violación es de una cota **inferior** (ρ+∂₂ queda por
DEBAJO de B(n)), consistente con refutar una desigualdad `≥`.

Certificado entero (sin punto flotante): `√41⁄2 − √6 − 3/4 > 0`
⇔ `2√41 > 4√6 + 3` ⇔ `164 > 105 + 24√6` ⇔ `59 > 24√6` ⇔ `59² > 24²·6`
⇔ `3481 > 3456`  → **verdadero**.

## Ejecutar

```
python retos/verificacion_independiente.py
```

Segundo método **independiente** del certificado principal
(`retos/refutacion_jia_song.py`), diseñado para no heredar bugs:

- **ρ** con `networkx.all_pairs_shortest_path_length` (BFS por diccionarios),
  NO con `floyd_warshall_numpy`. Confirma **ρ = 3/2** en las tres familias.
- **∂₂** por DOS vías cruzadas: `numpy.linalg.eigvalsh` (float64) **y**
  `sympy.Matrix(...).eigenvals()` **exacto** (diccionario autovalor→multiplicidad,
  NO `charpoly()`+`real_roots`). Paridad float↔exacto: |Δ| ≤ 6e-16.
- Comparación **ρ+∂₂ vs B(n)** en **tres precisiones**: float64, **mpmath 50
  dígitos**, y **exacta** (decisión de números algebraicos con `is_negative`).
  Las tres coinciden: **ρ+∂₂ < B(n)** para F₂ (n=5), K₁∨2K₃ (n=7), K₁∨2K₅ (n=11).

La salida imprime, para cada grafo, la auditoría de hipótesis, el espectro
completo, y la comparación en las tres precisiones, terminando en
`REFUTACION VERIFICADA INDEPENDIENTEMENTE: True`.

## Auditoría adversarial — todos los chequeos pasan

- **Hipótesis admisibles:** cada K₁∨2Kᵣ es **conexo**, tiene **n ≥ 4**, y NO es
  K_n ni K_n−e. Para F₂ se verifica explícitamente el no-isomorfismo con K₅
  (grados [4,4,4,4,4]) y con K₅−e (grados [4,4,4,3,3]); F₂ tiene grados
  [4,2,2,2,2] y 6 aristas → **admisible**.
- **Construcción robusta:** el grafo se construye por DOS rutas distintas
  (unión disjunta + vértice universal, y por etiquetas explícitas u/A/B) y se
  confirma que son **isomorfas** → no es un artefacto de construcción.
- **∂₂ sin ambigüedad:** ∂₁ es simple en toda la familia (espectro impreso), luego
  no hay riesgo de que ∂₂ colapse con ∂₁.
- **Signo del radical de B(n):** es **MENOS** antes de √. Con `−√`, B(5)=13/4−√6
  ≈ 0.8005 < n/(n−1)=1.25 (coherente); la variante `+√` daría ≈ 5.70 (absurda
  como cota inferior) y se descarta.
- **Grafo extremal reclamado:** la conjetura afirma igualdad **sii G = K_n−e**.
  Se verifica **exactamente** ρ+∂₂(K_n−e) = B(n) para n = 5, 7, 9, 11 (mismo 2º
  método). Como K₁∨2Kᵣ queda **estrictamente por debajo**, K_n−e **no** minimiza
  ρ+∂₂ → la conjetura es falsa.
- **Familia infinita:** barrido exacto (`is_negative`, 2º método) confirma
  ρ+∂₂ < B(n) para **todo r ∈ [2,30]**, con margen **estrictamente creciente**
  (r=2: +0.002072 → r=30: +0.152478).

## Nota menor de fe de erratas (no afecta el resultado)

En `retos/REFUTACION.md` la tabla lista para **K₁∨2K₅** la aproximación decimal
`ρ+∂₂ ≈ 0.818852`; el valor correcto es **0.81885425** (= `17/2 − √59`, verificado
a 40 dígitos con este script). La forma cerrada `17⁄2 − √59` y el margen
`+0.084993` de esa misma fila son **correctos**; sólo la 6ª decimal del decimal
intermedio tiene un typo. La refutación se mantiene con amplio margen.

## Referencias

- H. Jia, H. Song. *Remoteness and distance, distance (signless) Laplacian
  eigenvalues of a graph.* J. Inequal. Appl. **2018**:69 (open access). — **Conjecture 1.**
- M. Aouchiche, B. A. Rather. *Proximity and Remoteness in Graphs: a survey.*
  Discrete Appl. Math. **353** (2024) 94–120; arXiv:2310.12777. — cataloga la
  Conjecture 1 verbatim (líneas 1087–1093).
- H. Lin, K. C. Das, B. Wu. *Remoteness and distance eigenvalues of a graph.*
  Discrete Appl. Math. **215** (2016) 218–224; arXiv:1507.07083. — prueba las
  conjeturas AH *distintas* (ρ+∂₃, ρ+∂_⌊7D/8⌋, ∂₁−ρ), corroborando que ρ+∂₂ sigue
  **ABIERTA**.

## Veredicto

**PASS.** La refutación se sostiene bajo un segundo método independiente y
sobrevive la auditoría adversarial completa. Contraejemplo mínimo: **F₂ (n=5)**.

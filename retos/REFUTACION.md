# Refutación de la Conjetura 1 de Jia–Song (distancia-espectral, abierta)

**Resultado:** una **familia infinita de contraejemplos** — con el más pequeño el
**grafo de la amistad F₂ (n=5)** — a una conjetura publicada y **abierta** sobre
lejanía (remoteness) y el segundo mayor eigenvalor de la matriz de distancias.
Demostrado con **aritmética exacta** (sin punto flotante).

## La conjetura (abierta)

Jia & Song, *"Remoteness and distance, distance (signless) Laplacian eigenvalues
of a graph"*, J. Inequal. Appl. **2018**:69, **Conjetura 1**; catalogada verbatim
como **Conjecture 1** en el survey de Aouchiche & Rather, *"Proximity and
Remoteness in Graphs: a survey"*, Discrete Appl. Math. **353** (2024) 94–120
(arXiv:2310.12777):

> Sea `G ≇ {Kₙ, Kₙ − e}` un grafo **conexo** de orden `n ≥ 4` con lejanía `ρ`.
> Entonces
> ```
> ρ + ∂₂  ≥  n/(n−1) + (n−1 − √((n−1)²+8))/2   =:  B(n)
> ```
> con igualdad si y sólo si `G = Kₙ − e`.

donde `ρ` = lejanía = máximo sobre los vértices de la distancia promedio a los
demás, y `∂₂` = **segundo mayor** eigenvalor de la matriz de distancias.

**Estado:** ABIERTA. Nunca demostrada. (Lin–Das–Wu 2016, arXiv:1507.07083,
demostraron las conjeturas AH *distintas* `ρ+∂₃>0`, `ρ+∂_⌊7D/8⌋>0` y la cota
`∂₁−ρ` —que usa `+√`—, no ésta.) La cota trivial `ρ+∂₂ ≥ 0` (igualdad sólo en
`Kₙ`) sí está probada, pero es **más débil** que `B(n)`.

## El contraejemplo: la familia `K₁ ∨ 2Kᵣ`

`K₁ ∨ 2Kᵣ` = un **vértice universal** unido a **dos** cliques `Kᵣ` disjuntos
(orden `n = 2r+1`, diámetro 2). El menor, `r = 2`, es `K₁ ∨ 2K₂` = dos triángulos
que comparten un vértice = el **grafo de la amistad / corbatín F₂** (n=5).

Todos satisfacen las hipótesis (conexo, `≠ Kₙ, Kₙ−e`, `n ≥ 4`) y cumplen
`ρ + ∂₂ < B(n)` (violan la cota):

| grafo | n | ρ + ∂₂ (exacto) | B(n) (exacto) | B − (ρ+∂₂) |
|---|---|---|---|---|
| K₁∨2K₂ = **F₂** | 5 | 4 − √41⁄2 ≈ 0.798438 | 13⁄4 − √6 ≈ 0.800510 | **+0.002072** |
| K₁∨2K₃ | 7 | 11⁄2 − √22 ≈ 0.809584 | 25⁄6 − √11 ≈ 0.850042 | +0.040458 |
| K₁∨2K₄ | 9 | 7 − 3√17⁄2 ≈ 0.815341 | 41⁄8 − 3√2 ≈ 0.882359 | +0.067018 |
| K₁∨2K₅ | 11 | 17⁄2 − √59 ≈ 0.818854 | 61⁄10 − 3√3 ≈ 0.903845 | +0.084993 |
| K₁∨2K₃₀ | 61 | 46 − √8161⁄2 | 1861⁄60 − √902 | +0.152478 |

El margen **crece** con `r`. Verificado EXACTAMENTE (sympy, decisión de números
algebraicos, sin punto flotante) para todo `r ∈ [2, 30]`.

## Formas cerradas (espectro de distancias de `K₁ ∨ 2Kᵣ`)

Por la simetría del grafo, el espectro de la matriz de distancias es:
`{ ∂₁, ∂₂, −(r+1) (×1), −1 (×(2r−2)) }` con `∂₁,∂₂ = ((3r−1) ± √((3r−1)²+8r))/2`.
De ahí, exactamente:

```
ρ(K₁∨2Kᵣ)      = 3/2                                  (constante en r)
∂₂(K₁∨2Kᵣ)     = ((3r−1) − √(9r²+2r+1)) / 2
ρ + ∂₂         = ((3r+2) − √(9r²+2r+1)) / 2
```

y `B(2r+1) = (2r+1)/(2r) + r − √(r²+2)`. La diferencia se reduce a

```
B − (ρ+∂₂) = √(9r²+2r+1)/2 − √(r²+2) − (r²−1)/(2r)  > 0   para todo r ≥ 2
```

(desigualdad algebraica elemental; se establece elevando al cuadrado; verificada
exacta para `r ≤ 30` y con margen estrictamente creciente).

## Certificado entero del caso mínimo (F₂, n=5)

`B(5) − (ρ+∂₂) = √41⁄2 − √6 − 3⁄4 > 0`, equivalente por manipulación a
`2√41 > 4√6 + 3` ⇔ `164 > 105 + 24√6` ⇔ `59 > 24√6` ⇔ `59² > 24²·6` ⇔
`3481 > 3456` — **verdadero por aritmética entera**. QED.

(Cruce de verificación: `Kₙ − e` sí alcanza `B(n)` —el extremal reclamado— para
`n = 5,7,9,…`; nuestra familia queda estrictamente por debajo, luego `Kₙ−e` **no**
minimiza `ρ+∂₂` y la conjetura es falsa.)

## Cómo lo halló el sistema

1. **Investigación** (agentes web, citada): se fijó el objetivo abierto correcto
   (Jia–Song Conj. 1) descartando hermanas ya probadas o triviales.
2. **Caza** con el evaluador exacto rápido sobre familias densas
   (`retos/jia_song.py`): `Kₙ` menos subgrafos del atlas + split + multipartitos →
   candidato `K₁∨(2K₃)`.
3. **Caracterización** exacta (`retos/rho_d2_familia.py`): el candidato es parte de
   la familia `K₁∨2Kᵣ`, toda por debajo de `Kₙ−e`.
4. **Certificado exacto** (`retos/refutacion_jia_song.py`): `ρ+∂₂ < B(n)` demostrado
   con sympy (números algebraicos) + certificado entero para F₂.

## Reproducir

```
python retos/refutacion_jia_song.py
```
→ imprime la tabla exacta, la decisión `is_positive` para `r∈[2,30]`, y el
certificado entero de F₂.

## Referencias

- H. Jia, H. Song. *Remoteness and distance, distance (signless) Laplacian
  eigenvalues of a graph.* J. Inequal. Appl. 2018:69 (open access). — **Conjetura 1.**
- M. Aouchiche, B. A. Rather. *Proximity and Remoteness in Graphs: a survey.*
  Discrete Appl. Math. 353 (2024) 94–120; arXiv:2310.12777. — cataloga la Conj. 1
  verbatim (líneas 1087–1093).
- H. Lin, K. C. Das, B. Wu. *Remoteness and distance eigenvalues of a graph.*
  Discrete Appl. Math. 215 (2016) 218–224; arXiv:1507.07083. — demuestra las
  conjeturas AH *distintas* (`ρ+∂₃`, `ρ+∂_⌊7D/8⌋`, `∂₁−ρ`), no `ρ+∂₂`.
- M. Aouchiche, P. Hansen. *Proximity, remoteness and distance eigenvalues of a
  graph.* Discrete Appl. Math. 213 (2016) 17–25. — origen de las cotas `π,ρ` vs `∂ᵢ`.

## Nota de honestidad

El PDF primario de Aouchiche–Hansen 2016 (paywall) no se pudo abrir directamente;
el enunciado exacto que refutamos es el de **Jia–Song 2018, Conjetura 1**,
confirmado **verbatim** en el survey abierto de 2024 y su estado ABIERTO
corroborado por la fuente libre Lin–Das–Wu. Un único contraejemplo (F₂, n=5) ya
refuta la conjetura; la familia `K₁∨2Kᵣ` la refuta de forma fuerte (infinitos
contraejemplos).

---

## Cota corregida (propuesta)

Refutada la conjetura, buscamos el **minimizador verdadero** de `ρ+∂₂` sobre `G`
conexo, `G ∉ {Kₙ, Kₙ−e}`, `n ≥ 4`, y proponemos la **cota afilada corregida**
`B'(n)`. Reproducible: `python retos/mejora_jia_song.py`.

### El minimizador verdadero: el *join* balanceado de dos cliques

> **`T(n) := K₁ ∨ (Kₐ ∪ K_b)`** — un **vértice universal** unido a **dos cliques
> casi iguales**, con `a+b = n−1`, `|a−b| ≤ 1`, es decir
> `a = ⌊(n−1)/2⌋`, `b = ⌈(n−1)/2⌉` (diámetro 2).
> - **`n` impar** (`n=2r+1`): `a=b=r` ⟹ `T(n) = K₁ ∨ 2Kᵣ` (la familia de la
>   refutación; `r=2` ⟹ grafo de la amistad **F₂**).
> - **`n` par** (`n=2r+2`): `a=r`, `b=r+1` ⟹ `T(n) = K₁ ∨ (Kᵣ ∪ K_{r+1})`.

`T(n)` **generaliza** el contraejemplo `K₁∨2Kᵣ` (que sólo existe en `n` impar) al
minimizador correcto para **todo** `n`: cuando `n−1` es impar, el balance óptimo
reparte los vértices `⌊·⌋/⌈·⌉` entre las dos cliques.

### La cota corregida `B'(n) = ρ(T(n)) + ∂₂(T(n))`

Por la partición equitativa en 3 clases `(A, B, {u})`, el espectro de distancias de
`T(n)` es `{ −1 (×(n−3)), y 3 autovalores del cociente Q }`, con

```
Q = [[a−1, 2b, 1], [2a, b−1, 1], [a, b, 0]].
```

**`n` impar** (`a=b=r`): `Q` factoriza y da `−(r+1)` y las raíces de
`x² − (3r−1)x − 2r`. De ahí, **en forma cerrada**:

```
ρ(T)  = 3/2                                           (constante)
∂₂(T) = ((3r−1) − √(9r² + 2r + 1)) / 2
B'(n) = ((3r+2) − √(9r² + 2r + 1)) / 2                (r = (n−1)/2)
      = (3n+1)/4 − √(9n² − 14n + 9)/4                 (en n)
```

**`n` par** (`a=r`, `b=r+1`): el cúbico del cociente es **irreducible sobre ℚ**
(no es un radical simple; `∂₂` es un `CRootOf` genuino):

```
ρ(T)  = (3n−2) / (2(n−1))
∂₂(T) = 2ª mayor raíz real de   4x³ − (4n−12)x² − (3n²+2n−12)x − (2n²−4) = 0
B'(n) = ρ(T) + ∂₂(T)
```

Ambas formas verificadas EXACTAMENTE contra el cómputo directo del grafo (sympy)
para `n = 5..15`.

### Relación con Jia–Song y honestidad de alcance

`B'(n)` **mejora estrictamente** la cota original `B(n)` (i.e. `B'(n) < B(n)`,
luego Jia–Song es falsa ahí) **exactamente para `n` impar ≥ 5 y `n` par ≥ 10**:

| n | paridad | `T(n)` | `B'(n)` verdadero | `B(n)` vieja | `B(n)−B'(n)` | refuta |
|---|---|---|---|---|---|---|
| 4 | par | K₁∨(K₁∪K₂) | 0.9502036 | 0.7717805 | −0.178423 | **no** |
| 5 | impar | **F₂**=K₁∨2K₂ | 4 − √41⁄2 ≈ 0.7984379 | 0.8005103 | +0.002072 | sí |
| 6 | par | K₁∨(K₂∪K₃) | 0.9040748 | 0.8277187 | −0.076356 | **no** |
| 7 | impar | K₁∨2K₃ | 11⁄2 − √22 ≈ 0.8095842 | 0.8500419 | +0.040458 | sí |
| 8 | par | K₁∨(K₃∪K₄) | 0.8839106 | 0.8679399 | −0.015971 | **no** |
| 9 | impar | K₁∨2K₄ | 7 − 3√17⁄2 ≈ 0.8153416 | 0.8823593 | +0.067018 | sí |
| 10 | par | K₁∨(K₄∪K₅) | 0.8726610 | 0.8941206 | +0.021460 | sí |
| 11 | impar | K₁∨2K₅ | 17⁄2 − √59 ≈ 0.8188543 | 0.9038476 | +0.084993 | sí |
| 13 | impar | K₁∨2K₆ | 10 − √337⁄2 ≈ 0.8212201 | 0.9189193 | +0.097699 | sí |
| 15 | impar | K₁∨2K₇ | 23⁄2 − √114 ≈ 0.8229218 | 0.9300001 | +0.107078 | sí |

**Honestidad — `n ∈ {4, 6, 8}`:** ahí el mínimo verdadero queda **por encima** de
`B(n)` (verificado: **ningún** grafo de las familias ricas viola `B(n)`), de modo
que en esos tres órdenes pequeños y pares la cota de Jia–Song **sí es válida** y
`B'(n) > B(n)`. La refutación es real pero **no universal en `n`**: los
contraejemplos son precisamente `{n impar ≥ 5} ∪ {n par ≥ 10}`.

### Rigor / confianza en que es el mínimo GLOBAL

- **`n ≤ 7`: EXHAUSTIVO** (`networkx.graph_atlas_g()` = TODOS los grafos). `T(n)`
  es el minimizador **global exacto** y **nada** lo mejora (`B'(n) ≤ ρ+∂₂` sobre
  todo grafo conexo `∉{Kₙ,Kₙ−e}`). Confirma **F₂ como mínimo en `n=5`**.
- **`8 ≤ n ≤ 11`: FAMILIAS ricas** (el atlas no llega): `K₁∨(k cliques)`,
  `K_s∨(cliques)`, split completo, multipartito completo, kites, `Kₙ−H` con `H`
  del atlas. `T(n)` es el minimizador **en todas** ellas (≈80–110 grafos/`n`).
- **`n ≥ 12`: CONJETURADO.** Misma estructura balanceada; verificado contra las
  mismas familias. **No** es prueba de minimalidad global más allá de `n=11`.

### Certificado entero del caso mínimo (heredado)

`B(5) − B'(5) = √41⁄2 − √6 − 3⁄4 > 0` ⟺ `59² = 3481 > 3456 = 24²·6`
(aritmética **entera**). QED para el contraejemplo mínimo `F₂`.

Todo el cálculo es **exacto** (sympy: `ρ` racional, `∂₂` algebraico vía charpoly
entero + `real_roots`, decisiones de signo por números algebraicos, sin punto
flotante). Deliverable: `retos/mejora_jia_song.py`.

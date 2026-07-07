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
| K₁∨2K₅ | 11 | 17⁄2 − √59 ≈ 0.818852 | 61⁄10 − 3√3 ≈ 0.903845 | +0.084993 |
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

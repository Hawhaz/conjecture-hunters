# `certificados/` — Capa de certificación proof-grade (precisión y exactitud)

Última compuerta antes de afirmar que un grafo **refuta** una de las conjeturas
CAL-1 / CAL-2 / CAL-3. El buscador (`buscador_rs/`, `calibracion/ga_graphs.py`)
encuentra *candidatos* comparando `gap` en `float64`; esta capa los convierte en
**teoremas** —o los rechaza— demostrando `gap > 0` de forma **rigurosa**, no como
comparación de punto flotante.

No participa en la búsqueda. Corre **solo sobre candidatos finales**, por lo que
puede ser lenta (segundos; el caso `n≤40` usa polinomio característico exacto).

---

## Qué significa "certificado" aquí

`gap(G) > 0` como enunciado **exacto / de intervalo**, independiente del `f64`
del buscador. Concretamente, la capa produce una **cota inferior demostrada**
`margen ≤ gap(G)` y certifica **si y solo si** `margen > 0`.

Los términos aritméticos son **exactos**:

| término | conjetura | cómo se calcula (exacto) |
|---|---|---|
| `μ` (matching máximo) | CAL-1 | `networkx.max_weight_matching(maxcardinality=True)` → **entero** |
| `Hc = Σ 2/(d_u+d_v)` | CAL-2 | `fractions.Fraction` → **racional exacto** |
| `π = min_v Σ_u d(v,u) / (n−1)` | CAL-3 | distancias enteras (BFS) → **racional exacto** |

El único término no trivialmente exacto es el **eigenvalor** (`λ₁`, `λ₂` o `∂_k`).
Se acota con **rigor demostrable** según el tamaño:

### `n ≤ 40` → método `exacto-charpoly`

1. Polinomio característico de la matriz **entera** (adyacencia 0/1, o distancias
   enteras) vía `sympy.Matrix(...).charpoly` → **coeficientes enteros exactos**.
2. La raíz real objetivo (`λ₁` = mayor raíz; `λ₂` = 2ª mayor; `∂_k` = k-ésima
   mayor) se aísla con `sympy.polys.real_roots` (**aislamiento de Sturm**, exacto).
   Da un intervalo racional aislante `[lo, hi]` que **provablemente** contiene la
   raíz; `.refine()` lo bisecta (biseccion exacta) hasta ancho ~2⁻¹². Si la raíz
   es racional o un surdo cerrado (p. ej. `2·√5`), se conserva su valor exacto.
3. Se prueba `gap > 0` **simbólicamente**: p. ej. CAL-1 evalúa
   `(√(n−1)+1) − (hi_λ₁ + μ)` con `√(n−1)` como **número algebraico** de `sympy`;
   `expr.is_positive` es una **decisión exacta** (no numérica).

El `margen` reportado es exacto: un racional (CAL-2/CAL-3) o una expresión
algebraica como `√17 − 3482/849` (CAL-1).

### `n > 40` → método `mpmath-<dps>dps+residual`

El polinomio característico exacto es inviable (fixture C: `n=203`). Se usa una
**cota rigurosa a posteriori** (matriz simétrica): para un vector unitario `x`,
con `θ = xᵀMx` (cociente de Rayleigh) y `r = ‖Mx − θx‖`,

> existe un eigenvalor verdadero de `M` en el intervalo cerrado `[θ − r, θ + r]`.

`x` proviene de `numpy` (aproximación excelente), pero **`θ` y `r` se computan en
`mpmath` a alta precisión (`mp.dps=80`) a partir de la matriz ENTERA exacta**, así
que el encierro `[θ−r, θ+r]` es un **teorema**. Para fijar que el eigenvalor
encerrado es **exactamente** el k-ésimo (aquí `∂_k`, un eigenvalor **interior**),
se certifican también sus vecinos y se verifica que los intervalos son **disjuntos
y están ordenados** (separación espectral) — así el encierro corresponde
inequívocamente al k-ésimo mayor. El `margen` es una cota `mpf` de `gap`, con la
precisión y el residuo `r` reportados en `detalle`.

> Ejemplo real de por qué esto importa: para `K₅` bajo CAL-3 el `gap` **exacto es
> 0** (`∂_smallest = −1`, `π = 1`), pero `numpy` en `f64` da `∂_smallest =
> −1.0000000000000009` → `gap_f64 = +9e-16 ≈ "+0.000000"`, un **falso positivo**.
> La capa exacta devuelve `margen = 0` y `certificado = False`, y lo rechaza.

---

## Cómo se ejecuta

Dependencias: `networkx`, `numpy`, `scipy`, `sympy`, `mpmath`
(`pip install sympy mpmath` si faltan).

```bash
# Certificar un candidato individual
python certificados/verify.py         --g6 "<graph6>" --conj cal1|cal2|cal3
python certificados/certificar_cli.py --g6 "<graph6>" --conj cal1|cal2|cal3

# Certificar los 3 fixtures publicados (A/B/C) de tests/fixtures/
python certificados/verify.py         --fixtures
python certificados/certificar_cli.py --fixtures

# Salida JSON (pipeline / logging) y ajuste de precisión del caso grande
python certificados/certificar_cli.py --g6 "<graph6>" --conj cal3 --json --dps 100
```

Código de salida **0** ⇔ todo lo pedido queda certificado (`gap>0` demostrado),
**1** en caso contrario. Útil como compuerta:
`python certificados/verify.py --g6 "$G6" --conj cal1 && echo "CONTRAEJEMPLO CONFIRMADO"`.

### API programática

```python
from certificados.verify import certificar
cert = certificar(g6_str, "cal1")   # conj ∈ {"cal1","cal2","cal3"}
# cert = {
#   "certificado": bool,                 # True ⇔ gap>0 DEMOSTRADO
#   "metodo": "exacto-charpoly" | "mpmath-80dps+residual",
#   "margen": str,                       # cota inferior EXACTA de gap (racional/algebraica/mpf)
#   "detalle": {...},                    # λ/μ/Hc/π, intervalos, residuos, separación...
#   "conj": str, "g6": str, "n": int,
# }
```

`certificar` nunca lanza excepción por un `g6` estructuralmente inválido o
desconexo: devuelve `certificado=False` con el motivo en `detalle["error"]`.

---

## Rol en el sistema (compuerta final)

```
buscador (f64)  →  candidato (gap_f64 > umbral)  →  [ ESTA CAPA ]  →  ¿gap>0 demostrado?
                                                        │                    │
                                                        │                    ├─ sí → CONTRAEJEMPLO certificado (margen exacto)
                                                        └────────────────────┴─ no → descartar (falso positivo del f64)
```

Convenciones **idénticas** al oráculo (`parity/refs.py`,
`evaluators/agx_l1_mu.py`, `calibracion/construir_fixtures_b_c.py`): reetiquetado
`0..n−1` en orden `sorted`; `λ₂ = eigvalsh(A)[-2]`; `∂_k = ∂_desc[k−1]` con
`k = ⌊2·D_max/3⌋` y la convención de índice negativo de Python (`k=0` en grafos
completos → `∂_desc[−1]` = el menor). La capa **no** modifica ni depende de los
evaluadores congelados; solo reproduce sus definiciones con aritmética rigurosa.

---

## Resultado sobre los fixtures publicados

| fixture | conj | n | método | margen certificado (cota inferior EXACTA de `gap`) | `certificado` |
|---|---|---|---|---|---|
| A `fixture_l1mu.g6` | CAL-1 | 18 | `exacto-charpoly` | `√17 − 3482/849` ≈ **+0.021810** | **True** |
| B `fixture_c4_estrellas.g6` | CAL-2 | 35 | `exacto-charpoly` | `59223/744940` ≈ **+0.079500** (racional) | **True** |
| C `fixture_c2_203.g6` | CAL-3 | 203 | `mpmath-80dps+residual` | **+0.00028496269896…** (residuo `r≈1.2e-13`, `∂₈` separado de `∂₇,∂₉`) | **True** |

Reproducir: `python certificados/verify.py --fixtures`.

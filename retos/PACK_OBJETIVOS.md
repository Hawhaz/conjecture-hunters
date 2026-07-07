# Pack de objetivos — conjeturas ABIERTAS y testeables (campaña GPU)

Catálogo curado por dos barridos de literatura (fuentes citadas). Patrón buscado:
"invariante(G) ≥/≤ cota(n), igualdad iff grafo específico" — refutable por búsqueda +
verificación exacta. **Honestidad:** estas están abiertas porque son *difíciles*
(muchas verificadas a n pequeño, probablemente ciertas). Una refutación sería
genuinamente nueva pero NO está garantizada. El pre-scan CPU del #1 (Lin) ya dio
vacío — señal de que hace falta la GPU + Gemma explorando grafos raros, no familias.

## Ranking (mejor EV primero)

| # | Conjetura | Enunciado | Extremal | Estado / verificado | Máquina |
|---|-----------|-----------|----------|---------------------|---------|
| 1 | **Lin Problem 4** | ∂₂(D) ≤ n/2 − 2 | K_{n/2,n/2} | ABIERTA (sólo d=2 probado) · **CPU-scan: sin violación** | ∂₂ exacto (ya la tenemos) |
| 2 | **Brouwer** | Σᵢ₌₁ᵏ μᵢ ≤ e + C(k+1,2) ∀k | familia G_{k,r,s} | ABIERTA · verificada sólo a n=11 | Laplaciano μ |
| 3 | **Path-min LE (árboles)** | LE(Pₙ) ≤ LE(T) | camino Pₙ | ABIERTA (cota inf.) · árboles ≤18 | energía Laplaciana |
| 4 | **Pineapple max-LE** | LE ≤ LE(pineapple) | pineapple (clique+pendientes) | ABIERTA · threshold ≤35 | energía Laplaciana |
| 5 | **Bollobás–Nikiforov** | λ₁²+λ₂² ≤ 2(1−1/ω)m | — | ABIERTA (sólo ω=2, perfectos) | λ₁,λ₂ + ω |
| 6 | **EFGW** | min(s₊,s₋) ≥ n−1 | — | ABIERTA · casi-todo grafo probado | eigen² por signo |
| 7 | **Graffiti E≥2(n−α)** | Σ_{λ>0} λ ≥ n−α | — | ABIERTA · verif. ≤n=10 | energía + α |
| 8 | **Gap espectral árboles** | λ₁−λ₂ mín = double comet C(k,ℓ) | double comet (tabla a n=20) | ABIERTA | λ₁,λ₂ |
| 9 | **Energía r-cíclica AGX** | E ≤ E(Pₙ^{p×6;q×6}) | camino con hexágonos | ABIERTA (bi/tetra/tri) | energía adyacencia |
| 10 | **Powers λ₃** | λ₃ ≤ ⌊n/3⌋ | — | ABIERTA (i=4 YA refutada por Linz) | λ₃ |

## Sanity-checks del evaluador (contraejemplos CONOCIDos a re-descubrir)
Validan la tubería antes de cazar de verdad:
- **C₇** rompe la variante ℓ=n₊ de Elphick–Linz–Wocjan.
- **K_{Δ,δ}** rompe Akbari–Hosseinzadeh sin la hipótesis de no-singularidad.
- **P₄³** (no C₄) es el extremal real de energía unicíclica en n=4 (los extremales AGX fallan a n chico).
- Construcción de **Linz** rompe Powers i=4.
- Los 4 contraejemplos AMCS/AGX-2006 (K₅–P₇, etc.) con sus scores.

## Plan de campaña GPU
1. Codificar #1–#6 como evaluadores/carriles (lane #1 Lin ya cargado y validado).
2. Sanity-checks: re-descubrir los contraejemplos conocidos → tubería confiable.
3. MI300X: 20+ carriles en paralelo + Gemma como operador de mutación (explora grafos
   fuera de las familias obvias, donde se escondería un contraejemplo) + LoRA.
4. Certificado exacto en cada hit (backstop anti reward-hacking) + estado abierto.

## Fuentes
Lin arXiv:1805.09661 (DAM 259, 2019) · Brouwer–Haemers *Spectra of Graphs* (2012),
survey arXiv:2305.10290 · Aouchiche–Hansen *Distance spectra: a survey* (LAA 458, 2014) ·
Aouchiche–Caporossi–Hansen EURO J. Comput. Optim. 1 (2013) · Vito–Stefanus AMCS arXiv:2306.07956.

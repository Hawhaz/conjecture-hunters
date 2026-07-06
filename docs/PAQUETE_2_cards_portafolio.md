# PAQUETE 2 — Cards del portafolio de conjeturas
> Curaduría en vivo del 4-jul-2026 (lotes 1–3). Cada card se convierte mecánicamente en un
> evaluador: la desigualdad → función `gap`, los invariantes → funciones en `common/`.
> Status posibles: CALIBRACIÓN · VIVA-CONFIRMADA · CANDIDATA (con acción de confirmación
> para el día 0) · LISTA NEGRA.

---

## 0. Filtros de curaduría (aplicar a TODA candidata nueva antes de darle carril)

1. Enunciado **universal** (para todo n ≥ n₀ chico). Se EXCLUYEN las asintóticas
   ("para n suficientemente grande") — una violación finita no las refuta.
2. Invariantes computables en **tiempo polinomial** (BFS, eigenvalores, matching).
   NP-duros (α, ω, χ, γ) solo con n capado ≤ 80 y solver exacto.
3. Verificada por sus autores solo hasta **n chico** (≤ 15 ideal) → franja de caza abierta.
4. Antes de activar el carril: Scholar → "cited by" del paper fuente → buscar
   proof / counterexample / disproof / settled. Este campo se mueve mensualmente.
5. Preferir 2024–2026: NO atacadas por las tres olas previas
   (Wagner 2021 → NMCS/NRPA 2022 → AMCS 2023).

---

## 1. Módulo de invariantes métricos — contratos y test vectors

Definiciones (todo vía BFS / `scipy.sparse.csgraph`):
`t(v) = Σᵤ d(v,u)` (transmisión); `π = min_v t(v)/(n−1)`; `ρ = max_v t(v)/(n−1)`;
`l̄` = distancia promedio; `ecc` = excentricidad promedio; `r` = radio; `D` = diámetro.

**Property tests regalados** (desigualdades DEMOSTRADAS → sanity checks sobre 1,000
grafos conexos aleatorios; si alguna falla, el bug es nuestro):

```
π ≤ r ≤ ecc ≤ D        π ≤ l̄ ≤ ρ ≤ D        ρ ≤ ecc        r ≤ μ
```

**Test vectors cerrados** (tolerancia 1e−9):

| Grafo | Invariante | Valor exacto |
|---|---|---|
| K_n | π = ρ | 1 |
| P_n | ρ | n/2 |
| P_n, C_n (n impar) | π | (n+1)/4 |
| C_n (n par) | π = ρ | n² / (4(n−1)) |
| K_n | espectro de distancias | {n−1 (×1), −1 (×(n−1))} |
| Turnip T(n,g), g impar | π | (g²−4g+4n−1) / (4(n−1)) |
| Lollipop L(n,g), g par | ρ | n/2 − g(g−2)/(4(n−1)) |

(Fórmulas de turnip/lollipop: survey Aouchiche–Rather, DAM 353 (2024) 94–120.)

---

## 2. CALIBRACIÓN — refutadas con contraejemplo publicado (escalera de dificultad)

### CAL-1 · λ₁ + μ ≥ √(n−1) + 1  · [FÁCIL]
- Fuente: AutoGraphiX 2006 / Aouchiche–Hansen 2010. Grafos conexos, n ≥ 3.
- Refutada: Wagner 2021 (5000 iteraciones); AMCS 2023 (12 iteraciones, 46 s, desde árbol de orden 5).
- Invariantes: λ₁ (adyacencia, `eigvalsh`), μ (matching máximo).
- Fixture A del Paquete 1. **Es el evaluador ya especificado en el Paquete 1.**
- Uso: humo del GA. Debe caer en minutos.

### CAL-2 · λ₂ ≤ Hc(G)  · [FÁCIL-MEDIA]
- Fuente: Favaron–Mahéo–Saclé 1993 (Graffiti II). Todo grafo.
- Hc(G) = Σ_{uv∈E} 2/(d_u + d_v) (índice armónico). λ₂ = segundo eigenvalor de adyacencia.
- Refutada: AMCS 2023. Fixture B: centros de S₁₅ y S₁₉ unidos a un vértice nuevo.
- gap = λ₂ − Hc. Evaluador trivial (grados + un eigenvalor).

### CAL-3 · π + ∂⌊2D/3⌋ > 0, n ≥ 4  · [DURA — benchmark de paridad con el SOTA]
- Fuente: Aouchiche–Hansen 2016 (DAM 213:17–25). ∂ᵢ = i-ésimo eigenvalor de la matriz de distancias.
- Refutada: AMCS 2023 (16.5 min; único algoritmo que lo logró — NMCS, NRPA y deep-RL fallaron).
- Fixture C: centro de S₁₉₁ unido a un extremo de P₇ y a un extremo de P₅ (n=203, score ≈ 0.00028).
- gap = −π − ∂⌊2D/3⌋. Si nuestro sistema re-encuentra esta familia, estamos AL nivel de AMCS;
  todo lo del Paquete 3 en adelante es para superarlo.

(CAL-4 opcional: Collins 1989, picos de coeficientes de CP_A vs CP_D en árboles — refutada
por AMCS; evaluador más exótico, solo si sobra tiempo.)

---

## 3. VIVAS CONFIRMADAS (al 4-jul-2026)

### V-01 · Colisión de radio espectral de distancia en árboles (Stevanović–Indulal)
- **Enunciado**: no existen dos árboles T₁ ≠ T₂, no coespectrales en distancia, con
  ∂₁(T₁) = ∂₁(T₂). (Conjecture 2.29 del survey de espectros de distancia, GERAD/LAA 458:301–386.)
- **Refutación** = un PAR de árboles con ∂₁ exactamente igual y espectros de distancia distintos.
- **Verificado hasta**: árboles ≤ 22 vértices; árboles químicos (Δ≤4) ≤ 24.
  → **Franja de caza: n ∈ [23, 60].**
- **Búsqueda**: co-evolucionar pares (T₁, T₂) del mismo orden. Espacio: solo árboles
  (movimientos NMCS-trees: agregar hoja / subdividir). 
- **Fitness**: −|∂₁(T₁) − ∂₁(T₂)|, con score −∞ si CP_D(T₁) = CP_D(T₂) (coespectrales).
  OJO: aquí no hay "cruce de cero" — el objetivo es colisión exacta; la evolución produce
  candidatos con |Δ∂₁| ~ 1e−12 y la aritmética exacta decide.
- **Certificado exacto**: matrices de distancia enteras → CP_D sobre ℤ (sympy/flint);
  CP distintos (no coespectrales) + gcd(CP₁, CP₂) sobre ℚ no trivial + aislamiento de la
  raíz máxima (Sturm / intervalos) mostrando que la raíz máxima de ambos es LA MISMA raíz
  del gcd.
- **Status**: abierta hasta donde alcanzó la curaduría de hoy.
  CONFIRMAR día 0: Scholar "Stevanović Indulal distance spectral radius trees".

---

## 4. CANDIDATAS FUERTES — confirmar estado el día 0 (acción exacta incluida)

### C-01 · Hermanas restantes de Aouchiche–Hansen 2016 (π, ρ vs ∂ᵢ)
- El paper formuló VARIAS conjeturas AGX. Estado conocido hoy:
  π+∂₃>0 y ρ+∂₃>0 (D≥3) PROBADAS (2021); π+∂⌊2D/3⌋ REFUTADA (AMCS 2023).
- Acción: leer AH-2016 (open archive en ScienceDirect), extraer las restantes;
  por cada una, "cited by" + proof/counterexample. Las sobrevivientes → cards.
- Franja n: 20–300. La familia muere en cometas-estrella (ver seeds del Paquete 1 §9).

### C-02 · Liu–Li–Pan 2021 (MATCH 85:349–366, índices Zagreb modificados en árboles)
- AMCS mató 2 conjeturas de ese paper; papers así traen más adentro.
- Acción: conseguir el paper, listar conjeturas restantes, checar citas.
- Evaluadores triviales (sumas sobre grados). Espacio: árboles.

### C-03 · Veta digrafos/torneos (escuela Dankelmann–Mafunda–Mallu + Ai–Gerke–Gutin, 2021–2025)
- Papers frescos: arXiv 2405.15058 (remoteness con tamaño y conectividad),
  2510.08841 (digrafos, oct-2025), tesis Mallu 2022. Cotas "sharp salvo constante
  aditiva" → conjeturas de constante exacta y open problems al final de cada paper.
- **Ventaja estructural: NADIE ha corrido máquina sobre digrafos en esta familia.**
  Generalización trivial del sistema: matriz de distancias dirigida, chequeo de
  conexidad fuerte (Tarjan), mismos movimientos + orientación de aristas.
- Acción: extraer los open problems de los 3–4 papers más recientes de la escuela.

### C-04 · π, ρ en outerplanar/planar con caras acotadas (Czabarka et al.; arXiv 2508.10077, ago-2025)
- Fresquísimo. Evaluador con check de planaridad/outerplanaridad (networkx, polinomial).
- Acción: extraer conjeturas/sharpness abiertas del paper y sus citas.

### C-05 · Barrido arXiv 2024–2026 (math.CO + math.SP)
- Queries listas: "conjecture" × {distance Laplacian, distance signless Laplacian,
  Aα spectral radius, Sombor spectral radius, transmission regular}.
- Colar con los filtros del §0. Meta: llenar el portafolio hasta ~20 carriles.

---

## 5. LISTA NEGRA — no gastar carriles aquí

| Conjetura | Motivo |
|---|---|
| Brouwer: S_k ≤ m + C(k+1,2) | PROBADA (Kothari–Tudose, arXiv jun-2026, vía equivalencia con Grone–Merris–Bai; preprint sin peer review, pero el EV de cazarla murió) |
| λ₁·π ≤ n−1 · a(G)·π ≥ f(n) · λ₁−α ≥ √(n−1)−n+1 · R+α ≤ n−1+√(n−1) | REFUTADAS (AMCS 2023; las dos últimas con familias infinitas) |
| mM₂(T) ≤ (n+1)/4 y su hermana con γ (Liu et al. 2021) | REFUTADAS (AMCS 2023, familias infinitas T₁(k), T₂(k)) |
| m(∂L₁) ≤ n−2 | PROBADA |
| π+∂₃>0 · ρ+∂₃>0 (D≥3) | PROBADAS (2021) |
| ecc−π · l̄−π · ecc−ρ · ρ−l̄ · ρ−r (ambas direcciones) · ρ/g · π/l̄ | PROBADAS (Ma–Wu–Zhang, Sedlar, Wu–Zhang, Hua–Chen–Das, Hua–Das; ver survey 2024 §3) |
| Cualquier espectral-Turán con "n suficientemente grande" | Asintótica: fuera de forma refutable |

---

## 6. Plantilla de card (para las que se agreguen el día 0)

```
### X-NN · <nombre corto>
- Enunciado exacto (desigualdad computable, cuantificador, clase de grafos, n₀)
- Invariantes y cómo se computan (función de common/ o nueva)
- Verificada por autores hasta n = ___  →  franja de caza
- Familias extremales conocidas/sospechadas (→ seeds y primer)
- Fitness propuesto (gap + desempates si hay mesetas)
- Certificado exacto (qué corre verify.py)
- Fuente (paper, año, sección) + status + fecha de última verificación de status
```

---

## 7. Estado del portafolio y ruta a 20 carriles

**Hoy (suficiente para programar TODO el sistema):** 3 calibración + 1 viva + 5 vetas
con receta. Los evaluadores de CAL-1/2/3 + V-01 + el módulo métrico del §1 cubren ya
todos los TIPOS de invariante que las 20 finales van a necesitar: espectral-adyacencia,
espectral-distancia, métrico-BFS, topológico-de-grados y matching. Programar contra
estas cards generaliza a las que faltan sin tocar arquitectura.

**Día 0 (6-jul, con créditos activos):** ejecutar las acciones de C-01…C-05 conmigo
(3–4 horas de curaduría en vivo) → llenar hasta ~20 cards con la plantilla del §6.

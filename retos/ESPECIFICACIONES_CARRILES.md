# Especificaciones de carriles — plano de encoding (research verbatim, con fuentes)

Investigado por dos agentes contra fuentes primarias. Cada carril: enunciado exacto,
contraejemplo conocido (validación) o extremal reclamado (abierta), y **flags de
honestidad**. `gap>0 ⇔ contraejemplo`. Objetivo: **20 carriles** (7 validación + 13 abiertas).

## YA ENCODEADOS (`pack_conjeturas.py`, 9 carriles, gate verde)
jia_song (val·F₂) · elphick_np (val·C₇) · lin_p4 · bollobas · efgw · graffiti · powers λ₃ · brouwer · le_tree.

## NUEVOS — VALIDACIÓN (contraejemplo conocido, el motor DEBE re-descubrirlo)

### V3 · λ₁·π ≤ n−1  (AutoGraphiX Conj.7, Aouchiche 2006)
π = proximidad = mínima transmisión/(n−1). **CE: K₅ + P₇** (un vértice de K₅ unido a un
extremo de P₇), n=12, `g6=K~}?GC@?G?_@`. gap = λ₁·π − (n−1) = **+0.05923**.
Fuente: Vito–Stefanus AMCS arXiv:2306.07956 (Fig.5). ✅ exacto.

### V4 · λ₁ − α ≥ √(n−1) − n + 1  (AGX Conj.9)
gap = (√(n−1)−n+1) − (λ₁−α). **CE: doble-estrella asimétrica (7 y 8 hojas + centro)**, n=18,
`g6=QqPAA@?O@?C?G?G?C?@??G??_??`. gap **+0.02181**. ⚠️ g6 RECONSTRUIDO por el agente
(score calza a 5 decimales; el paper solo da imagen). Verificar al encodear.

### V5 · R + α ≤ n−1 + √(n−1)  (AGX Conj.10, R=Randić)
R = Σ_{uv∈E} 1/√(d_u d_v). gap = (R+α) − (n−1+√(n−1)). **CE: T(2,5)** = doble-estrella
balanceada, dos centros con 4 hojas c/u + conector, n=11, `g6=JqPA@?_G@??`. gap **+0.04789**. ✅

### V6 · λ₁ + μ ≥ √(n−1) + 1  (CAL-1 / AGX; μ=número de emparejamiento)
gap = (√(n−1)+1) − (λ₁+μ). **CE: Wagner T(2,8)** doble-estrella balanceada (dos centros con
8 hojas + conector), n=19, `g6=RkaCCA?_C?C?G?G?C?@??G??_?@???`, λ₁=√10, μ=2. gap **+0.08036**.
Cierto para n≤18. Fuente: Wagner arXiv:2104.14516. ✅

### V7 · E(G) ≤ 2n−2  (Gutman; energía = Σ|λ_i(A)|)
gap = E(G) − (2n−2). **CE: L(K₅)** = grafo línea de K₅ (triangular T(5)), n=10, 4-regular,
E=20 > 18. gap **+2.0**. (Ningún hiperenergético con n≤7.) ✅ `nx.line_graph(nx.complete_graph(5))`.

## NUEVOS — ABIERTAS (caza real; deben sostenerse en el corpus)

### O8 · Lin Problem 2 · S_k(D(G)) ≤ S_k(D(P_n))  (camino maximiza)
S_k = suma de los k mayores autovalores de la matriz de DISTANCIAS. Extremal P_n. Abierta
(arXiv:1805.09661). ⚠️ "n suficientemente grande" — probar en corpus; si hay excepciones a n
chico, restringir dominio a n≥umbral. Encodear k=2.

### O9 · Lin Problem 3 · S_k(D(G)) ≥ 2n−2k  (bipartito)
Sólo G bipartito conexo. Igualdad iff K_{r,n−r}. Abierta (mismo paper). ⚠️ "n grande" — restringir.

### O10 · Energía de distancia · E_D(G) ≥ 4(n−1−m/n)
E_D = Σ|∂_i|. Abierta (Caporossi–Chasset–Furtula, GERAD G-2009-64). ⚠️ NO afirmar extremal
(el primario no se abrió; NO confundir con la fórmula PROBADA 4(n−γ) de multipartitos).

### O11 · Pineapple · LE(G) ≤ LE(pineapple)
LE = energía Laplaciana = Σ|μ_i − 2m/n|. Pineapple = clique de tamaño **1+⌊2n/3⌋** + resto
como pendientes en UN vértice del clique (ya está `pineapple()` en el pack). Abierta; probada
sólo threshold. Fuente: Vinagre–Del-Vecchio–Justo–Trevisan / lista Stevanović.

### O12 · Gap espectral en árboles · λ₁−λ₂ minimizado por double comet
Minimizante tabulado (verif. n≤20): P_n (n≤8) · C(2,n−4) (9≤n≤11) · C(3,n−6) (12≤n≤15) ·
C(4,n−8) (16≤n≤20). **C(k,ℓ) = camino P_ℓ con k pendientes en CADA extremo, n=ℓ+2k.**
gap = (λ₁−λ₂)(minimizante_tabla(n)) − (λ₁−λ₂)(T) ; >0 = árbol que le gana al mínimo = CE.
Sólo árboles. Abierta (Jovović–Koledin–Stanić, Ars Math. Contemp. 14 (2018)).

### O13 · Elphick–Linz–Wocjan (forma CORRECTA) · Σ_{i≤min(n₊,ω)} λ_i² ≤ 2(1−1/ω)m
n₊ = # autovalores positivos. Abierta (Conj.4 survey arXiv:2305.10290). Distinta del carril
elphick_np (forma ℓ=n₊, FALSA con C₇, que es validación).

## NO ENCODEAR (flags de honestidad — evitar basura)
- **WOW-284** (δ* ≤ −∂_n, Petersen): el agente detectó que Petersen da δ*=3 > −∂_n=2 → la
  dirección/definición transcrita está MAL. NO encodear sin reconciliar la fuente primaria.
- **Powers i=4** (λ₄ ≤ ⌊n/4⌋): contraejemplo real es n=60 (blow-up del icosaedro) → muy grande
  para carril de validación chico. Mantener powers λ₃ (i=3, abierta) que ya está.
- **AGX Conj.8** (a(G)·π ≥ umbral): el paper sólo da imagen del CE, sin construcción → no pinneable.

## Fuentes
Vito–Stefanus AMCS arXiv:2306.07956 · Wagner arXiv:2104.14516 · Lin arXiv:1805.09661 ·
Li–Sun–Wei *Unsolved Problems in Spectral Graph Theory* arXiv:2305.10290 · Linz arXiv:2304.12324 ·
Caporossi–Chasset–Furtula GERAD G-2009-64 · Jovović–Koledin–Stanić Ars Math. Contemp. 14 (2018).

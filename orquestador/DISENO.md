# DISENO.md — Orquestador evolutivo caza-contraejemplos

Racional de diseno del orquestador de `orquestador/`, con cada componente
mapeado al hallazgo de investigacion que lo motiva (FunSearch, AlphaEvolve,
ShinkaEvolve, MAP-Elites, Thompson Sampling, trees-only/AMCS, certificado
exacto). El objetivo declarado es **igualar o superar a FunSearch/AlphaEvolve en
ESTA clase de problema** (refutar conjeturas espectrales de teoria de grafos en
la banda n=10..40, y escalar el patron al benchmark duro n=203 de CAL-3).

El invariante que gobierna todo el sistema: **el `gap` continuo ORDENA la
busqueda, pero solo el CERTIFICADO EXACTO DECLARA un contraejemplo.**

---

## Decision 1 — Cascada de evaluacion de 3 niveles (AlphaEvolve)

**Hallazgo (AlphaEvolve):** las corridas evolutivas se aceleran drasticamente si
la evaluacion es una CASCADA: filtros baratos primero, el juez caro solo sobre
los pocos supervivientes. AlphaEvolve documenta ademas que el evaluador debe ser
robusto a *reward-hacking*: si el objetivo es "gameable", la evolucion explota el
bug del evaluador en vez de resolver el problema.

**Implementacion:**
- **T1 — validez barata** (`grafos.valido`): grafo simple, conexo, `n` en banda
  [10,40]. Sin tocar el gap. Descarta basura estructural antes de gastar CPU.
- **T2 — gap rapido en LOTE** (`evaluar.Evaluador`): el binario Rust
  `buscador_rs evaluar --eval calX` evalua el lote COMPLETO en paralelo
  (~10k evals/s), emite `g6,n,gap,contraejemplo`. gap>0 ⇔ candidato. En
  plataformas sin el `.exe` (p. ej. CI Linux) cae al oraculo Python
  `parity/refs.py`, que da el MISMO gap por contrato de paridad (los 86 pytest
  garantizan `gap_rust == gap_python` a 1e-9).
- **T3 — certificado EXACTO** (`certificar.certificar` → `certificados/verify`):
  aritmetica exacta (charpoly sympy hasta n=40; mpmath + cota residual de Weyl
  arriba). Se corre **solo** sobre candidatos con `gap > 1e-9`. Es el veredicto
  **in-gameable**: el f64 del buscador dice "candidato"; T3 lo convierte en
  teorema o lo rechaza.

**Defensa anti reward-hacking (documentada):** un contraejemplo se declara
"encontrado" **unicamente** cuando T3 devuelve `certificado=True`. El sistema
jamas confia en el gap rapido para la afirmacion final — el ruido de `eigvalsh`
(~1e-15) o un evaluador manipulado podrian mentir; el certificado exacto no.
Ver `orquestar._corrida_conjetura` (bloque `cert_al_vuelo`).

---

## Decision 2 — Objetivo = +gap continuo (margen de violacion)

**Hallazgo (FunSearch/AlphaEvolve):** un objetivo BINARIO ("¿es contraejemplo?")
no da gradiente; la evolucion se estanca en mesetas. Un objetivo CONTINUO (cuan
cerca esta de violarse la desigualdad) guia la busqueda cuesta arriba.

**Implementacion:** el fitness es el `gap` real y con signo
(`gap = cota − (invariantes)` para CAL-1, `λ₂ − Hc` para CAL-2,
`−(π + ∂_k)` para CAL-3). Nunca se binariza. Ordena elites, best global y
recompensa del bandit. Ver `archivo.Elite.clave_orden`.

---

## Decision 3 — Islas + archivo MAP-Elites (FunSearch + AlphaEvolve + MAP-Elites)

**Hallazgo:** FunSearch mantiene **islas** (poblaciones semi-aisladas) para
preservar diversidad y evitar convergencia prematura; MAP-Elites mantiene un
**archivo por nicho** (una rejilla de descriptores) donde cada celda guarda el
mejor individuo de ese nicho — asi la busqueda ilumina el espacio en vez de
colapsar a un optimo. AlphaEvolve combina ambos y **reinicia** islas estancadas.

**Implementacion (`archivo.py`):**
- Cada **isla** es un archivo MAP-Elites: `celda → elite`, con
  `celda = (n_bin, density_bin)`, `density = m / C(n,2)`, y elite = grafo de
  **mayor gap** en esa celda.
- **`--islas` islas** (def 5); hard-reset de la **peor mitad** cada `R`
  generaciones, resembrando cada isla reiniciada desde el best de una isla
  **superviviente** (`Archipielago.reset_peor_mitad`).
- **Descriptores ELEGIDOS a proposito:** `n` y `densidad` — **ortogonales al
  fitness**. Se EXCLUYEN el numero de emparejamiento (μ) y los eigenvalores
  porque **correlacionan con el gap**: usarlos como ejes del archivo colapsaria
  la diversidad justo sobre la dimension que se quiere explorar (anti-patron
  clasico de MAP-Elites). Ver `grafos.celda`.

---

## Decision 4 — Bandit Discounted Thompson Sampling (Beta-Bernoulli, γ=0.99)

**Hallazgo:** elegir que operador aplicar es un problema de bandit no
estacionario (que operador ayuda cambia a lo largo de la corrida, y de golpe
tras un reset de islas). Thompson Sampling equilibra exploracion/explotacion de
forma casi optima; el **descuento** γ olvida evidencia vieja para adaptarse al
no-estacionario.

**Implementacion (`bandit.py`):** arms = **(conjetura × operador)**. Cada paso:
(1) descuenta `S_i,F_i ← γ·S_i, γ·F_i`; (2) muestrea `θ_i ~ Beta(S_i+1,F_i+1)`;
(3) tira `argmax θ_i`; (4) **recompensa 1** si la mutacion **avanzo la frontera
de la isla** (celda nueva o mayor gap → eventos `nueva_celda`/`mejora_celda` de
`Isla.insertar`), **0** si no. El muestreo Beta usa `gammavariate` de la stdlib
para ser 100% reproducible con la misma semilla en cualquier plataforma.

---

## Decision 5 — Operadores estructurales + modo `--trees-only`

**Hallazgo (AMCS / trees-only):** en esta familia de conjeturas, los
contraejemplos extremales son casi arboles (estrellas con colas). Restringir la
busqueda a **operadores que preservan la estructura de arbol** es la palanca de
mayor apalancamiento: es lo que dejo a **AMCS crackear el benchmark n=203** que
ningun otro metodo re-encontro.

**Implementacion (`grafos.py`):** operadores `add_leaf`, `subdivide_edge`,
`prune_leaf`, `prune_subdivision` (todos preservan conectividad), `add_edge`
(**solo** en modo conexo), y `LLM-delta` (via `mutador`). `--trees-only`
restringe a los cuatro operadores de arbol. Es un flag de primera clase de la
CLI precisamente por su impacto.

---

## Decision 6 — Muestreo de padres por novedad + rechazo de duplicados (ShinkaEvolve)

**Hallazgo (ShinkaEvolve):** (a) muestrear padres proporcional a su calidad Y a
su **sub-explotacion** acelera; (b) **rechazar candidatos estructuralmente
duplicados** ahorra evaluaciones desperdiciadas (el cuello de botella real).

**Implementacion:**
- **Peso de padre** (`orquestar.muestrear_padre`):
  `w_i = sigmoid(λ·(gap_i − mediana_gap)) · 1/(1 + n_offspring_i)`. El primer
  factor favorece elites de gap alto; el segundo penaliza a los ya muy usados
  como padres (`Elite.n_offspring`), forzando exploracion.
- **Rechazo por novedad** (`archivo.Isla.insertar`): antes de insertar se calcula
  el **hash Weisfeiler-Lehman** (`grafos.wl_hash` →
  `networkx.weisfeiler_lehman_graph_hash`); si ya existe en la isla, el candidato
  se rechaza (evento `duplicado`) y no consume una celda. Dos grafos isomorfos
  comparten hash.

---

## Decision 7 — Capa de mutacion: dos backends tras una interfaz

**Hallazgo (AlphaEvolve/FunSearch + realidad de un modelo 4B):** el motor debe
correr sin red (para CI reproducible) y, opcionalmente, con un LLM que proponga
saltos estructurales mas creativos. Pero un modelo pequeno (gemma3:4b) **no
razona sobre floats**: el fitness debe llegarle como **rango ordinal**, y los
grafos como **listas de aristas** (no g6, que es opaco para el LLM).

**Implementacion (`mutador.py`):**
- **`mock`** (DETERMINISTA, ruta de CI, sin red): aplica el operador elegido por
  el bandit a un elite muestreado. rng sembrado → reproducible.
- **`ollama`** (opt-in): llama a gemma3:4b (`POST {api_base}/chat/completions`,
  mismo transporte urllib que `prompts/ollama_cliente.py`). Prompt = few-shot
  **ranqueado** de k=3 elites como **listas de aristas**, ordenados **peor→mejor**,
  fitness como **RANGO ORDINAL** (no floats). Pide un **delta de aristas**
  (`add edge (u,v); remove edge (x,y)`), que se aplica DETERMINISTAMENTE en codigo
  (`grafos.aplicar_delta`), **best-of-N=4**, validando que cada intento decodifique
  a un grafo conexo legal. Si Ollama es inalcanzable, **cae a `mock`** (nunca
  crashea). Cambiar a vLLM/Fireworks es solo cambiar `api_base`.

---

## Decision 8 — Semillas por conjetura

**Hallazgo (§9 del proyecto / literatura extremal):** estas conjeturas mueren en
familias concretas (estrellas, caminos, cometas de doble cola, kites,
dos-estrellas, peines). Sembrar la busqueda ahi ahorra generaciones de calentar.

**Implementacion (`grafos.familias_semilla`, `grafos.semillas`):** constructores
replicados de `calibracion/ga_graphs.py`. Para **CAL-3** se antepone la semilla
**esqueleto-cola P13** (`_tail_skeleton_p13`): estrella central con dos colas
largas → **diametro alto**, el regimen donde vive el margen de CAL-3 y donde
esta el contraejemplo publicado n=203 (centro de S₁₉₁ + P₇ + P₅).

---

## Decision 9 — Shaping de meseta por flooring de CAL-3 (SOLO desempate)

**Hallazgo:** el gap de CAL-3 es `−(π + ∂_{⌊2D/3⌋})`. El **flooring**
`k=⌊2D/3⌋` es una funcion escalonada del diametro `D`: entre dos cruces de
multiplo de 3, `k` NO cambia y el gradiente del gap respecto a `D` se **aplana**
(meseta). Eso ciega a la busqueda sobre cuando conviene alargar el diametro.

**Implementacion (`orquestar.shaping_cal3`):** un termino secundario **infimo**
(escala 1e-6) que premia a `2D` acercandose a un multiplo de 3 (donde `k`
saltara). Entra **solo** como criterio de **desempate** entre elites de igual gap
real (`Elite.clave_orden` = `(gap, shaping)`), y **jamas** reemplaza el gap real
ni la clasificacion de contraejemplo (esa la decide T3). Es un tie-break, no un
objetivo.

---

## Decision 10 — Bucle + logging compatible con el dashboard

**Implementacion (`orquestar.orquestar`):** el bucle principal encadena todo lo
anterior y registra, por generacion y por conjetura, el mejor gap a un CSV con
cabecera **identica** a `calibracion/ga_graphs.py`:
`corrida,gen,best_gap,best_g6,n,evento,epoch`. Asi el dashboard existente lo
lee sin cambios. Cuando un candidato se CERTIFICA, el evento pasa a
`contraejemplo` y se imprime/loguea de forma prominente con el **margen del
certificado** (cota inferior EXACTA del gap).

---

## Por que esto iguala/supera a FunSearch/AlphaEvolve en esta clase

1. **El juez es exacto, no aprendido.** FunSearch/AlphaEvolve dependen de un
   evaluador que puede ser gameado; aqui T3 es un **teorema** (charpoly/mpmath).
   Un "contraejemplo" nuestro es matematicamente incontrovertible.
2. **T2 en Rust paralelo** da ordenes de magnitud mas evaluaciones/segundo que
   un evaluador Python, con **paridad demostrada** (86 pytest oraculo) — mas
   iteraciones evolutivas por unidad de CPU.
3. **`--trees-only` + semillas extremales** inyectan el conocimiento de dominio
   (lo que hizo a AMCS unico en el n=203) directamente en el operador y la
   poblacion inicial.
4. **Diversidad estructurada** (islas + MAP-Elites con descriptores ortogonales
   al fitness + rechazo WL) evita el colapso que sufren los buscadores ingenuos
   en paisajes de meseta como CAL-3.

## Referencias de codigo (mapa rapido)

| Componente | Archivo | Decision |
|---|---|---|
| Codec g6, descriptores, WL, operadores, semillas | `grafos.py` | 3,5,6,8 |
| Cascada T1/T2 (Rust + fallback Python) | `evaluar.py` | 1,2 |
| Compuerta T3 (certificado exacto) | `certificar.py` | 1 |
| Islas + MAP-Elites + reset | `archivo.py` | 3,6 |
| Thompson descontado | `bandit.py` | 4 |
| Mutacion mock/ollama | `mutador.py` | 7 |
| Bucle, novelty-parent, shaping CAL-3, CSV | `orquestar.py` | 6,9,10 |

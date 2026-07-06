# PAQUETE 1 — Vertical de calibración: spec + vectores de prueba

> **Handoff para Claude Code.** Contrato TDD: los tests de este documento SON la especificación.
> Implementar hasta que `pytest` esté 100% verde. Prohibido modificar los tests para que pasen;
> se modifica la implementación. Prohibido modificar `evaluators/` desde código evolucionado.

---

## 0. Contexto en cinco líneas

Sistema evolutivo caza-contraejemplos para conjeturas de teoría espectral de grafos.
Un LLM actúa como operador de mutación vía API OpenAI-compatible (hoy: mock determinista
y/o Ollama local; en el evento: Fireworks / vLLM en MI300X — solo cambia `api_base`).
Este paquete construye ÚNICAMENTE la vertical de calibración: una conjetura **ya refutada**
(ground truth publicada) de punta a punta. Si el sistema no re-descubre ese resultado, no caza.

---

## 1. Estructura del repo

```
conjeturas/
├── common/
│   └── invariantes.py        # λ₁, μ, validación de grafos (doble implementación: fast + ref)
├── evaluators/
│   └── agx_l1_mu.py          # evaluador de la conjetura de calibración (CONGELADO tras verde)
├── calibracion/
│   └── ga_graphs.py          # GA directo sobre grafos (sin LLM) para validar la BÚSQUEDA
├── mock_llm/
│   └── server.py             # FastAPI OpenAI-compatible, respuestas deterministas de fixture
├── tests/
│   ├── test_invariantes.py   # Nivel 0
│   ├── test_evaluator_oracle.py  # Nivel 1 (atlas exhaustivo + property tests)
│   ├── test_fixture_wagner.py    # Nivel 1.5 (skip hasta tener el .g6)
│   ├── test_sandbox.py       # Nivel 2 (programas adversariales)
│   ├── test_loop_mock.py     # Nivel 3 (loop completo contra el mock)
│   └── fixtures/
│       ├── wagner19.g6       # TODO HUMANO — ver §6
│       ├── diffs.jsonl       # parches enlatados para el mock
│       └── adversarial/      # a_basura.py ... h_ids_fuera_rango.py
├── configs/
│   └── calibracion.yaml      # config de OpenEvolve para la vertical
└── requirements.txt          # numpy, scipy, networkx, fastapi, uvicorn, pytest, hypothesis
```

---

## 2. La conjetura de calibración

Enunciado (familia AutoGraphiX / Aouchiche–Hansen): para todo grafo simple **conexo** con n ≥ 3,

```
λ₁(G) + μ(G) ≥ √(n−1) + 1
```

- `λ₁`: mayor eigenvalor de la **matriz de adyacencia**.
- `μ`: número de emparejamiento (maximum matching, cardinalidad).
- **Estado: REFUTADA** por A. Z. Wagner (2021, "Constructions in combinatorics via neural
  networks"), contraejemplo con ~19 vértices. Por eso sirve de calibrador.

Definiciones del sistema:

```
gap(G)   = (sqrt(n-1) + 1) - (lam1(G) + mu(G))
gap > 0  ⇔ contraejemplo
fitness  = gap   (se maximiza)
```

---

## 3. Contrato de invariantes — `common/invariantes.py`

| Función | Implementación | Uso |
|---|---|---|
| `lam1_fast(A)` | `numpy.linalg.eigvalsh` sobre matriz densa float64 → último valor | hot path |
| `lam1_ref(G)`  | vía networkx `adjacency_spectrum` (tomar máx. parte real) | SOLO tests |
| `mu_fast(G)`   | `networkx.max_weight_matching(G, maxcardinality=True)` → `len(...)` | hot path |
| `mu_brute(G)`  | recursión exacta sobre aristas (solo n ≤ 12) | SOLO tests |
| `validar(texto_aristas)` | parsea stdout → A o error estructurado | evaluador |

⚠️ **Trampa conocida:** `networkx.maximal_matching` es GREEDY (maximal ≠ maximum).
Usarlo aquí produce basura silenciosa. Solo `max_weight_matching(..., maxcardinality=True)`.

Reglas de `validar`: grafo simple (sin lazos ni multiaristas), conexo (BFS), 3 ≤ n ≤ 300,
vértices etiquetados 0..n−1 sin huecos; cualquier violación → rechazo estructurado, nunca excepción.

---

## 4. Nivel 0 — vectores de prueba contra formas cerradas

Tolerancia `1e-9` salvo indicación. `cota(n) = sqrt(n-1) + 1`.

| Grafo | n | λ₁ exacto | μ | gap esperado |
|---|---|---|---|---|
| K₃ | 3 | 2 | 1 | √2+1−3 ≈ **−0.58578644** |
| K₁₀ | 10 | 9 | 5 | 4−14 = **−10** |
| Estrella K₁,₄ | 5 | 2 | 1 | 3−3 = **0 (IGUALDAD exacta)** |
| Estrella K₁,₉ | 10 | 3 | 1 | 4−4 = **0 (IGUALDAD exacta)** |
| P₄ (camino) | 4 | 2cos(π/5) = (1+√5)/2 | 2 | √3+1−(φ+2) ≈ **−0.88602540** |
| C₅ (ciclo) | 5 | 2 | 2 | 3−4 = **−1** |
| C₆ | 6 | 2 | 3 | √5+1−5 ≈ **−1.76393202** |
| K₂,₃ | 5 | √6 | 2 | 3−(√6+2) ≈ **−1.44948975** |
| K₃,₃ | 6 | 3 | 3 | √5+1−6 ≈ **−2.76393202** |
| Petersen | 10 | 3 | 5 | 4−8 = **−4** |

Los dos casos de **igualdad exacta** (estrellas) son los detectores de errores de signo y de
cota: cualquier fórmula volteada los rompe de inmediato.

Property tests (hypothesis o loop, 1,000 grafos `G(n,p)` conexos, n ∈ [3, 60]):

1. `lam1_fast == lam1_ref` (atol 1e-8).
2. Invarianza bajo permutación aleatoria de vértices: λ₁, μ y gap idénticos.
3. `mu_fast == mu_brute` para todos los casos con n ≤ 12.
4. `gap(estrella_n) == 0` para todo n ∈ [3, 120].

---

## 5. Nivel 1 — oráculo exhaustivo

- `networkx.graph_atlas_g()` → todos los grafos con n ≤ 7; filtrar conexos con n ≥ 3.
- `assert gap(G) <= 1e-9` para todos.
- Si alguno "viola": con probabilidad ~1 es bug de fórmula. Detener y auditar contra §4.

---

## 6. Nivel 1.5 — fixtures de contraejemplos publicados (los tests que validan medio proyecto)

Tres peldaños de dificultad creciente. B y C tienen construcción EXPLÍCITA (3 líneas de
Python cada uno, tomadas de Vito–Stefanus 2023, arXiv 2306.07956). NO inventar grafos.

- **Fixture A — `fixture_l1mu.g6`** (evaluador de ESTE paquete, λ₁+μ):
  extraer del repo de Wagner (cross-entropy-for-combinatorics) o del repo de AMCS
  (github.com/valentinovito/Adaptive_MC_Search). Test: `gap > 0`.
- **Fixture B — `fixture_c4_estrellas.g6`** (para evaluador λ₂ ≤ índice armónico, Paquete 2):
  unir los centros de las estrellas S₁₅ y S₁₉ a un vértice nuevo.
- **Fixture C — `fixture_c2_203.g6`** (para evaluador π + ∂⌊2D/3⌋, Paquete 2):
  unir el centro de una estrella S₁₉₁ a un extremo de un P₇ y a un extremo de un P₅
  (n = 203, score ≈ 0.00028). Benchmark DURO: solo AMCS logró re-encontrarlo;
  NMCS, NRPA y deep-RL fallaron.
- Tests con `pytest.mark.skipif` si falta el archivo: cargar → `evaluate` → `assert gap > 0`.
- Estos tests confirman los evaluadores contra la realidad publicada **sin ejecutar búsqueda alguna**.

---

## 7. Nivel 2 — sandbox y programas adversariales

Contrato de `evaluate(program_path) -> dict`:

- Ejecuta `python program.py` en subprocess: **timeout 30 s**, RAM capada ~2 GB (`setrlimit`),
  stdout truncado a 1 MB, cwd temporal, sin red.
- **AST check ANTES de ejecutar.** Imports permitidos: `math, random, itertools, heapq,
  collections, numpy`. Prohibidos: `os, sys, subprocess, socket, shutil, pathlib`,
  `open`, `eval`, `exec`, `__import__`.
- stdout esperado: una arista `"u v"` por línea (enteros, 0-indexed). Parse estricto.
- Rechazo → `{"combined_score": -1e9, "error": "<motivo>"}`. El orquestador **sigue vivo**.

Adversariales en `tests/fixtures/adversarial/` (cada uno debe dar score `-1e9`,
`error` no vacío, y cero excepciones no controladas):

| Archivo | Ataque |
|---|---|
| `a_basura.py` | imprime texto arbitrario no parseable |
| `b_timeout.py` | `while True: pass` |
| `c_desconexo.py` | grafo válido pero con 2 componentes |
| `d_import_os.py` | intenta `import os` y escribir archivo |
| `e_flood.py` | imprime 10⁷ líneas |
| `f_vacio.py` | termina limpio con stdout vacío |
| `g_lazo_multi.py` | imprime `"3 3"` y una arista duplicada |
| `h_ids_fuera.py` | imprime vértices negativos y con huecos |

---

## 8. Nivel 3 — mock LLM + loop completo

- `mock_llm/server.py`: FastAPI con `POST /v1/chat/completions`. Responde en round-robin
  desde `fixtures/diffs.jsonl` (parches en el formato diff/SEARCH-REPLACE que OpenEvolve
  espera — consultar su README). 100% determinista: misma secuencia en cada corrida.
- Smoke test del loop: OpenEvolve, 30 iteraciones, contra el mock, sobre el TOY.
  Asserts: el archivo de programas crece; `best_score` es no-decreciente;
  checkpoint + resume reproduce el estado.
- **TOY con óptimo conocido:** "grafo conexo, n = 20, grado máximo ≤ 3, maximizar aristas".
  Óptimo = **30** (existe 3-regular con 20 vértices). Fitness = m si es válido, −1e9 si no.
  El loop debe alcanzar 30. Cambiar mock → Ollama (`gemma3:4b`) → Fireworks → vLLM
  es cambiar UNA URL en `configs/`.

---

## 9. Calibración de la BÚSQUEDA (sin LLM) — `calibracion/ga_graphs.py`

GA mínimo y legible (~150 líneas), porque valida dinámica de búsqueda, no arquitectura:

- Población 200 grafos; selección por torneo k=3; elitismo 10.
- Operadores sobre grafos: `add_edge`, `remove_edge_preservando_conexidad`, `rewire_edge`,
  `graft_camino_pendiente(largo 1–4)`, `agregar_hoja`, `subdividir_arista`, `podar_hoja`,
  `cruza_de_padres` (unión parcial de listas de aristas + reparación de conexidad).
- **Organismo baseline obligatorio en la población inicial**: una búsqueda local estilo AMCS
  (movimientos: agregar hoja / subdividir arista / agregar arista / podar aleatorio, con
  profundidad y nivel adaptativos al estancarse; referencia pública:
  github.com/valentinovito/Adaptive_MC_Search). El estado del arte es el punto de partida
  de la población, no el rival.
- **Seeds estructurales** (familias donde históricamente mueren estas conjeturas, con
  evidencia 2021–2023): estrellas, caminos, cometas, cometas de doble cola DTC(n,p,q),
  lollipops, turnips, kites (K_ω + camino), uniones de dos estrellas por un vértice nuevo
  T(2,b), y peines con espina T₁(k)/T₂(k).
- n libre en [10, 40]. Multi-arranque: 20 corridas con semillas distintas.
- Fitness = gap del evaluador de §2. Log a SQLite o CSV: (gen, best_gap, mejor_grafo_g6).

**Criterio de éxito empírico:** alguna corrida alcanza `gap > 0` (re-descubre la familia del
contraejemplo) en **minutos u horas de CPU, no días** — referencia: AMCS lo logra en 46
segundos y 12 iteraciones desde un árbol aleatorio de orden 5. Si tras una noche no cayó,
el problema es de operadores o de fitness, no de cómputo: diversificar ANTES de tocar la nube.

---

## 10. Definición de "terminado" del Paquete 1

1. `pytest` 100% verde (Wagner en skip mientras no exista el fixture; verde cuando exista).
2. El TOY de §8 alcanza el óptimo 30 con el mock (y opcionalmente con Ollama).
3. `ga_graphs.py` corre 1,000 generaciones sin crash, y la corrida nocturna produce
   `gap > 0` en la calibración.

Solo entonces se enchufa Fireworks (día 6 del evento) cambiando `api_base` en `configs/`.

---

## Fuera de alcance de este paquete (paquetes siguientes)

- Cards y evaluadores de las 20 conjeturas frescas (Paquete 2 — sale de la curaduría).
- Banco de operadores sintetizado por Gemma + prompts de mutación (Paquete 3).
- Bandit UCB multi-universo, dashboard para el URL de entrega, `verify.py` con aritmética
  exacta y `deploy/bootstrap.sh` (Paquete 4).

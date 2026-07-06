# CLAUDE.md — Reglas obligatorias del proyecto Conjecture Hunters

## 1. Disciplina de Git/GitHub (OBLIGATORIA — los jueces evalúan la trayectoria completa)

Los evaluadores del hackathon revisan TODO el historial del repo
(github.com/Hawhaz/conjecture-hunters). Cada sesión DEBE dejar rastro profesional:

1. **Commits atómicos**: una unidad lógica por commit (un evaluador, un fix, un
   test, un módulo). PROHIBIDO acumular horas de trabajo en un mega-commit.
2. **Formato Conventional Commits, en inglés** (jueces internacionales):
   `type(scope): imperative summary ≤72 chars`
   - types: `feat` | `fix` | `test` | `perf` | `refactor` | `docs` | `chore` | `ci`
   - scopes: `evaluators`, `calibracion`, `buscador_rs`, `mock`, `configs`,
     `tests`, `docs`, `dashboard`, `repo`
3. **Cuerpo SIEMPRE** (2-8 líneas): qué + por qué + **evidencia de validación**.
   Ejemplos de evidencia que los jueces deben ver:
   - `pytest: 86 passed, 1 skipped in 73s`
   - `parity vs Python oracle: max |Δgap| = 3e-15 over 5,000 random g6`
   - `counterexample re-discovered: n=18, gap=+0.02181 (AMCS ref: 46s → ours: 0.6s)`
   - `bench: 200 runs 61x faster than Python baseline (rayon, 16 threads)`
4. **pytest antes de cada commit**: verde → commit; rojo → NO se commitea a
   `master` (solo `wip:` en rama aparte, jamás en master).
5. **Push inmediato tras cada commit** — los timestamps de la trayectoria cuentan
   para la evaluación. Nunca terminar una sesión con trabajo sin commitear/pushear.
6. **Al cerrar cada tarea del task list → commit.** Hitos grandes (paquete verde,
   contraejemplo nuevo, kernel Rust con paridad) → commit propio + tag anotado
   (`git tag -a v0.x -m "..."`).
7. Identidad: `user.name "Hawhaz"`, `user.email "ofidenciotirado@gmail.com"`.

## 2. Directiva Rust (orden del dueño, 7-jul-2026 — NO viene de los specs)

El motor de BÚSQUEDA se escribe/refactoriza en Rust (`buscador_rs/`): GA
multi-carril paralelo (rayon), AMCS, operadores, seeds, BFS, matching, λ₁
(faer/nalgebra), binario CLI con el mismo formato CSV que `calibracion/ga_graphs.py`.
Python queda SOLO donde es estrictamente necesario: `evaluators/` congelados
(contrato pytest; los 86 tests son el ORÁCULO de paridad — `gap_rust == gap_python`
a 1e-9 sobre miles de g6 antes de usar Rust en corridas reales), loop
OpenEvolve/LLM (I/O-bound) y `mock_llm/`. Prohibido modificar los tests para que pasen.

## 3. Contexto del evento

AMD Developer Hackathon ACT II (lablab.ai) · equipo "Conjecture Hunters" · Track 3
Unicorn + premio "Best AMD-Hosted Gemma Project" · **deadline 11-jul-2026 9:00 AM PDT**
· entrega vía lablab.ai: repo público + demo video + slide deck (+ containerizado)
· GPU: notebooks.amd.com/hackathon (cuenta ofidenciotirado; acceso desde 7-jul)
· Ollama local: api_base http://localhost:11434/v1, modelo gemma3:4b.

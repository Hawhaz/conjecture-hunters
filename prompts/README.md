# prompts/ — Banco de prompts de mutación Gemma (gemma3:4b vía Ollama)

Este directorio contiene TODO lo necesario para que un LLM (hoy `gemma3:4b`
local vía Ollama, mañana Fireworks/vLLM) actúe como **operador de mutación**
dentro del cazador evolutivo de contraejemplos: recibe el mejor programa
encontrado hasta ahora (un script que imprime aristas `u v`) y devuelve un
parche en formato SEARCH/REPLACE que OpenEvolve puede aplicar directamente.

No toca nada fuera de `prompts/`: no se corrió `git`, `cargo` ni se modificó
ningún otro directorio del repo.

## Árbol de archivos

```
prompts/
├── system_mutador.md       # prompt de sistema (rol fijo, formato SEARCH/REPLACE)
├── plantilla_usuario.md    # plantilla del mensaje de usuario (5 placeholders)
├── banco_conjeturas.md     # CAL-1/2/3: desigualdad, gap, pistas de familias extremales
├── ollama_cliente.py       # cliente urllib-only + CLI --dry-run
├── README.md               # este archivo
└── operadores/              # un fragmento de prompt por familia de mutación
    ├── add_edge.md
    ├── remove_edge_preserving_connectivity.md
    ├── rewire.md
    ├── graft_pendant_path.md
    ├── add_leaf.md
    ├── subdivide_edge.md
    ├── prune_leaf.md
    ├── densify_toward_family.md
    ├── grow_double_tailed_comet.md
    └── two_stars_join.md
```

## Cómo encajan en el loop (§8 del spec)

```
                     ┌─────────────────────────────────────────┐
                     │  system_mutador.md  (role: system)       │
                     │  + plantilla_usuario.md renderizada      │
                     │    con {conjetura} {gap_actual}          │
                     │    {n_actual} {programa_actual}          │
                     │    {historial_operadores}                │
                     └──────────────────┬────────────────────────┘
                                        │  POST /v1/chat/completions
                                        ▼
        mock_llm/server.py  ──O──  ollama_cliente.py  ──O──  Fireworks/vLLM
        (hoy, en tests)        (gemma3:4b, hoy)          (mañana, GPU real)
                                        │
                                        ▼
                     bloque(s) <<<<<<< SEARCH / ======= / >>>>>>> REPLACE
                                        │
                                        ▼
                   OpenEvolve aplica el parche → nuevo programa candidato
                                        │
                                        ▼
                   evaluators/agx_l1_mu.py (u homólogo CAL-2/CAL-3)
                     sandbox AST + subprocess → gap → combined_score
                                        │
                                        ▼
                   gap > 0  ⇒  CONTRAEJEMPLO. Si no, vuelve al tope: el
                   mejor programa nuevo entra como {programa_actual} de
                   la siguiente iteración, con el gap actualizado.
```

**Los tres backends son intercambiables cambiando SOLO `api_base`** (y
`api_key` si el proveedor lo exige vía Bearer token) en la llamada a `mutar(...)`
o en el YAML de OpenEvolve (`llm.models[].api_base`):

| Etapa | api_base | Notas |
|---|---|---|
| Hoy (tests, determinista) | el que levante `mock_llm/server.py` (`http://127.0.0.1:<puerto>/v1`) | round-robin sobre `tests/fixtures/diffs.jsonl`, sin red real |
| Hoy (humo local) | `http://localhost:11434/v1` | Ollama local, modelo `gemma3:4b`, CPU (~1-2 min/iteración) |
| Día 0 (GPU AMD) | endpoint de Fireworks/vLLM | mismo `ollama_cliente.py`, mismas plantillas — cambia el host y probablemente el `api_key` |

Nada en `system_mutador.md`, `plantilla_usuario.md`, `banco_conjeturas.md` ni
`operadores/*.md` depende del backend: son texto plano cargado por
`ollama_cliente.py` vía `open(...)`, independiente de qué servidor OpenAI-
compatible responda al otro lado de `api_base`.

## Los 5 placeholders (contrato exacto)

`plantilla_usuario.md` expone exactamente estos 5 placeholders, rellenados por
`ollama_cliente.py::render_usuario`:

| Placeholder | Origen esperado en el loop real |
|---|---|
| `{conjetura}` | texto de `banco_conjeturas.md` correspondiente al carril activo (CAL-1, CAL-2 o CAL-3) |
| `{gap_actual}` | `metrics["combined_score"]` del mejor programa en la BD de OpenEvolve |
| `{n_actual}` | `metrics["n"]` del mismo programa |
| `{programa_actual}` | el código fuente completo del mejor programa (texto, no AST) |
| `{historial_operadores}` | resumen de texto libre de mutaciones recientes y su efecto en el gap (opcional; si no hay historial, el cliente inserta un mensaje por default) |

El renderizado usa reemplazo literal de marcador (`str.replace`), NO
`str.format()`, precisamente porque `{programa_actual}` es código Python real
que casi siempre trae sus propias llaves (listas, dicts, f-strings) que
romperían un `.format()` ingenuo. Ver el docstring de
`ollama_cliente.py::render_usuario` para el detalle.

## Cómo se calibró el formato de diff

El formato SEARCH/REPLACE de `system_mutador.md` se copió EXACTO de:

- `mock_llm/server.py` — sirve las respuestas de `tests/fixtures/diffs.jsonl`
  tal cual, sin transformarlas.
- `tests/fixtures/diffs.jsonl` — 7 parches enlatados, todos con el patrón
  `<<<<<<< SEARCH\n...\n=======\n...\n>>>>>>> REPLACE\n`.
- `tests/test_loop_mock.py::test_mock_diffs_tienen_formato_search_replace` —
  el regex real que valida el formato: `r"<<<<<<< SEARCH\n(.*?)=======\n(.*?)>>>>>>> REPLACE"`
  con `re.DOTALL`. Los ejemplos de `system_mutador.md` se verificaron contra
  este MISMO regex (ver smoke-test más abajo) y el SEARCH del ejemplo
  concreto se verificó carácter-por-carácter contra
  `calibracion/programa_inicial.py` real.

## Smoke-test (sin gastar tokens ni requerir Ollama arriba)

```
python prompts/ollama_cliente.py --dry-run
```

Esto:

1. Carga `system_mutador.md`, `plantilla_usuario.md` y usa un programa/
   conjetura de ejemplo embebidos (comet CAL-1, `HOJAS=12/LARGO_COLA=6`,
   `n=19`, `gap=-2.375495371091703` — los mismos valores que
   `calibracion/runs/humo_ollama/best/best_program_info.json`).
2. Renderiza el mensaje `role: user` completo (los 5 placeholders resueltos).
3. Imprime ambos mensajes (system + user) y un resumen — **sin abrir ningún
   socket**, así que funciona igual con Ollama arriba o caído.
4. Termina con `[DRY-RUN] OK: plantillas cargadas y renderizadas sin errores,
   sin tocar la red.` y código de salida 0.

Variantes útiles:

```
# con historial de operadores explícito
python prompts/ollama_cliente.py --dry-run --historial "add_leaf: gap -0.40 -> -0.35 (subio); rewire: -0.35 -> -0.38 (bajo, descartado)"

# con un programa y conjetura reales del repo
python prompts/ollama_cliente.py --dry-run --programa calibracion/programa_inicial.py --gap -2.3754953711 --n 19

# llamada REAL contra Ollama local (requiere `ollama serve` + `ollama pull gemma3:4b`)
python prompts/ollama_cliente.py --gap -2.3754953711 --n 19
```

Si Ollama está caído y se corre SIN `--dry-run`, el cliente atrapa el error de
red (`urllib.error.URLError`/`OSError`), imprime un mensaje claro sugiriendo
`--dry-run` o levantar Ollama/el mock, y sale con código 1 (no lanza traceback
crudo).

## Notas de implementación

- **Sin dependencias externas**: `ollama_cliente.py` usa solo `argparse`,
  `json`, `os`, `sys`, `urllib.error`, `urllib.request` — todo stdlib. No
  requiere `requests`, `httpx` ni el SDK de OpenAI.
- **Import como librería**: `from prompts.ollama_cliente import mutar` expone
  la función `mutar(programa, conjetura, gap, n, api_base=..., model=...)
  -> str` que devuelve el diff crudo del modelo (sin parsear — el parseo y
  aplicación del diff es responsabilidad de OpenEvolve).
- **`banco_conjeturas.md` como fuente de `{conjetura}`**: quien orqueste el
  loop real (fuera de este directorio) debe extraer el bloque correspondiente
  a CAL-1/CAL-2/CAL-3 de `banco_conjeturas.md` y pasarlo como el argumento
  `conjetura` de `mutar(...)`; `ollama_cliente.py` expone
  `cargar_banco_conjeturas()` para leer el archivo completo si se prefiere
  recortar el bloque activo en el orquestador en vez de aquí.
- **Los `operadores/*.md` son material de referencia para quien escriba el
  prompt final**, no se auto-insertan en `plantilla_usuario.md` — si se
  quiere que el LLM vea el catálogo completo de operadores en cada llamada,
  concatenar su contenido en `{historial_operadores}` o en un placeholder
  nuevo es una extensión sencilla, pero se dejó fuera del contrato de 5
  placeholders pedido para no inflar el prompt en cada iteración (gemma3:4b
  corre en CPU en el humo local; prompts más cortos = iteraciones más rápidas).

# orquestador/ — Orquestador evolutivo caza-contraejemplos

El centro del cazador: un bucle evolutivo que refuta conjeturas espectrales de
teoria de grafos combinando **cascada de evaluacion** (validez → gap rapido en
Rust → **certificado exacto**), **islas + archivo MAP-Elites**, **bandit Thompson
descontado**, **muestreo de padres por novedad + rechazo de duplicados** y una
**capa de mutacion** con backend `mock` (determinista, CI) u `ollama` (opt-in).

El diseno y sus citas (FunSearch / AlphaEvolve / ShinkaEvolve / MAP-Elites /
Thompson / trees-only / certificado exacto) estan en **`DISENO.md`**.

> **Invariante de oro:** el `gap` continuo ORDENA la busqueda; solo el
> **certificado exacto** (T3) DECLARA un contraejemplo. El gap rapido nunca es
> el veredicto final (defensa anti reward-hacking).

## Correr YA (mock, sin red, sin GPU)

Desde la **raiz del repo** (`conjeturas/`):

```bat
python orquestador\orquestar.py --conjeturas cal1 --iters 300 --llm mock ^
    --islas 5 --semilla 7 --out calibracion\runs\orq_log.csv
```

En Windows con el binario Rust ya compilado, T2 usa
`buscador_rs\target\release\buscador_rs.exe` automaticamente (lote paralelo,
~10k evals/s). En una plataforma sin ese `.exe` (p. ej. CI Linux), agrega
`--forzar-python-eval` y la cascada usa el oraculo `parity/refs.py`, que da el
**mismo gap** por contrato de paridad (los 86 pytest son el oraculo).

Salida esperada (mock, cal1): encuentra y **certifica** un contraejemplo de
CAL-1 en <1 s de CPU, imprimiendo el g6, el gap y el **margen del certificado**
(cota inferior EXACTA de gap; p. ej. `-400333/87943 + sqrt(23)` ≈ 0.24).

### Flags principales

| Flag | Def | Que hace |
|---|---|---|
| `--conjeturas cal1,cal2,cal3` | cal1 | conjeturas a atacar (coma-separadas) |
| `--iters N` | 400 | mutaciones por conjetura |
| `--llm mock\|ollama` | mock | backend de mutacion (`mock` = CI determinista) |
| `--islas N` | 5 | islas del archipielago (MAP-Elites por isla) |
| `--trees-only` | off | restringe a operadores de arbol (**palanca AMCS n=203**) |
| `--semilla N` | 7 | semilla RNG global (reproducibilidad) |
| `--reset-cada N` | 40 | hard-reset de la peor mitad de islas cada N iters |
| `--forzar-python-eval` | off | usa el oraculo Python en vez del binario Rust |
| `--sin-certificado` | off | no correr T3 al vuelo (modo benchmark de busqueda) |
| `--out RUTA.csv` | — | log CSV (esquema `ga_graphs.py`, para el dashboard) |

## Ollama (opt-in, gemma3:4b local)

El backend LLM propone **deltas de lista de aristas** a partir de un few-shot
**ranqueado** de elites (fitness como **rango ordinal**, no floats — un 4B no
razona sobre floats; ver `DISENO.md` decision 7). Cada delta se aplica de forma
determinista en codigo, best-of-N=4, validando conectividad. Si Ollama no
responde, **cae a `mock`** (nunca crashea).

```bat
ollama serve
ollama pull gemma3:4b
python orquestador\orquestar.py --conjeturas cal1 --iters 200 --llm ollama --out calibracion\runs\orq_log.csv
```

### Cambiar de proveedor (vLLM / Fireworks / AMD Dev Cloud)

Es **solo cambiar `api_base`** (y `api_key` si el proveedor la exige por Bearer)
en `orquestador/configs/default.yaml` (bloque `ollama:`) o al construir el
`Mutador`. El transporte es OpenAI-compatible (`POST {api_base}/chat/completions`),
igual que `prompts/ollama_cliente.py`:

```yaml
ollama:
  api_base: https://api.fireworks.ai/inference/v1   # o el endpoint vLLM/AMD
  model: accounts/fireworks/models/gemma-3-4b-it
  api_key: <token>
```

## Como alimenta el dashboard

El log CSV tiene la **misma cabecera** que `calibracion/ga_graphs.py`:

```
corrida,gen,best_gap,best_g6,n,evento,epoch
```

Por eso el dashboard existente (`dashboard/`) lo lee sin cambios: apunta el
dashboard a `calibracion/runs/orq_log.csv`. El evento pasa de `gen` a
`contraejemplo` en la generacion donde T3 certifica, marcando el hito en la
curva. `epoch` es el timestamp Unix por fila (progreso temporal).

## Modulos

| Archivo | Rol |
|---|---|
| `grafos.py` | codec g6 (paridad 0..n-1 'sorted'), descriptores n/densidad, WL-hash, deltas, operadores arbol/conexo, familias de semilla |
| `evaluar.py` | cascada T1/T2: gap en LOTE via binario Rust; fallback oraculo Python |
| `certificar.py` | compuerta T3: envuelve `certificados/verify.certificar` (exacto) |
| `archivo.py` | islas + archivo MAP-Elites + hard-reset de la peor mitad |
| `bandit.py` | Thompson descontado (Beta-Bernoulli, γ=0.99) sobre (conjetura×operador) |
| `mutador.py` | mutacion `mock` (determinista) / `ollama` (delta de aristas, fallback) |
| `orquestar.py` | bucle principal + CLI + novelty-parent + shaping CAL-3 + CSV |
| `configs/` | `default.py` y `default.yaml` (hiperparametros ↔ decisiones de DISENO) |
| `tests/` | humo determinista mock (pytest) |

## Tests

```bat
python -m pytest orquestador\tests\test_orquestador.py -q
```

No dependen del binario Rust ni de Ollama (usan `forzar_python=True` y el backend
`mock`), asi que corren en cualquier plataforma. El `pytest.ini` del repo tiene
`testpaths = tests`, por lo que la suite de `orquestador/tests/` **no** se
recolecta en el `pytest` por defecto (los 86 tests existentes quedan intactos);
se corre explicitando la ruta como arriba.

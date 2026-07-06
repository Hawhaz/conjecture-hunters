# Dashboard GA — Cazador de contraejemplos

Visualiza los CSV que emite el algoritmo genético multi-carril (`corrida,gen,best_gap,best_g6,n,evento,epoch`).
`gap > 0` ⇔ se encontró un contraejemplo.

## Archivos

- `dashboard.html` — versión "viva": carga un CSV por drag-and-drop / botón, o intenta
  auto-cargar `../calibracion/runs/ga_log_sin_seeds.csv` vía `fetch`.
- `build_dashboard.py` — script (solo stdlib) que lee un CSV y genera `dashboard_baked.html`,
  con los datos incrustados como JSON. Se abre directo desde el disco, sin servidor.
- `dashboard_baked.html` — salida generada por `build_dashboard.py` (no editar a mano; se
  regenera cada vez que se corre el script).

## Cómo abrirlo

### Opción A — servidor local (recomendada para `dashboard.html`)

El `fetch` a `../calibracion/runs/ga_log_sin_seeds.csv` solo funciona si la página se sirve
por HTTP (no funciona con `file://` por las restricciones CORS del navegador). Para eso,
servir la **raíz del repo** (no la carpeta `dashboard/`) y abrir `dashboard.html` desde ahí:

```cmd
cd /d C:\Users\123\Documents\hackthon\conjeturas
python -m http.server 8000
```

Luego abrir en el navegador:

```
http://localhost:8000/dashboard/dashboard.html
```

Va a auto-cargar `ga_log_sin_seeds.csv` apenas abra. Si el fetch falla (por ejemplo si se
abrió el archivo directamente con doble click, `file://`), el dashboard lo indica con un
mensaje y vos podés cargar el CSV a mano con el botón "Elegir CSV…" o arrastrándolo sobre
la zona punteada.

### Opción B — abrir directo desde el disco (sin servidor)

Abrir `dashboard_baked.html` con doble click o arrastrándolo a una pestaña del navegador.
Ya tiene los datos incrustados (por defecto, los de `ga_log_sin_seeds.csv` al momento en que
se generó), así que no necesita servidor ni conexión.

Si preferís partir de `dashboard.html` sin servidor, también funciona: el `fetch` inicial va
a fallar silenciosamente (mensaje de error visible pero no bloqueante) y podés cargar
cualquier CSV a mano con el botón o soltándolo en la zona de drag-and-drop.

## Cómo apuntarlo a un CSV nuevo (generado por el Rust)

Una vez que el buscador en Rust (`buscador_rs`) escriba un CSV nuevo con el mismo esquema
de columnas, hay dos formas de verlo:

1. **Sin tocar nada**: en `dashboard.html` (servido por HTTP), usar el botón "Elegir CSV…"
   o arrastrar el archivo nuevo sobre la zona punteada. Reemplaza los datos en memoria al
   instante, sin recargar la página.

2. **Regenerar el baked file**: correr `build_dashboard.py` apuntando al CSV nuevo:

```cmd
cd /d C:\Users\123\Documents\hackthon\conjeturas
python dashboard\build_dashboard.py --csv ruta\al\csv_nuevo.csv
```

Por defecto, sin `--csv`, usa `calibracion\runs\ga_log_sin_seeds.csv`. También se puede
elegir dónde guardar la salida con `--out`:

```cmd
python dashboard\build_dashboard.py --csv ruta\al\csv_nuevo.csv --out dashboard\dashboard_baked.html
```

El script es puro stdlib (`csv`, `json`, `argparse`, `pathlib`) — no necesita instalar nada.

## Qué muestra

- **Gráfico multilínea**: `best_gap` en función de `gen`, una línea por `corrida` (carril),
  con una línea blanca punteada gruesa en `gap = 0` marcando el umbral de contraejemplo.
- **Tarjetas KPI**: cantidad de carriles, mejor gap global, cuántos carriles cruzaron
  `gap > 0`, la primera generación en que algún carril cruzó, y el `n` (vértices) mínimo
  entre los contraejemplos encontrados.
- **Tabla ordenable por carril**: `corrida`, mejor/última `best_gap`, generación del primer
  contraejemplo (o "—" si no lo encontró), `n`, y `best_g6` truncado (click para copiar el
  string completo al portapapeles). Las filas de carriles que encontraron contraejemplo se
  resaltan en verde.

## Notas

- Ambos HTML son autocontenidos salvo por Chart.js, que se carga desde cdnjs
  (`https://cdnjs.cloudflare.com/ajax/libs/Chart.js/...`). Si no hay conexión a internet,
  el gráfico no va a renderizar pero las KPIs y la tabla sí funcionan.
- No se usa `localStorage` ni `sessionStorage` en ningún archivo.
- El parser de CSV en el HTML es propio (no depende de librerías externas) y soporta campos
  con comillas, comas y saltos de línea internos, además de CRLF.

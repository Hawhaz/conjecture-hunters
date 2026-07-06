# plantilla_usuario.md — Plantilla del mensaje `role: user`

> Se renderiza vía reemplazo literal de marcador (NO `str.format`) desde
> `ollama_cliente.py::render_usuario`. Placeholders exactos — no renombrar sin
> actualizar el cliente: `{conjetura}`, `{gap_actual}`, `{n_actual}`,
> `{programa_actual}`, `{historial_operadores}`. Se usa reemplazo simple
> (`str.replace`) y NO `str.format()` porque el código Python que va dentro de
> `{programa_actual}` casi siempre trae llaves propias (listas, dicts,
> f-strings) que romperían un `.format()` ingenuo. Todo el texto ANTES del
> separador `---` de abajo es documentación para quien lee este archivo en el
> editor; el cliente descarta ese encabezado antes de renderizar (así las
> menciones de `{conjetura}` etc. aquí arriba no se confunden con los
> placeholders reales del cuerpo).

---

## Objetivo

Estás mutando un programa que genera un grafo, dentro de una búsqueda
evolutiva de contraejemplos. El objetivo numérico es UNO SOLO: subir el valor
de `gap`. `gap > 0` significa que el grafo actual YA es un contraejemplo
publicable; `gap` más alto (aunque siga negativo) significa que el programa
está más cerca de serlo. No hay ningún otro criterio de éxito.

## Conjetura activa

{conjetura}

## Estado actual de la búsqueda

- **gap actual**: {gap_actual}
- **n actual** (número de vértices del grafo que imprime el programa): {n_actual}
- **historial de operadores recientes** (qué se intentó ya y con qué efecto en
  el gap; evita repetir un movimiento que ya se probó en el mismo lugar sin
  subir el gap):

{historial_operadores}

## Programa actual (a mutar)

```python
{programa_actual}
```

## Tu tarea

1. Elige **un solo** movimiento estructural pequeño (agregar/quitar una arista,
   injertar una hoja o un camino pendiente, subdividir una arista, cambiar UN
   parámetro numérico del bloque `EVOLVE-BLOCK`, etc. — ver `operadores/*.md`
   para el catálogo completo con ejemplos).
2. Verifica mentalmente que el grafo resultante sigue siendo conexo, simple,
   con vértices `0..n-1` sin huecos, y `3 ≤ n ≤ 300`.
3. Prioriza moverte hacia las familias donde esta conjetura concreta
   históricamente se refuta (revisa la pista en la sección "Conjetura activa"
   arriba y `banco_conjeturas.md`).
4. Expresa ese único cambio como uno o más bloques `SEARCH/REPLACE` que citen
   líneas EXACTAS del "Programa actual" de arriba.
5. No expliques tu razonamiento. No agregues texto fuera de los bloques.
   Responde solo con el/los bloque(s) de parche.

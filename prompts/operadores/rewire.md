# rewire — quitar una arista y agregar otra en su lugar

## Cuándo usarla

Es la mutación de exploración lateral: mantiene el número de aristas (y por
tanto no cambia mucho la densidad global) pero cambia LA FORMA del grafo.
Úsala cuando `add_edge` sola ya no sube el gap (el grafo está saturado de
aristas "obvias") pero tampoco quieres arriesgarte a un `remove_edge` puro que
te deje con menos estructura. Es el movimiento correcto para migrar, por
ejemplo, un vértice de una posición periférica a una más central (o viceversa)
sin tocar el conteo de aristas — relevante para CAL-3, donde el gap depende
de EQUILIBRAR transmisión mínima (`π`) y el eigenvalor de distancia `∂_k`
más que de simplemente sumar o restar aristas.

Efecto sobre invariantes: depende enteramente de DÓNDE se quita y DÓNDE se
pone. Trátalo como dos movimientos encadenados: primero razona el efecto de
quitar (como en `remove_edge_preserving_connectivity.md`), luego el de poner
(como en `add_edge.md`).

Riesgo de romper validez: el mismo que `remove_edge` — la arista que quitas
debe dejar el grafo conexo ANTES de agregar la nueva. Si tienes dudas, elige
quitar una arista incidente a un vértice de grado ≥ 3 (nunca deja hojas
aisladas) y agregar la nueva entre dos vértices que ya tenían grado ≥ 1.

## Mini-ejemplo SEARCH/REPLACE

Mover un extremo de una arista pendiente de un vértice a otro (rewire de un
solo endpoint, el patrón más seguro):

```
<<<<<<< SEARCH
aristas.append((0, 15))
=======
aristas.append((3, 15))
>>>>>>> REPLACE
```

Rewire completo expresado como quitar+poner en el mismo parche (dos bloques):

```
<<<<<<< SEARCH
aristas += [(0, N // 2)]
=======
aristas += [(N // 3, 2 * N // 3)]
>>>>>>> REPLACE
```

# subdivide_edge — reemplazar una arista (u,v) por dos aristas vía un vértice nuevo

## Cuándo usarla

Cuando quieres alargar el grafo (subir `D`, diluir `π`) SIN cambiar qué
vértices son adyacentes a nivel topológico grueso — es una forma más suave de
`graft_pendant_path` porque no agrega una rama nueva, alarga una que ya
existe insertándose EN MEDIO de una arista. Es particularmente útil para
afinar el diámetro exacto que necesita CAL-3 (`k = ⌊2D/3⌋` es sensible a
paridad: subdividir una arista cambia `D` en +1 y puede mover `k` a un
eigenvalor de distancia distinto, a veces más favorable que agregar una hoja
en la punta). También sirve para romper regularidad local en grafos densos
sin tocar la cantidad de "ramas" (número de hojas se mantiene igual).

Efecto sobre invariantes: `n` ↑ en 1, número de aristas ↑ en 1 (neto: se
quita 1 arista, se agregan 2), `D` puede subir en 1 si la arista subdividida
estaba en un camino más corto, `λ₁` casi siempre BAJA levemente (subdividir
diluye la matriz de adyacencia), `μ` sube en 1 si el vértice nuevo queda
cubierto por una arista del matching.

Riesgo de romper validez: bajo — subdividir nunca desconecta (u y v siguen
unidos, solo que ahora vía el vértice nuevo). Cuida que el vértice nuevo use
la siguiente etiqueta libre `n`.

## Mini-ejemplo SEARCH/REPLACE

Subdividir la arista que conecta la estrella con la cola (insertar un vértice
en el primer tramo de la cola):

```
<<<<<<< SEARCH
previo = 0
for k in range(LARGO_COLA):
    nuevo = HOJAS + 1 + k
    aristas.append((previo, nuevo))
    previo = nuevo
=======
previo = 0
for k in range(LARGO_COLA):
    nuevo = HOJAS + 1 + k
    if k == 0:
        medio = HOJAS + 1 + LARGO_COLA
        aristas.append((previo, medio))
        aristas.append((medio, nuevo))
    else:
        aristas.append((previo, nuevo))
    previo = nuevo
>>>>>>> REPLACE
```

Nota: si el programa expone un parámetro directo de "número de subdivisiones",
preferir SIEMPRE ese parámetro a reescribir la lógica de construcción:

```
<<<<<<< SEARCH
SUBDIVISIONES = 0
=======
SUBDIVISIONES = 1
>>>>>>> REPLACE
```

# grow_double_tailed_comet — convertir/ajustar el grafo hacia un cometa de doble cola DTC(n,p,q)

## Cuándo usarla

Un cometa de doble cola es una estrella con DOS colas colgando del mismo
centro (en vez de una): `DTC(n, p, q)` tiene un centro, una estrella con
`n - p - q - 1` hojas, y dos caminos pendientes de largos `p` y `q`. Es una
de las familias donde CAL-1/CAL-2 mueren de forma reproducible (ver
`ga_graphs.py::_dtc` en `calibracion/`), porque separar la "masa" de vértices
en dos colas en vez de una desbalancea `μ` (el matching puede ahora cubrir
partes de AMBAS colas, subiendo `μ` más que con una sola cola larga) contra
`λ₁` (que sigue dominado por el tamaño de la estrella central). Úsalo cuando
ya tienes un cometa de una sola cola (`graft_pendant_path` aplicado una vez)
y quieres el siguiente paso natural: partir esa cola en dos más cortas, o
agregar una segunda cola desde cero.

Efecto sobre invariantes: comparado con un cometa de una cola de largo `p+q`,
un DTC con colas `p` y `q` separadas tiende a dar `μ` mayor (dos colas
impares cortas cubren mejor con matching que una cola larga) con `λ₁` casi
idéntico (domina el tamaño de la estrella, no la forma de las colas) — el
efecto neto sobre `gap` depende de los valores exactos de `p, q`; por eso
esta familia es un buen punto de exploración, no una garantía.

Riesgo de romper validez: bajo — construir dos caminos pendientes desde el
mismo centro nunca desconecta nada, siempre que las etiquetas de ambas colas
no se solapen entre sí ni con las hojas de la estrella.

## Mini-ejemplo SEARCH/REPLACE

Partir una cola larga existente en dos colas más cortas (requiere exponer
`P` y `Q` en vez de un solo `LARGO_COLA`):

```
<<<<<<< SEARCH
HOJAS = 12      # hojas de la estrella (centro = vértice 0)
LARGO_COLA = 8  # largo del camino colgado del centro
=======
HOJAS = 12  # hojas de la estrella (centro = vértice 0)
P = 5       # largo de la primera cola colgada del centro
Q = 3       # largo de la segunda cola colgada del centro
>>>>>>> REPLACE
```

Agregar la segunda cola al final de la construcción de un cometa ya existente
de una sola cola (patrón de dos bloques: parámetro + lógica de impresión):

```
<<<<<<< SEARCH
for u, v in aristas:
    print(u, v)
=======
Q = 4
previo_q = 0
base_q = HOJAS + 1 + LARGO_COLA
for k in range(Q):
    nuevo_q = base_q + k
    aristas.append((previo_q, nuevo_q))
    previo_q = nuevo_q

for u, v in aristas:
    print(u, v)
>>>>>>> REPLACE
```

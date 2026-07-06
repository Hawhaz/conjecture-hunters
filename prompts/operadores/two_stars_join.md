# two_stars_join — unir los centros de dos estrellas a un vértice común (o entre sí)

## Cuándo usarla

Es la construcción EXACTA del fixture B de CAL-2 (centros de `S15` y `S19`
unidos a un vértice nuevo, ver `banco_conjeturas.md`) y de la familia
`T(2,b)` / `_dos_estrellas` de `ga_graphs.py`: dos estrellas de tamaños
distintos cuyos centros se conectan (directamente, o vía un vértice
intermedio nuevo). El mecanismo que rompe la conjetura: cada estrella grande
por sí sola tiene `λ₂` muy negativo (el segundo eigenvalor de una estrella
pura es 0), pero DOS estrellas unidas producen un segundo eigenvalor grande
y positivo (la unión se comporta espectralmente como un grafo bipartito casi
completo entre los dos centros de alto grado), mientras que `Hc` (el índice
armónico) se mantiene bajo porque casi todas las aristas siguen siendo
centro-hoja de grado dispar (`2/(d_u+d_v)` pequeño cuando un extremo tiene
grado alto). Úsala cuando la conjetura activa sea CAL-2, o cuando el
historial muestre que estás estancado con una sola estrella y necesitas una
segunda fuente de grado alto para mover `λ₂`.

Efecto sobre invariantes: `λ₂` ↑ marcadamente (mecanismo central de CAL-2),
`Hc` se mantiene bajo (mayoría de aristas centro-hoja de grado dispar),
`λ₁` sube levemente (más masa total), `μ` sube en 1-2 (el enlace entre
centros y/o el vértice intermedio se vuelve emparejable).

Riesgo de romper validez: bajo — unir dos estrellas ya construidas por un
solo vértice nuevo (o una arista directa centro-centro) nunca desconecta
nada, siempre que las dos estrellas usen rangos de etiquetas disjuntos.

## Mini-ejemplo SEARCH/REPLACE

Cambiar el tamaño relativo de dos estrellas ya unidas (ajuste fino de `a, b`
en el patrón `T(2,b)`):

```
<<<<<<< SEARCH
TAM_ESTRELLA_1 = 15
TAM_ESTRELLA_2 = 19
=======
TAM_ESTRELLA_1 = 12
TAM_ESTRELLA_2 = 22
>>>>>>> REPLACE
```

Construir la unión desde cero: dos estrellas + vértice puente (patrón
literal del fixture B de CAL-2, con centros en `0` y `TAM_ESTRELLA_1`):

```
<<<<<<< SEARCH
for u, v in aristas:
    print(u, v)
=======
centro2 = TAM_ESTRELLA_1
puente = TAM_ESTRELLA_1 + TAM_ESTRELLA_2
aristas.append((0, puente))
aristas.append((centro2, puente))

for u, v in aristas:
    print(u, v)
>>>>>>> REPLACE
```

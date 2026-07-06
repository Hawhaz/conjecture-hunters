# prune_leaf — quitar un vértice de grado 1 (y su arista)

## Cuándo usarla

Es el inverso de `add_leaf`: úsalo cuando el grafo se pasó de tamaño (`n`
cerca de 300, o simplemente más grande de lo necesario para el efecto que
buscas) o cuando una rama específica está DILUYENDO el gap en vez de
ayudarlo (por ejemplo, una cola demasiado larga en CAL-1 puede bajar `λ₁`
más de lo que sube `μ` — vale la pena podar y volver a medir). También es el
movimiento correcto cuando el historial de operadores muestra que la última
mutación de `add_leaf` o `graft_pendant_path` bajó el gap: revertir podando
es más barato que reconstruir desde cero.

Efecto sobre invariantes: `n` ↓ en 1, `λ₁` sube levemente o queda igual
(menos "masa" de baja conectividad), `μ` baja en 1 SOLO si esa hoja estaba
cubierta por el matching máximo, `D` baja o igual.

Riesgo de romper validez: MEDIO — si podas la única hoja que mantenía a un
vértice de grado 2 conectado en un extremo de camino, está bien (ese vértice
de grado 2 pasa a ser la nueva hoja). Pero si podas el vértice que hace de
PUENTE entre dos ramas (grado ≥ 2 que no es realmente una hoja), desconectas
el grafo. Regla dura: solo podar vértices con grado EXACTAMENTE 1. Después de
podar, todas las etiquetas de vértices por encima de la podada deben
renumerarse para no dejar huecos (o, más simple, podar siempre el vértice de
etiqueta más alta si es una hoja).

## Mini-ejemplo SEARCH/REPLACE

Acortar la cola de un cometa en un vértice (patrón `LARGO_COLA`):

```
<<<<<<< SEARCH
LARGO_COLA = 8  # largo del camino colgado del centro
=======
LARGO_COLA = 7  # largo del camino colgado del centro
>>>>>>> REPLACE
```

Quitar la última hoja agregada explícitamente (vértice de etiqueta más alta,
seguro para no dejar huecos):

```
<<<<<<< SEARCH
aristas.append((3, 25))

for u, v in aristas:
=======
for u, v in aristas:
>>>>>>> REPLACE
```

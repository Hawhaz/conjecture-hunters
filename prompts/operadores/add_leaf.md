# add_leaf — colgar una hoja nueva (vértice de grado 1) de un vértice existente

## Cuándo usarla

Es el movimiento más pequeño y más seguro disponible: agrega exactamente un
vértice nuevo, de grado 1, sin tocar ninguna otra arista. Úsalo para hacer
crecer estrellas (subir el número de hojas de una estrella sube `λ₁` de forma
sublineal — `λ₁(S_n) = √(n-1)` — mientras que `μ` de una estrella se queda
fijo en 1: esta brecha es exactamente por qué las estrellas grandes casi
refutan CAL-1). También es el ajuste fino de última milla cuando ya
encontraste la familia correcta (comet, DTC, dos-estrellas) y solo falta
calibrar el tamaño exacto de una rama en 1 vértice para cruzar `gap > 0`.

Efecto sobre invariantes: `λ₁` ↑ levemente si la hoja cuelga de un vértice de
grado ya alto (refuerza el centro de una estrella), casi nulo si cuelga de una
hoja existente (eso en realidad es `graft_pendant_path` de largo 1). `μ` sube
en 1 SOLO si el vértice del que cuelga no estaba ya cubierto por el matching
máximo — en una estrella pura, agregar una hoja NUNCA sube `μ` (sigue siendo
1), que es precisamente el mecanismo detrás de CAL-1.

Riesgo de romper validez: mínimo — un vértice nuevo de grado 1 nunca
desconecta nada. Solo cuida la etiqueta: debe ser exactamente `n` (el
siguiente entero libre), nunca un número salteado.

## Mini-ejemplo SEARCH/REPLACE

Subir el número de hojas de una estrella en 1 (patrón `HOJAS` del programa
inicial de CAL-1):

```
<<<<<<< SEARCH
HOJAS = 12      # hojas de la estrella (centro = vértice 0)
=======
HOJAS = 13      # hojas de la estrella (centro = vértice 0)
>>>>>>> REPLACE
```

Colgar una hoja suelta de un vértice específico que no sea el centro (para
romper la simetría de la estrella, útil en CAL-2 donde el gap depende de
grados dispares en los extremos de las aristas — ver `Hc`):

```
<<<<<<< SEARCH
for u, v in aristas:
    print(u, v)
=======
aristas.append((3, len(aristas) + 20))

for u, v in aristas:
    print(u, v)
>>>>>>> REPLACE
```

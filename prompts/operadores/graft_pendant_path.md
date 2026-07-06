# graft_pendant_path — injertar un camino colgante desde un vértice existente

## Cuándo usarla

Es EL movimiento que construye cometas, cometas de doble cola y el
contraejemplo de CAL-3 (estrella + dos colas cortas). Úsalo cuando el grafo ya
tiene un núcleo denso o una estrella y quieres alargar el diámetro sin tocar
el núcleo: cada vértice nuevo en el camino sube `D` (diámetro) en 1 y diluye
la transmisión mínima `π` (los vértices del núcleo quedan más "cerca del
centro de masa" relativo a los de la cola). Es la mutación de referencia para
CAL-3, donde el contraejemplo publicado es exactamente "estrella grande +
un camino corto colgado en un punto + otro camino corto colgado en otro punto"
(fixture C: S₁₉₁ + P₇ + P₅, ver `banco_conjeturas.md`).

Efecto sobre invariantes: `D` ↑ (uno por vértice agregado en la punta de la
cola), `π` tiende a bajar (más masa lejos del centro), `λ₁` casi no cambia
(las colas son de grado 1, aportan poco al radio espectral de adyacencia),
`μ` sube en 1 cada 2 vértices de cola agregados (la cola es un camino, matching
perfecto en sus propias aristas).

Riesgo de romper validez: bajo — un camino colgado de un vértice existente
nunca desconecta nada, siempre que cada nuevo vértice reciba una etiqueta
consecutiva `n, n+1, n+2, ...` sin huecos.

## Mini-ejemplo SEARCH/REPLACE

Alargar una cola ya existente en dos vértices más (patrón `LARGO_COLA` del
programa inicial de CAL-1):

```
<<<<<<< SEARCH
LARGO_COLA = 6  # largo del camino colgado del centro
=======
LARGO_COLA = 8  # largo del camino colgado del centro
>>>>>>> REPLACE
```

Injertar una SEGUNDA cola corta desde el centro de una estrella (patrón del
fixture C de CAL-3 — construir el segundo brazo pendiente):

```
<<<<<<< SEARCH
for u, v in aristas:
    print(u, v)
=======
LARGO_COLA_2 = 5
previo2 = 0
for k in range(LARGO_COLA_2):
    nuevo2 = len(aristas) + 1 + k
    aristas.append((previo2, nuevo2))
    previo2 = nuevo2

for u, v in aristas:
    print(u, v)
>>>>>>> REPLACE
```

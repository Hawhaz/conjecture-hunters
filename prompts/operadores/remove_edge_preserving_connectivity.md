# remove_edge_preserving_connectivity — quitar una arista sin desconectar

## Cuándo usarla

Cuando el grafo es denso o casi-regular y el objetivo es EMPOBRECER
localmente `λ₁` o alejarlo de la cota (útil cuando el gap mejora al reducir
`λ₁ + μ` en CAL-1, o al bajar `Hc` — el índice armónico baja cuando se quita
una arista de grado alto — sin tirar tanto `λ₂` en CAL-2). También es el
primer paso obligatorio antes de un `rewire`: nunca quites una arista sin
inmediatamente comprobar (o, en el siguiente turno, forzar) que el grafo
sigue conexo.

Efecto sobre invariantes: `λ₁` ↓ (o igual), `Hc` ↓ (menos términos en la
suma armónica), `μ` puede bajar si la arista quitada era la única que cubría
un vértice, `D` sube o igual (menos atajos).

Riesgo de romper validez: ALTO si se elige mal la arista — quitar un puente
(bridge) desconecta el grafo y el programa se rechaza completo
(`combined_score = -1e9`). Regla dura: NUNCA quites la única arista que
conecta una hoja o una rama entera al resto del grafo sin revisar que exista
otro camino. Ante la duda, prefiere quitar una arista de un ciclo (una cuerda)
en vez de una arista de la espina/árbol.

## Mini-ejemplo SEARCH/REPLACE

Grafo con una cuerda extra en un ciclo (quitarla preserva conexidad porque el
resto del ciclo sigue uniendo todo):

```
<<<<<<< SEARCH
aristas = [(i, (i + 1) % N) for i in range(N)]
aristas += [(0, N // 2)]
=======
aristas = [(i, (i + 1) % N) for i in range(N)]
>>>>>>> REPLACE
```

Parámetro de cuerdas (bajar el nivel de densificación en vez de enumerar
aristas a mano):

```
<<<<<<< SEARCH
CUERDAS = 4
=======
CUERDAS = 2
>>>>>>> REPLACE
```

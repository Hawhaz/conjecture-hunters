# add_edge — agregar una arista entre dos vértices no adyacentes

## Cuándo usarla

Cuando el grafo actual es demasiado disperso (árbol o casi-árbol) y subir
`λ₁` (radio espectral de adyacencia) ayuda más que seguir alargando colas.
Añadir una arista SIEMPRE sube o mantiene `λ₁` (monotonía espectral), así que
es la mutación de menor riesgo cuando el gap depende de aumentar `λ₁` o
`λ₂` (CAL-1, CAL-2). Úsala con moderación en CAL-3: más aristas suele bajar
el diámetro `D` y con él `k = ⌊2D/3⌋`, lo cual puede no ser lo que quieres si
el objetivo es mantener un diámetro grande con excentricidad concentrada.

Efecto sobre invariantes: `λ₁` ↑ (o igual), `λ₂` puede subir o bajar según
dónde se agregue, `μ` (matching) puede subir si la arista nueva conecta dos
vértices antes no emparejables, `D` baja o igual.

Riesgo de romper validez: bajo — agregar una arista entre dos vértices
existentes nunca desconecta el grafo ni produce huecos de etiquetado. Solo
verifica que no sea un lazo (`u != v`) ni una arista ya presente.

## Mini-ejemplo SEARCH/REPLACE

Programa con una lista fija de aristas dentro del bloque evolutivo:

```
<<<<<<< SEARCH
aristas = [(0, 1), (1, 2), (2, 3), (3, 4)]
=======
aristas = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
>>>>>>> REPLACE
```

Programa con parámetro de densidad (p. ej. cuerdas de un ciclo, como en el TOY
`NIVEL`):

```
<<<<<<< SEARCH
CUERDAS = 3
=======
CUERDAS = 4
>>>>>>> REPLACE
```

# densify_toward_family — mover un parámetro de forma hacia una familia extremal conocida

## Cuándo usarla

Es un movimiento de NIVEL SUPERIOR (no toca aristas individuales): cuando el
programa actual expone un parámetro discreto de "qué tan cerca estoy de la
familia X" (como el `NIVEL` del TOY, que interpola entre camino → ciclo →
ciclo con cuerdas → 3-regular), este operador sube o baja ese nivel UN paso
hacia la familia extremal que la conjetura activa necesita (ver
`banco_conjeturas.md` para cuál familia corresponde a cada CAL-1/2/3). Es la
mutación preferida cuando el historial de operadores muestra progreso
consistente en una dirección (el gap subió en los últimos 2-3 intentos con el
mismo tipo de cambio): en vez de un micro-ajuste, da un paso más grande en la
misma dirección.

Efecto sobre invariantes: depende de la familia objetivo, pero el punto del
operador es que YA sabes el efecto porque la familia es conocida — por
ejemplo, moverse hacia "estrella pura" baja `μ` a 1 y sube `λ₁` como
`√(n-1)` (bueno para CAL-1); moverse hacia "dos estrellas unidas" sube `λ₂`
manteniendo `Hc` bajo (bueno para CAL-2).

Riesgo de romper validez: bajo SI el parámetro ya está acotado por el
programa (el patrón `NIVEL`/`min(nivel, 4)` del TOY, por ejemplo, ya clampa
internamente). Si el parámetro no está acotado, verifica que el nuevo valor
no dispare `n` fuera de `[3, 300]` ni produzca un grafo con `n` calculado mal.

## Mini-ejemplo SEARCH/REPLACE

Subir un nivel de densificación (patrón genérico tipo TOY):

```
<<<<<<< SEARCH
NIVEL = 1
=======
NIVEL = 2
>>>>>>> REPLACE
```

Cambiar la familia base completa de un programa parametrizado por nombre
(cuando el programa expone un selector de familia, no solo un nivel numérico):

```
<<<<<<< SEARCH
FAMILIA = "camino"
=======
FAMILIA = "dos_estrellas"
>>>>>>> REPLACE
```

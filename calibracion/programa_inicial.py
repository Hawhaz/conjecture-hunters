# Programa inicial de la vertical CAL-1: imprime las aristas de un COMETA
# (estrella + cola), una de las familias donde históricamente caen estas
# conjeturas (§9). El LLM muta los parámetros/estructura dentro del bloque.
# EVOLVE-BLOCK-START
HOJAS = 12      # hojas de la estrella (centro = vértice 0)
LARGO_COLA = 6  # largo del camino colgado del centro
# EVOLVE-BLOCK-END

aristas = []
for h in range(1, HOJAS + 1):
    aristas.append((0, h))
previo = 0
for k in range(LARGO_COLA):
    nuevo = HOJAS + 1 + k
    aristas.append((previo, nuevo))
    previo = nuevo

for u, v in aristas:
    print(u, v)

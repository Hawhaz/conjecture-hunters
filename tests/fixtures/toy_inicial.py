# TOY (§8): grafo conexo, n = 20, grado maximo <= 3, maximizar aristas.
# Optimo = 30 (3-regular con 20 vertices). Fitness = m si es valido, -1e9 si no.
# EVOLVE-BLOCK-START
NIVEL = 0
# EVOLVE-BLOCK-END

N = 20


def construir(nivel):
    if nivel <= 0:
        return [(i, i + 1) for i in range(N - 1)]  # camino P20: 19 aristas
    aristas = [(i, (i + 1) % N) for i in range(N)]  # ciclo C20: 20 aristas
    cuerdas = {1: 0, 2: 5, 3: 8, 4: 10}.get(min(nivel, 4), 10)
    aristas += [(i, i + 10) for i in range(cuerdas)]  # diagonales i <-> i+10
    return aristas


for u, v in construir(NIVEL):
    print(u, v)

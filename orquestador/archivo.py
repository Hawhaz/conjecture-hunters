#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archivo MAP-Elites + Islas (FunSearch + AlphaEvolve + MAP-Elites, decision 3).

- Una ISLA es un archivo MAP-Elites: un diccionario celda -> elite, donde la
  celda = (n_bin, density_bin) (descriptores ORTOGONALES al fitness; NO usan
  matching ni eigenvalores, decision 3) y el elite de una celda es el grafo de
  MAYOR gap visto en esa celda. Ademas mantiene un set de hashes WL para el
  rechazo por novedad (decision 6, ShinkaEvolve).
- Un ARCHIPIELAGO tiene `--islas` islas (def 5). Cada R generaciones hace un
  hard-reset de la peor mitad de islas, resembrando cada una desde el mejor
  individuo de una isla superviviente (decision 3).

El fitness que ordena TODO es el gap continuo (decision 2). El shaping opcional
de CAL-3 (decision 9) entra SOLO como desempate secundario y jamas cambia el
gap real ni la clasificacion de contraejemplo (esa la decide T3).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

from . import grafos as G

Celda = Tuple[int, int]


@dataclass
class Elite:
    """Un individuo elite en una celda del archivo."""
    g6: str
    gap: float
    celda: Celda
    n: int
    densidad: float
    wl: str
    n_offspring: int = 0  # cuantas veces se uso como padre (para novelty weight)
    shaping: float = 0.0  # termino secundario CAL-3 (tie-break); 0 por defecto

    def clave_orden(self) -> Tuple[float, float]:
        """Orden lexicografico: primero gap REAL, luego shaping (desempate)."""
        return (self.gap, self.shaping)


class Isla:
    """Un archivo MAP-Elites (una isla del archipielago)."""

    def __init__(self, idx: int):
        self.idx = idx
        self.celdas: Dict[Celda, Elite] = {}
        self.hashes: set = set()  # WL hashes presentes (novelty)

    # ---- consultas ---------------------------------------------------------
    def __len__(self) -> int:
        return len(self.celdas)

    def elites(self) -> List[Elite]:
        return list(self.celdas.values())

    def mejor(self) -> Optional[Elite]:
        """Elite de mayor (gap, shaping) de toda la isla."""
        if not self.celdas:
            return None
        return max(self.celdas.values(), key=lambda e: e.clave_orden())

    def mejor_gap(self) -> float:
        m = self.mejor()
        return m.gap if m is not None else float("-inf")

    def contiene_hash(self, wl: str) -> bool:
        return wl in self.hashes

    # ---- insercion ---------------------------------------------------------
    def insertar(self, g6: str, gap: float, shaping: float = 0.0) -> str:
        """Intenta colocar un individuo. Devuelve el EVENTO de frontera:

            "nueva_celda"  : ocupo una celda vacia (avance de frontera)
            "mejora_celda" : supero el elite de su celda (avance de frontera)
            "sin_mejora"   : no mejoro su celda (no avanza)
            "duplicado"    : su hash WL ya estaba en la isla (rechazado)

        Los eventos "nueva_celda"/"mejora_celda" son los que dan reward=1 al
        bandit (decision 4). El grafo se decodifica de g6 para descriptores.
        """
        try:
            graf = G.from_g6(g6)
        except Exception:
            return "sin_mejora"
        wl = G.wl_hash(graf)
        if wl in self.hashes:
            return "duplicado"
        cel = G.celda(graf)
        n = graf.number_of_nodes()
        dens = G.densidad(graf)
        nuevo = Elite(g6=g6, gap=gap, celda=cel, n=n, densidad=dens, wl=wl,
                      shaping=shaping)
        actual = self.celdas.get(cel)
        if actual is None:
            self.celdas[cel] = nuevo
            self.hashes.add(wl)
            return "nueva_celda"
        if nuevo.clave_orden() > actual.clave_orden():
            # sustituye el elite; el hash viejo puede seguir presente en otra
            # celda, pero al menos deja de bloquear esta. Registramos el nuevo.
            self.celdas[cel] = nuevo
            self.hashes.add(wl)
            return "mejora_celda"
        # no mejora, pero SI registramos su hash para no reintentar el duplicado
        self.hashes.add(wl)
        return "sin_mejora"

    def marcar_padre(self, g6: str) -> None:
        """Incrementa n_offspring del elite cuyo g6 coincida (novelty weight)."""
        for e in self.celdas.values():
            if e.g6 == g6:
                e.n_offspring += 1
                return

    # ---- reset -------------------------------------------------------------
    def reset_desde(self, semilla: Elite) -> None:
        """Vacia la isla y la resiembra con un unico elite (hard-reset)."""
        self.celdas.clear()
        self.hashes.clear()
        clon = Elite(g6=semilla.g6, gap=semilla.gap, celda=semilla.celda,
                     n=semilla.n, densidad=semilla.densidad, wl=semilla.wl)
        self.celdas[clon.celda] = clon
        self.hashes.add(clon.wl)


class Archipielago:
    """Coleccion de islas con hard-reset periodico de la peor mitad."""

    def __init__(self, n_islas: int = 5, reset_cada: int = 40):
        self.islas: List[Isla] = [Isla(i) for i in range(n_islas)]
        self.reset_cada = reset_cada

    def __len__(self) -> int:
        return len(self.islas)

    def total_celdas(self) -> int:
        return sum(len(i) for i in self.islas)

    def mejor_global(self) -> Optional[Elite]:
        cands = [i.mejor() for i in self.islas if i.mejor() is not None]
        if not cands:
            return None
        return max(cands, key=lambda e: e.clave_orden())

    def mejor_gap_global(self) -> float:
        m = self.mejor_global()
        return m.gap if m is not None else float("-inf")

    def sembrar(self, g6s_gaps: List[Tuple[str, float]]) -> None:
        """Distribuye semillas iniciales round-robin entre las islas."""
        for k, (g6, gap) in enumerate(g6s_gaps):
            self.islas[k % len(self.islas)].insertar(g6, gap)

    def reset_peor_mitad(self, rng) -> int:
        """Hard-reset de la peor mitad de islas (por mejor_gap), resembrando

        cada una desde el best de una isla SUPERVIVIENTE elegida al azar
        (decision 3). Devuelve cuantas islas se reiniciaron. No hace nada si
        hay <2 islas o ninguna superviviente con elite.
        """
        if len(self.islas) < 2:
            return 0
        ordenadas = sorted(self.islas, key=lambda i: i.mejor_gap())
        k = len(ordenadas) // 2
        peores = ordenadas[:k]
        supervivientes = [i for i in ordenadas[k:] if i.mejor() is not None]
        if not supervivientes:
            return 0
        reiniciadas = 0
        for isla in peores:
            fuente = supervivientes[rng.randrange(len(supervivientes))]
            best = fuente.mejor()
            if best is not None:
                isla.reset_desde(best)
                reiniciadas += 1
        return reiniciadas

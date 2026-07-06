#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bandit Discounted Thompson Sampling (Beta-Bernoulli, decision 4).

Arms = (conjetura x operador). En cada paso:
  1. Descuenta S_i, F_i por gamma (olvido exponencial: los aciertos viejos pesan
     menos, el bandit se adapta si el paisaje cambia tras un reset de islas).
  2. Muestrea theta_i ~ Beta(S_i+1, F_i+1) para cada arm.
  3. Tira el arm de mayor theta (argmax).
  4. Recompensa 1 si la mutacion AVANZO la frontera de esa isla (celda nueva o
     mayor gap), 0 si no. Actualiza S_i o F_i del arm tirado.

Determinista dado el rng (random.Random sembrado): reproducible en CI.
El muestreo Beta se hace con dos Gamma via el rng estandar (no numpy) para
mantener el mock 100% reproducible con la misma semilla en cualquier plataforma.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

Arm = Tuple[str, str]  # (conjetura, operador)


def _muestra_beta(rng, alpha: float, beta: float) -> float:
    """Beta(alpha,beta) via dos Gamma con el rng de la stdlib (reproducible).

    random.Random.gammavariate esta disponible y es determinista dada la
    semilla. Beta(a,b) = X/(X+Y), X~Gamma(a,1), Y~Gamma(b,1).
    """
    x = rng.gammavariate(alpha, 1.0)
    y = rng.gammavariate(beta, 1.0)
    if x + y <= 0.0:
        return 0.5
    return x / (x + y)


@dataclass
class Bandit:
    """Bandit Thompson descontado sobre arms (conjetura x operador).

    Parametros
    ----------
    conjeturas : lista de conjeturas activas (p.ej. ["cal1"]).
    operadores : lista de operadores activos (depende de --trees-only).
    gamma : factor de descuento (def 0.99).
    """
    conjeturas: List[str]
    operadores: List[str]
    gamma: float = 0.99
    S: Dict[Arm, float] = field(default_factory=dict)
    F: Dict[Arm, float] = field(default_factory=dict)

    def __post_init__(self):
        for c in self.conjeturas:
            for op in self.operadores:
                self.S.setdefault((c, op), 0.0)
                self.F.setdefault((c, op), 0.0)

    def arms(self) -> List[Arm]:
        return list(self.S.keys())

    def _descontar(self) -> None:
        """Aplica el olvido exponencial a TODOS los arms (paso 1)."""
        for a in self.S:
            self.S[a] *= self.gamma
            self.F[a] *= self.gamma

    def seleccionar(self, rng, conj: str = None) -> Arm:
        """Descuenta, muestrea theta~Beta(S+1,F+1) y devuelve el argmax.

        Si `conj` se pasa, restringe la seleccion a los arms de esa conjetura
        (el loop procesa una conjetura por turno). Determinista dado rng.
        """
        self._descontar()
        candidatos = [a for a in self.S
                      if conj is None or a[0] == conj]
        if not candidatos:
            candidatos = list(self.S.keys())
        mejor_arm = candidatos[0]
        mejor_theta = -1.0
        for a in candidatos:
            theta = _muestra_beta(rng, self.S[a] + 1.0, self.F[a] + 1.0)
            if theta > mejor_theta:
                mejor_theta = theta
                mejor_arm = a
        return mejor_arm

    def actualizar(self, arm: Arm, recompensa: int) -> None:
        """Registra el resultado del arm tirado (paso 4).

        recompensa == 1 -> S[arm]+=1 ; else F[arm]+=1.
        """
        if arm not in self.S:
            self.S[arm] = 0.0
            self.F[arm] = 0.0
        if recompensa >= 1:
            self.S[arm] += 1.0
        else:
            self.F[arm] += 1.0

    def media_posterior(self, arm: Arm) -> float:
        """(S+1)/(S+F+2): media de la Beta posterior (para logging/inspeccion)."""
        s = self.S.get(arm, 0.0)
        f = self.F.get(arm, 0.0)
        return (s + 1.0) / (s + f + 2.0)

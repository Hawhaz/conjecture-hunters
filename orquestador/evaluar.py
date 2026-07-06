#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capa T2 de la cascada de evaluacion (AlphaEvolve, decision 1).

Evalua un LOTE de grafos y devuelve el gap CONTINUO (+gap = margen de violacion,
decision 2) para la conjetura objetivo. gap>0  <=>  candidato a contraejemplo.

Backend primario: el binario Rust `buscador_rs/target/release/buscador_rs.exe`
via subprocess (`evaluar --eval cal1|cal2|cal3`), que evalua el lote COMPLETO en
paralelo (~10k evals/seg) y emite CSV `g6,n,gap,contraejemplo`. Un unico proceso
por lote (no por grafo): se le pasan todos los g6 por --corpus (archivo temporal)
o por stdin.

Backend de reserva: `parity/refs.py` (cal1/cal2/cal3 en Python puro sobre
networkx/numpy/scipy). Se usa si el binario Rust no existe / no arranca / no es
ejecutable en esta plataforma (p. ej. el .exe de Windows en un runner Linux, o
CI sin haber compilado). El fallback da EXACTAMENTE el mismo gap que el oraculo
(es literalmente el oraculo), asi la cascada nunca se cae por falta del binario.

IMPORTANTE: T2 NUNCA es el veredicto final. Solo prioriza candidatos. El
contraejemplo solo se "encuentra" cuando T3 (`certificar.py`) lo certifica.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence

import networkx as nx

from . import grafos as G

# Raiz del repo (para importar parity.refs y localizar el binario Rust).
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# Fallback Python: el propio oraculo. cal1/cal2/cal3 devuelven tuplas cuyo
# ULTIMO elemento es el gap.
from parity.refs import cal1 as _ref_cal1  # noqa: E402
from parity.refs import cal2 as _ref_cal2  # noqa: E402
from parity.refs import cal3 as _ref_cal3  # noqa: E402

_REFS = {"cal1": _ref_cal1, "cal2": _ref_cal2, "cal3": _ref_cal3}

TOL_POSITIVO = 1e-9  # gap>TOL  <=>  candidato (igual que ga_graphs / Rust)


def ruta_binario() -> str:
    """Ruta por defecto del binario Rust dentro del repo."""
    return os.path.join(_RAIZ, "buscador_rs", "target", "release", "buscador_rs.exe")


class Evaluador:
    """Evaluador de lote con backend Rust + fallback Python-refs.

    Parametros
    ----------
    conj : "cal1" | "cal2" | "cal3"
    binario : ruta al buscador_rs.exe (por defecto la del repo).
    forzar_python : si True, ignora el binario y usa siempre el oraculo Python
        (util para tests deterministas independientes de la plataforma).
    """

    def __init__(self, conj: str, binario: Optional[str] = None,
                 forzar_python: bool = False, umbral: float = TOL_POSITIVO):
        conj = conj.lower().strip()
        if conj not in _REFS:
            raise ValueError("conj debe ser cal1|cal2|cal3; llego %r" % conj)
        self.conj = conj
        self.umbral = umbral
        self.binario = binario or ruta_binario()
        self.forzar_python = forzar_python
        self._rust_ok: Optional[bool] = None  # cache de disponibilidad
        self.backend_usado = None  # "rust" | "python" (ultimo lote)

    # ---- disponibilidad del binario ---------------------------------------
    def rust_disponible(self) -> bool:
        """True si el binario existe y arranca en esta plataforma (cacheado)."""
        if self.forzar_python:
            return False
        if self._rust_ok is not None:
            return self._rust_ok
        ok = False
        if os.path.isfile(self.binario):
            try:
                # Sonda barata: evalua un solo g6 trivial por stdin.
                sonda = nx.to_graph6_bytes(
                    nx.path_graph(3), header=False).decode("ascii").strip()
                r = subprocess.run(
                    [self.binario, "evaluar", "--eval", self.conj],
                    input=sonda + "\n", capture_output=True, text=True,
                    timeout=30,
                )
                ok = (r.returncode == 0 and "g6,n,gap,contraejemplo" in r.stdout)
            except Exception:
                ok = False
        self._rust_ok = ok
        return ok

    # ---- evaluacion de lote -----------------------------------------------
    def evaluar(self, g6s: Sequence[str]) -> Dict[str, float]:
        """Evalua un lote de g6 y devuelve {g6: gap}. Lote completo de una vez.

        Preserva el g6 EXACTO de entrada como clave (asumiendo que ya viene
        normalizado por grafos.g6_of, como en todo el orquestador). Ignora g6
        invalidos (no apareceran en el dict resultante).
        """
        g6s = [s.strip() for s in g6s if s and s.strip()]
        if not g6s:
            self.backend_usado = None
            return {}
        if self.rust_disponible():
            try:
                out = self._evaluar_rust(g6s)
                self.backend_usado = "rust"
                # Rellena cualquier g6 que el Rust no devolvio, via fallback.
                faltan = [s for s in g6s if s not in out]
                if faltan:
                    out.update(self._evaluar_python(faltan))
                return out
            except Exception:
                pass  # cae al fallback Python
        self.backend_usado = "python"
        return self._evaluar_python(g6s)

    def gap(self, g6: str) -> float:
        """Gap de un unico g6 (conveniencia; internamente lote de tamano 1)."""
        d = self.evaluar([g6])
        return d.get(g6, float("-inf"))

    def es_candidato(self, gap: float) -> bool:
        """gap>umbral  <=>  candidato a contraejemplo (a pasar a T3)."""
        return gap > self.umbral

    # ---- backends internos -------------------------------------------------
    def _evaluar_rust(self, g6s: Sequence[str]) -> Dict[str, float]:
        """Invoca el binario Rust con --corpus (archivo temporal) sobre el lote."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".g6", delete=False, encoding="ascii")
        try:
            tmp.write("\n".join(g6s) + "\n")
            tmp.close()
            r = subprocess.run(
                [self.binario, "evaluar", "--eval", self.conj,
                 "--corpus", tmp.name, "--umbral", repr(self.umbral)],
                capture_output=True, text=True, timeout=600,
            )
            if r.returncode != 0:
                raise RuntimeError("buscador_rs evaluar rc=%d: %s"
                                   % (r.returncode, r.stderr[:400]))
            return self._parsear_csv(r.stdout)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    @staticmethod
    def _parsear_csv(salida: str) -> Dict[str, float]:
        """Parsea el CSV `g6,n,gap,contraejemplo` del binario Rust."""
        out: Dict[str, float] = {}
        for linea in salida.splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("g6,n,gap"):
                continue
            # g6 puede contener comas? No: graph6 usa ASCII 63..126 salvo coma?
            # graph6 alphabet es 63..126 e INCLUYE ','(44)? No: 44<63, seguro.
            partes = linea.split(",")
            if len(partes) < 3:
                continue
            g6 = partes[0]
            try:
                gap = float(partes[2])
            except ValueError:
                continue
            out[g6] = gap
        return out

    def _evaluar_python(self, g6s: Sequence[str]) -> Dict[str, float]:
        """Fallback: gap via oraculo parity.refs (identico al Rust por contrato)."""
        f = _REFS[self.conj]
        out: Dict[str, float] = {}
        for s in g6s:
            try:
                graf = G.from_g6(s)
                res = f(graf)
                out[s] = float(res[-1])  # ultimo elemento de la tupla = gap
            except Exception:
                continue
        return out


def evaluar_lote(conj: str, g6s: Sequence[str],
                 binario: Optional[str] = None,
                 forzar_python: bool = False) -> Dict[str, float]:
    """Atajo funcional: crea un Evaluador y evalua el lote."""
    return Evaluador(conj, binario=binario,
                     forzar_python=forzar_python).evaluar(g6s)

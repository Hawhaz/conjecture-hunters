#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capa T3 de la cascada: la compuerta EXACTA e IN-GAMEABLE (decision 1).

Envuelve `certificados/verify.certificar(g6, conj)` — la unica autoridad que
convierte un candidato (gap f64>0 del Rust) en TEOREMA (gap>0 demostrado con
aritmetica exacta / intervalos rigurosos). Es lenta (charpoly sympy hasta n=40,
mpmath+residual arriba): por eso el orquestador la corre SOLO sobre candidatos
con gap>1e-9 de T2, nunca sobre todo el lote.

Un contraejemplo NO se declara "encontrado" hasta que esta capa devuelve
certificado=True. Es la defensa documentada contra reward-hacking: el gap
rapido puede mentir (ruido de eigvalsh, un evaluador manipulado); el
certificado no. Ver DISENO.md (decision 1) y certificados/verify.py.
"""
from __future__ import annotations

import os
import sys
from typing import Optional

# Anade el directorio certificados/ a sys.path (contrato del enunciado) y la
# raiz del repo (verify.py tambien reusa convenciones del repo).
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CERT_DIR = os.path.join(_RAIZ, "certificados")
for _p in (_RAIZ, _CERT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from verify import certificar as _certificar_verify  # noqa: E402


def certificar(g6: str, conj: str) -> dict:
    """Certifica RIGUROSAMENTE gap(G)>0 para `g6` y la conjetura `conj`.

    Delega 1:1 en `certificados/verify.certificar`. Devuelve su dict:
        {"certificado": bool, "metodo": str, "margen": str, "detalle": dict,
         "conj": str, "g6": str, "n": int|None}
    Nunca lanza por un g6 valido (errores estructurales -> certificado False).
    """
    return _certificar_verify(g6, conj)


def es_contraejemplo(g6: str, conj: str) -> bool:
    """True SOLO si el certificado exacto demuestra gap>0 (veredicto final)."""
    return bool(certificar(g6, conj).get("certificado", False))

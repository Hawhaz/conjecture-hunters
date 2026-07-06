#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capa de mutacion: dos backends tras UNA interfaz (decision 7).

- `mock` (DETERMINISTA, la ruta testeada en CI, sin red): aplica el operador
  estructural elegido por el bandit a un elite muestreado. rng sembrado ->
  reproducible. Es la ruta por defecto y la unica que corre en CI.

- `ollama` (opt-in): llama a gemma3:4b en http://localhost:11434/v1 (mismo
  transporte urllib que prompts/ollama_cliente.py). El prompt es un few-shot
  RANQUEADO de k=3 elites descritos como LISTAS DE ARISTAS, ordenados de peor a
  mejor, con el fitness transmitido como RANGO ORDINAL (NO floats crudos: un
  modelo 4B no razona sobre floats). Pide un DELTA de lista de aristas
  ("add edge (u,v); remove edge (x,y)"), que se aplica DETERMINISTAMENTE en
  codigo, best-of-N=4, validando que cada intento decodifique a un grafo conexo
  legal. Si Ollama no responde, cae a `mock` (nunca crashea).

Interfaz comun:
    Mutador(backend, ...).mutar(elite_g6, arm, isla, rng) -> (g6_hijo|None, meta)
donde `arm=(conj,op)` viene del bandit e `isla` da el pool de elites para el
few-shot LLM. meta es un dict con {"backend","op","detalle"} para logging.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

import networkx as nx

from . import grafos as G

Arm = Tuple[str, str]


# ---------------------------------------------------------------------------
# Descripcion de un grafo como lista de aristas (para el prompt LLM).
# ---------------------------------------------------------------------------
def a_lista_aristas(g6: str) -> str:
    """'(u,v) (u,w) ...' aristas del grafo normalizado, orden estable."""
    graf = G.from_g6(g6)
    return " ".join("(%d,%d)" % (u, v) for u, v in sorted(graf.edges()))


_RE_ARISTA = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)")


def _parsear_delta(texto: str) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """Extrae (agregar, quitar) de un texto tipo 'add edge (u,v); remove (x,y)'.

    Heuristica robusta: parte el texto por lineas/;, y para cada fragmento mira
    si contiene 'remove'/'delete'/'quita' -> quitar, si 'add'/'agrega' -> agregar.
    Un par (u,v) sin verbo se asume 'add'. Tolerante a ruido del modelo 4B.
    """
    agregar: List[Tuple[int, int]] = []
    quitar: List[Tuple[int, int]] = []
    for frag in re.split(r"[;\n]", texto):
        pares = _RE_ARISTA.findall(frag)
        if not pares:
            continue
        low = frag.lower()
        es_quitar = any(k in low for k in ("remove", "delete", "quita", "quitar", "borra"))
        for (a, b) in pares:
            par = (int(a), int(b))
            if es_quitar:
                quitar.append(par)
            else:
                agregar.append(par)
    return agregar, quitar


# ---------------------------------------------------------------------------
# Interfaz de mutacion
# ---------------------------------------------------------------------------
class Mutador:
    def __init__(self, backend: str = "mock",
                 trees_only: bool = False,
                 api_base: str = "http://localhost:11434/v1",
                 model: str = "gemma3:4b",
                 api_key: str = "ollama",
                 n_llm: int = 4,
                 k_fewshot: int = 3,
                 timeout_s: float = 60.0):
        self.backend = backend.lower().strip()
        self.trees_only = trees_only
        self.api_base = api_base
        self.model = model
        self.api_key = api_key
        self.n_llm = n_llm
        self.k_fewshot = k_fewshot
        self.timeout_s = timeout_s
        self._ollama_vivo: Optional[bool] = None

    # ---- API principal -----------------------------------------------------
    def mutar(self, elite_g6: str, arm: Arm, isla, rng) -> Tuple[Optional[str], dict]:
        """Produce un hijo (g6) a partir del elite. Devuelve (g6|None, meta).

        Con backend 'ollama' intenta el LLM; si esta caido o no produce grafo
        conexo valido, cae a 'mock' (mismo operador del arm). Nunca lanza.
        """
        conj, op = arm
        if self.backend == "ollama":
            g6, meta = self._mutar_ollama(elite_g6, arm, isla, rng)
            if g6 is not None:
                return g6, meta
            # fallback a mock (documentado, decision 7): jamas crashea
            g6m, metam = self._mutar_mock(elite_g6, arm, rng)
            metam["detalle"] = "ollama_fallback->mock; " + meta.get("detalle", "")
            return g6m, metam
        return self._mutar_mock(elite_g6, arm, rng)

    # ---- backend mock ------------------------------------------------------
    def _mutar_mock(self, elite_g6: str, arm: Arm, rng) -> Tuple[Optional[str], dict]:
        conj, op = arm
        graf = G.from_g6(elite_g6)
        hijo = G.aplicar_operador(op, graf, rng)
        meta = {"backend": "mock", "op": op, "detalle": ""}
        if hijo is None:
            meta["detalle"] = "op_no_aplica"
            return None, meta
        # En modo conexo requerimos conectividad; los ops de arbol ya la
        # preservan. add_edge tambien (agrega, no quita).
        if not G.valido(hijo, requiere_conexo=True):
            meta["detalle"] = "hijo_invalido"
            return None, meta
        return G.g6_of(hijo), meta

    # ---- backend ollama ----------------------------------------------------
    def _ollama_disponible(self) -> bool:
        if self._ollama_vivo is not None:
            return self._ollama_vivo
        try:
            req = urllib.request.Request(
                self.api_base.rstrip("/").rsplit("/v1", 1)[0] + "/api/tags",
                method="GET")
            with urllib.request.urlopen(req, timeout=3.0):
                self._ollama_vivo = True
        except Exception:
            # sonda alternativa: intentar /v1/models
            try:
                req = urllib.request.Request(
                    self.api_base.rstrip("/") + "/models", method="GET")
                with urllib.request.urlopen(req, timeout=3.0):
                    self._ollama_vivo = True
            except Exception:
                self._ollama_vivo = False
        return self._ollama_vivo

    def _construir_prompt(self, elite_g6: str, isla, conj: str) -> Tuple[str, str]:
        """few-shot ranqueado (peor->mejor) como listas de aristas, rango ORDINAL."""
        elites = sorted(isla.elites(), key=lambda e: e.gap)  # peor->mejor
        pool = elites[-self.k_fewshot:] if elites else []
        # asegura que el elite objetivo este presente
        if all(e.g6 != elite_g6 for e in pool):
            pool = (pool + [next((e for e in elites if e.g6 == elite_g6), None)])
            pool = [e for e in pool if e is not None][-self.k_fewshot:]
        lineas = []
        for rango, e in enumerate(pool, start=1):
            lineas.append("RANK %d (worse..better), n=%d, edges: %s"
                          % (rango, e.n, a_lista_aristas(e.g6)))
        system = (
            "You are a graph mutation operator hunting counterexamples to a "
            "spectral graph conjecture. You are given a few connected graphs as "
            "EDGE LISTS, ordered by ordinal RANK from worse to better (higher "
            "rank = closer to a counterexample). Propose a SMALL structural "
            "change to the BEST (highest-rank) graph that plausibly increases "
            "its rank. Reply with ONLY an edge-list delta, e.g.:\n"
            "add edge (0,7); remove edge (3,4)\n"
            "Use existing vertex ids; to add ONE new leaf vertex use id = n "
            "(the next integer). Keep the graph connected. No prose."
        )
        user = (
            "Conjecture: %s. Candidates (worse to better):\n%s\n\n"
            "Best graph is the last one. Give an edge-list delta that likely "
            "raises its rank. Answer with the delta only."
            % (conj.upper(), "\n".join(lineas))
        )
        return system, user

    def _llamar_llm(self, system: str, user: str) -> Optional[str]:
        cuerpo = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.8,
            "stream": False,
        }).encode("utf-8")
        url = self.api_base.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(
            url, data=cuerpo,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % self.api_key},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                crudo = resp.read().decode("utf-8", errors="replace")
            return json.loads(crudo)["choices"][0]["message"]["content"]
        except Exception:
            return None

    def _mutar_ollama(self, elite_g6: str, arm: Arm, isla, rng
                      ) -> Tuple[Optional[str], dict]:
        conj, op = arm
        meta = {"backend": "ollama", "op": "llm-delta", "detalle": ""}
        if not self._ollama_disponible():
            meta["detalle"] = "ollama_inalcanzable"
            return None, meta
        system, user = self._construir_prompt(elite_g6, isla, conj)
        base = G.from_g6(elite_g6)
        # best-of-N: intenta N deltas, aplica cada uno, valida conectividad.
        for _ in range(self.n_llm):
            texto = self._llamar_llm(system, user)
            if not texto:
                continue
            agregar, quitar = _parsear_delta(texto)
            if not agregar and not quitar:
                continue
            try:
                hijo = G.aplicar_delta(base, agregar=agregar, quitar=quitar)
            except Exception:
                continue
            if G.valido(hijo, requiere_conexo=True):
                meta["detalle"] = "delta:+%d/-%d" % (len(agregar), len(quitar))
                return G.g6_of(hijo), meta
        meta["detalle"] = "sin_delta_valido_en_%dN" % self.n_llm
        return None, meta

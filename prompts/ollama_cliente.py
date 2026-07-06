#!/usr/bin/env python3
"""Cliente minimalista (solo stdlib) para el operador de mutación LLM.

Arma el mensaje system+user desde las plantillas .md de este mismo directorio
(`system_mutador.md`, `plantilla_usuario.md`, `banco_conjeturas.md`) y llama a
un endpoint OpenAI-compatible (`POST {api_base}/chat/completions`) usando
SOLO `urllib` — sin `requests`, sin SDK de OpenAI, sin dependencias extra.
Hoy apunta a Ollama local (gemma3:4b); mañana a Fireworks/vLLM cambiando
ÚNICAMENTE `api_base` (y `api_key` si el proveedor lo exige) — ver README.md.

Uso como librería:

    from prompts.ollama_cliente import mutar
    diff_texto = mutar(programa, conjetura, gap, n)

Uso como script (humo sin gastar tokens ni requerir Ollama arriba):

    python prompts/ollama_cliente.py --dry-run
    python prompts/ollama_cliente.py --dry-run --historial "add_leaf: gap -0.4 -> -0.3"
    python prompts/ollama_cliente.py   # llamada real contra Ollama en localhost:11434
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DIR_PROMPTS = os.path.dirname(os.path.abspath(__file__))

RUTA_SYSTEM = os.path.join(DIR_PROMPTS, "system_mutador.md")
RUTA_USUARIO = os.path.join(DIR_PROMPTS, "plantilla_usuario.md")
RUTA_BANCO = os.path.join(DIR_PROMPTS, "banco_conjeturas.md")

SIN_HISTORIAL = "(sin historial todavía — esta es la primera mutación de esta corrida)"


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def cargar_system():
    """Prompt de sistema tal cual (sin placeholders) — ver system_mutador.md."""
    return _leer(RUTA_SYSTEM)


def cargar_plantilla_usuario():
    """Cuerpo renderizable de plantilla_usuario.md, con sus placeholders {…} intactos.

    plantilla_usuario.md trae un encabezado de documentación (para quien lo
    lea directamente en el editor) que MENCIONA los nombres de los
    placeholders entre backticks — p. ej. `{conjetura}` — antes del primer
    separador `---`. Si esas menciones se dejaran dentro del texto que se
    renderiza, un reemplazo literal de `{conjetura}` las sustituiría también
    a ELLAS (falso positivo), corrompiendo la nota explicativa. Por eso acá
    se descarta todo hasta el primer `---` inclusive: solo el cuerpo debajo
    de esa línea es la plantilla real que se le manda al modelo.
    """
    completo = _leer(RUTA_USUARIO)
    marcador = "\n---\n"
    idx = completo.find(marcador)
    if idx == -1:
        return completo  # sin separador: no hay encabezado que descartar
    return completo[idx + len(marcador):]


def cargar_banco_conjeturas():
    """Texto completo de banco_conjeturas.md, por si se quiere citar entero."""
    return _leer(RUTA_BANCO)


def render_usuario(programa: str, conjetura: str, gap: float, n: int,
                    historial_operadores: str = None) -> str:
    """Rellena plantilla_usuario.md con los 5 placeholders del contrato.

    Placeholders: {conjetura} {gap_actual} {n_actual} {programa_actual}
    {historial_operadores}. El programa se pega tal cual (no se re-escapan
    llaves internas: usamos reemplazo de marcador único en vez de
    str.format() para no chocar con las llaves de listas/dicts/f-strings
    que el programa Python mutado pueda contener).
    """
    plantilla = cargar_plantilla_usuario()
    historial = historial_operadores if historial_operadores else SIN_HISTORIAL

    # Reemplazo por marcador literal (NO str.format): el {programa_actual} de
    # un programa Python real casi siempre trae llaves propias ({}, dicts,
    # f-strings) que romperían un .format() ingenuo con KeyError/IndexError.
    texto = plantilla
    texto = texto.replace("{conjetura}", conjetura)
    texto = texto.replace("{gap_actual}", _fmt_gap(gap))
    texto = texto.replace("{n_actual}", str(n))
    texto = texto.replace("{historial_operadores}", historial)
    texto = texto.replace("{programa_actual}", programa)
    return texto


def _fmt_gap(gap: float) -> str:
    try:
        return f"{float(gap):.10f}"
    except (TypeError, ValueError):
        return str(gap)


def _payload(system_msg: str, user_msg: str, model: str, temperature: float) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": temperature,
        "stream": False,
    }


def mutar(programa: str, conjetura: str, gap: float, n: int,
          api_base: str = "http://localhost:11434/v1",
          model: str = "gemma3:4b",
          historial_operadores: str = None,
          temperature: float = 0.7,
          timeout_s: float = 600.0,
          api_key: str = "ollama") -> str:
    """Llama a `{api_base}/chat/completions` y devuelve el diff crudo del modelo.

    Contrato de retorno: el texto tal cual de `choices[0].message.content`
    (se espera que sean bloques SEARCH/REPLACE puros, por el prompt de
    sistema — este cliente NO parsea ni valida el diff, esa responsabilidad
    es de OpenEvolve / del aplicador de parches).

    Cambiar de proveedor (Ollama → Fireworks/vLLM) es SOLO cambiar
    `api_base` (y `api_key` si el proveedor la exige vía Bearer token);
    nada más en esta función cambia.
    """
    system_msg = cargar_system()
    user_msg = render_usuario(programa, conjetura, gap, n, historial_operadores)
    cuerpo = json.dumps(_payload(system_msg, user_msg, model, temperature)).encode("utf-8")

    url = api_base.rstrip("/") + "/chat/completions"
    cabeceras = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        crudo = resp.read().decode("utf-8", errors="replace")
    respuesta = json.loads(crudo)
    return respuesta["choices"][0]["message"]["content"]


# ------------------------------------------------------------------ CLI / dry-run

def _programa_ejemplo():
    """Mismo contenido que calibracion/programa_inicial.py, embebido para que
    el --dry-run funcione sin depender de rutas fuera de prompts/."""
    return (
        "# Programa inicial de la vertical CAL-1: imprime las aristas de un COMETA\n"
        "# (estrella + cola), una de las familias donde historicamente caen estas\n"
        "# conjeturas (Sec 9). El LLM muta los parametros/estructura dentro del bloque.\n"
        "# EVOLVE-BLOCK-START\n"
        "HOJAS = 12      # hojas de la estrella (centro = vertice 0)\n"
        "LARGO_COLA = 6  # largo del camino colgado del centro\n"
        "# EVOLVE-BLOCK-END\n"
        "\n"
        "aristas = []\n"
        "for h in range(1, HOJAS + 1):\n"
        "    aristas.append((0, h))\n"
        "previo = 0\n"
        "for k in range(LARGO_COLA):\n"
        "    nuevo = HOJAS + 1 + k\n"
        "    aristas.append((previo, nuevo))\n"
        "    previo = nuevo\n"
        "\n"
        "for u, v in aristas:\n"
        "    print(u, v)\n"
    )


def _conjetura_cal1():
    return (
        "CAL-1 · lambda_1 + mu >= sqrt(n-1) + 1 (AutoGraphiX / Aouchiche-Hansen).\n"
        "gap(G) = (sqrt(n-1) + 1) - (lambda_1 + mu); gap > 0 equivale a contraejemplo.\n"
        "Ver banco_conjeturas.md para las pistas completas de esta conjetura."
    )


def _dry_run(args):
    """Renderiza el prompt completo SIN llamar a la red y lo imprime.

    Debe funcionar SIEMPRE, incluso con Ollama caido: es exactamente el modo
    que exige el smoke-test del README (python prompts/ollama_cliente.py
    --dry-run).
    """
    programa = args.programa if args.programa else _programa_ejemplo()
    conjetura = args.conjetura if args.conjetura else _conjetura_cal1()
    system_msg = cargar_system()
    user_msg = render_usuario(programa, conjetura, args.gap, args.n, args.historial)

    print("=" * 72)
    print("[DRY-RUN] mensaje role=system:")
    print("=" * 72)
    print(system_msg)
    print("=" * 72)
    print("[DRY-RUN] mensaje role=user (plantilla ya renderizada):")
    print("=" * 72)
    print(user_msg)
    print("=" * 72)
    print(f"[DRY-RUN] api_base destino (no contactado)= {args.api_base}")
    print(f"[DRY-RUN] modelo destino (no contactado)   = {args.model}")
    print("[DRY-RUN] OK: plantillas cargadas y renderizadas sin errores, "
          "sin tocar la red.")


def _llamada_real(args):
    programa = args.programa if args.programa else _programa_ejemplo()
    conjetura = args.conjetura if args.conjetura else _conjetura_cal1()
    try:
        diff = mutar(
            programa, conjetura, args.gap, args.n,
            api_base=args.api_base, model=args.model,
            historial_operadores=args.historial,
        )
    except (urllib.error.URLError, OSError) as e:
        print(f"[ERROR] no se pudo contactar {args.api_base}: {e}", file=sys.stderr)
        print("Sugerencia: corre con --dry-run para validar el prompt sin red, "
              "o levanta Ollama (`ollama serve`) / el mock (`python -m mock_llm.server`).",
              file=sys.stderr)
        sys.exit(1)
    print(diff)


def main():
    ap = argparse.ArgumentParser(
        description="Cliente urllib-only del operador de mutación gemma3:4b (Ollama)."
    )
    ap.add_argument("--dry-run", action="store_true",
                     help="renderiza el prompt y lo imprime SIN llamar a la red "
                          "(funciona aunque Ollama esté caído)")
    ap.add_argument("--api-base", default="http://localhost:11434/v1",
                     dest="api_base", help="endpoint OpenAI-compatible")
    ap.add_argument("--model", default="gemma3:4b")
    ap.add_argument("--gap", type=float, default=-2.375495371091703,
                     help="gap actual de ejemplo (default: el del best_program.py "
                          "de humo_ollama, comet HOJAS=12/LARGO_COLA=6, n=19)")
    ap.add_argument("--n", type=int, default=19)
    ap.add_argument("--programa", default=None,
                     help="ruta a un .py a usar como programa_actual; por default "
                          "usa un comet de ejemplo embebido")
    ap.add_argument("--conjetura", default=None,
                     help="texto de la conjetura activa; por default usa CAL-1")
    ap.add_argument("--historial", default=None,
                     help="texto libre de historial de operadores recientes")
    args = ap.parse_args()

    if args.programa:
        with open(args.programa, encoding="utf-8") as f:
            args.programa = f.read()

    if args.dry_run:
        _dry_run(args)
    else:
        _llamada_real(args)


if __name__ == "__main__":
    main()

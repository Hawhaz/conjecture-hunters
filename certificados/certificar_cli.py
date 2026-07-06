#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI dedicada de la capa de certificacion proof-grade.

Envoltura delgada sobre `certificados.verify` (que tambien expone su propio
__main__). Uso identico:

    # certificar un candidato individual
    python certificados/certificar_cli.py --g6 "<graph6>" --conj cal1|cal2|cal3

    # certificar los 3 fixtures publicados (A/B/C) de tests/fixtures/
    python certificados/certificar_cli.py --fixtures

    # salida JSON (para pipeline / logging)
    python certificados/certificar_cli.py --g6 "<graph6>" --conj cal1 --json

Codigo de salida: 0 si TODO lo pedido queda certificado (gap>0 demostrado),
1 en caso contrario (util como compuerta en scripts: `&& echo CONTRAEJEMPLO`).
"""
import argparse
import json
import os
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _p in (_RAIZ, _AQUI):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from verify import (  # noqa: E402
    DPS_GRANDE,
    _FIXTURES,
    _imprimir_cert,
    _leer_g6,
    _ruta_fixture,
    certificar,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="certificar_cli.py",
        description="Certificacion proof-grade de contraejemplos (gap>0 exacto/riguroso).",
    )
    ap.add_argument("--g6", type=str, default=None,
                    help="graph6 (str, sin cabecera) del candidato")
    ap.add_argument("--conj", type=str, default=None,
                    choices=["cal1", "cal2", "cal3"], help="conjetura objetivo")
    ap.add_argument("--dps", type=int, default=DPS_GRANDE,
                    help="digitos mpmath para el caso grande (n>40)")
    ap.add_argument("--fixtures", action="store_true",
                    help="certifica los 3 fixtures publicados A/B/C")
    ap.add_argument("--json", action="store_true",
                    help="imprime el/los certificado(s) como JSON")
    args = ap.parse_args(argv)

    if args.fixtures:
        resultados = {}
        ok_todos = True
        for etq, (nombre, conj, tam) in _FIXTURES.items():
            ruta = _ruta_fixture(nombre)
            if not os.path.exists(ruta):
                print("[FALTA] %s: %s" % (etq, ruta), file=sys.stderr)
                ok_todos = False
                continue
            cert = certificar(_leer_g6(ruta), conj, dps=args.dps)
            resultados[etq] = cert
            if not args.json:
                _imprimir_cert(cert, "%s [%s, %s]" % (etq, nombre, tam))
            ok_todos = ok_todos and cert["certificado"]
        if args.json:
            print(json.dumps(resultados, indent=2, ensure_ascii=False, default=str))
        else:
            print("=== RESUMEN: %s ===" %
                  ("TODOS CERTIFICADOS" if ok_todos else "ALGUN FIXTURE NO CERTIFICO"))
        return 0 if ok_todos else 1

    if not args.g6 or not args.conj:
        ap.error("indique --g6 <str> --conj cal1|cal2|cal3  (o use --fixtures)")

    cert = certificar(args.g6, args.conj, dps=args.dps)
    if args.json:
        print(json.dumps(cert, indent=2, ensure_ascii=False, default=str))
    else:
        _imprimir_cert(cert)
    return 0 if cert["certificado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

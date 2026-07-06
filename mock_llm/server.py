"""Mock LLM OpenAI-compatible (§8).

POST /v1/chat/completions responde en round-robin desde tests/fixtures/diffs.jsonl
(parches en formato diff/SEARCH-REPLACE que OpenEvolve espera). 100% determinista:
misma secuencia en cada corrida (contador arranca en 0; `created` fijo).

Uso:  python -m mock_llm.server --port 8000
      (o crear_app(ruta_diffs) desde tests)
"""
import argparse
import json
import threading
from pathlib import Path

from fastapi import FastAPI

RUTA_DIFFS_DEFECTO = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "diffs.jsonl"


def _cargar_respuestas(ruta):
    respuestas = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                respuestas.append(json.loads(linea)["response"])
    if not respuestas:
        raise ValueError(f"diffs.jsonl sin respuestas: {ruta}")
    return respuestas


def crear_app(ruta_diffs=None):
    app = FastAPI(title="mock-llm-conjeturas")
    respuestas = _cargar_respuestas(ruta_diffs or RUTA_DIFFS_DEFECTO)
    estado = {"contador": 0}
    candado = threading.Lock()

    def reiniciar():
        with candado:
            estado["contador"] = 0

    app.state.reiniciar = reiniciar
    app.state.estado = estado

    @app.post("/v1/chat/completions")
    async def chat_completions(cuerpo: dict):
        with candado:
            k = estado["contador"]
            estado["contador"] += 1
        contenido = respuestas[k % len(respuestas)]
        return {
            "id": f"mock-{k}",
            "object": "chat.completion",
            "created": 0,  # fijo: determinismo total entre corridas
            "model": cuerpo.get("model", "mock"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": contenido},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    @app.post("/reset")
    async def reset():
        reiniciar()
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"ok": True, "servidas": estado["contador"]}

    return app


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Mock LLM determinista (OpenAI-compatible)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--diffs", default=str(RUTA_DIFFS_DEFECTO))
    args = parser.parse_args()
    uvicorn.run(crear_app(args.diffs), host=args.host, port=args.port)

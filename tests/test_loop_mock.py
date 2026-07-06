"""Nivel 3 — mock LLM OpenAI-compatible + loop completo con OpenEvolve (§8).

- El mock responde en round-robin desde tests/fixtures/diffs.jsonl, 100%
  determinista: misma secuencia en cada corrida.
- Smoke test del loop sobre el TOY ("grafo conexo, n=20, grado máx <= 3,
  maximizar aristas"; óptimo = 30): el archivo de programas crece, best_score
  es no-decreciente entre checkpoints, el TOY alcanza 30, y checkpoint+resume
  reproduce el estado.
"""
import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"
DIFFS = FIX / "diffs.jsonl"
TOY_INICIAL = FIX / "toy_inicial.py"
TOY_EVALUADOR = RAIZ / "evaluators" / "toy_max_edges.py"
OPTIMO_TOY = 30.0


def _respuestas_esperadas():
    with open(DIFFS, encoding="utf-8") as f:
        return [json.loads(l)["response"] for l in f if l.strip()]


# ------------------------------------------------------------------ mock determinista

def test_mock_round_robin_determinista():
    from fastapi.testclient import TestClient

    from mock_llm.server import crear_app

    esperadas = _respuestas_esperadas()
    assert len(esperadas) >= 3, "diffs.jsonl debe traer varios parches enlatados"

    def secuencia(k):
        cliente = TestClient(crear_app(str(DIFFS)))
        outs = []
        for _ in range(k):
            r = cliente.post(
                "/v1/chat/completions",
                json={"model": "mock", "messages": [{"role": "user", "content": "muta"}]},
            )
            assert r.status_code == 200
            j = r.json()
            assert j["object"] == "chat.completion"
            assert j["choices"][0]["finish_reason"] == "stop"
            assert j["choices"][0]["message"]["role"] == "assistant"
            outs.append(j["choices"][0]["message"]["content"])
        return outs

    a = secuencia(len(esperadas) + 2)
    b = secuencia(len(esperadas) + 2)
    assert a == b, "dos corridas del mock deben dar la MISMA secuencia"
    assert a[: len(esperadas)] == esperadas, "el mock debe servir diffs.jsonl en orden"
    assert a[len(esperadas)] == esperadas[0], "al agotarse, el round-robin envuelve"


def test_mock_diffs_tienen_formato_search_replace():
    """Los parches enlatados usan el formato diff que OpenEvolve espera (README)."""
    import re

    patron = r"<<<<<<< SEARCH\n(.*?)=======\n(.*?)>>>>>>> REPLACE"
    for resp in _respuestas_esperadas():
        assert re.findall(patron, resp, re.DOTALL), f"respuesta sin bloque SEARCH/REPLACE: {resp[:80]!r}"


# ------------------------------------------------------------------ servidor real

@pytest.fixture(scope="module")
def mock_server():
    import httpx
    import uvicorn

    from mock_llm.server import crear_app

    app = crear_app(str(DIFFS))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="error"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    for _ in range(120):
        try:
            if httpx.get(f"http://127.0.0.1:{puerto}/health", timeout=1.0).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        pytest.fail("el mock no arrancó")
    yield f"http://127.0.0.1:{puerto}", app
    servidor.should_exit = True
    hilo.join(timeout=5)


def _escribir_config(ruta, api_base):
    ruta.write_text(
        f"""\
max_iterations: 100
checkpoint_interval: 10
random_seed: 42
diff_based_evolution: true
max_code_length: 20000
llm:
  models:
    - name: "mock-gemma"
      api_base: "{api_base}"
      api_key: "mock"
      weight: 1.0
  temperature: 0.0
  timeout: 30
  retries: 1
prompt:
  num_top_programs: 2
  num_diverse_programs: 1
  use_template_stochasticity: false
database:
  population_size: 30
  archive_size: 15
  num_islands: 1
  random_seed: 42
evaluator:
  timeout: 60
  cascade_evaluation: false
  parallel_evaluations: 1
""",
        encoding="utf-8",
    )


def _correr_loop(api_base, out_dir, iteraciones, tmp_path, checkpoint_path=None):
    from openevolve.config import load_config
    from openevolve.controller import OpenEvolve

    yaml_path = tmp_path / f"config_{out_dir.name}.yaml"
    _escribir_config(yaml_path, api_base)
    config = load_config(str(yaml_path))
    ctl = OpenEvolve(str(TOY_INICIAL), str(TOY_EVALUADOR), config, output_dir=str(out_dir))
    mejor = asyncio.run(ctl.run(iterations=iteraciones, checkpoint_path=checkpoint_path))
    return ctl, mejor


def _checkpoints(out_dir):
    d = Path(out_dir) / "checkpoints"
    if not d.is_dir():
        return []
    con_num = []
    for p in d.iterdir():
        if p.is_dir() and p.name.startswith("checkpoint_"):
            con_num.append((int(p.name.split("_")[1]), p))
    return [p for _, p in sorted(con_num)]


def _score_de_checkpoint(ck):
    info = json.loads((ck / "best_program_info.json").read_text(encoding="utf-8"))
    return float(info["metrics"]["combined_score"]), info


def _n_programas(ck):
    return len(list((ck / "programs").glob("*.json")))


def test_loop_toy_alcanza_30(mock_server, tmp_path):
    base, app = mock_server
    app.state.reiniciar()  # determinismo: cada corrida arranca la secuencia en 0

    ctl, mejor = _correr_loop(base + "/v1", tmp_path / "corrida30", 30, tmp_path)

    # 1) el TOY alcanza el óptimo 30 (§8/§10)
    assert mejor is not None
    assert float(mejor.metrics["combined_score"]) == pytest.approx(OPTIMO_TOY)

    # 2) el archivo de programas crece (más que el programa inicial)
    assert len(ctl.database.programs) >= 3

    # 3) best_score no-decreciente a lo largo de los checkpoints
    cks = _checkpoints(tmp_path / "corrida30")
    assert len(cks) >= 2, "con checkpoint_interval=10 y 30 iteraciones esperamos varios checkpoints"
    scores = [_score_de_checkpoint(ck)[0] for ck in cks]
    assert scores == sorted(scores), f"best_score decreció entre checkpoints: {scores}"
    assert scores[-1] == pytest.approx(OPTIMO_TOY)

    # 4) el número de programas guardados nunca decrece entre checkpoints
    conteos = [_n_programas(ck) for ck in cks]
    assert conteos == sorted(conteos), f"programas guardados decrecieron: {conteos}"
    assert conteos[-1] >= 3


def test_loop_checkpoint_y_resume_reproducen_estado(mock_server, tmp_path):
    base, app = mock_server

    app.state.reiniciar()
    ctl1, _ = _correr_loop(base + "/v1", tmp_path / "a", 20, tmp_path)
    cks = _checkpoints(tmp_path / "a")
    assert cks, "la corrida base no dejó checkpoints"
    ck = cks[-1]
    score_ck, info_ck = _score_de_checkpoint(ck)
    n_ck = _n_programas(ck)

    app.state.reiniciar()
    ctl2, mejor2 = _correr_loop(base + "/v1", tmp_path / "b", 10, tmp_path, checkpoint_path=str(ck))

    # el estado del checkpoint se reprodujo: el mejor programa guardado existe en la BD resumida
    assert info_ck["id"] in ctl2.database.programs
    # y no se perdieron programas al resumir
    assert len(ctl2.database.programs) >= n_ck
    # continuar desde el checkpoint jamás empeora el mejor score
    assert float(mejor2.metrics["combined_score"]) >= score_ck - 1e-12

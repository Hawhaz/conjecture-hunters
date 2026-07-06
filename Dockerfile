# Conjecture Hunters — sistema evolutivo caza-contraejemplos (AMD Hackathon ACT II, Track 3)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verificación al construir la imagen: la suite TDD debe estar verde
RUN python -m pytest -q || (echo "pytest rojo: imagen inválida" && exit 1)

# Por defecto: humo del GA de calibración (CAL-1 cae en segundos y escribe CSV)
# Otros modos documentados en el README:
#   pytest              -> python -m pytest
#   mock LLM            -> python -m mock_llm.server --port 8000
#   loop evolutivo      -> openevolve-run calibracion/programa_inicial.py evaluators/agx_l1_mu.py --config configs/calibracion.yaml
CMD ["python", "calibracion/ga_graphs.py", "--runs", "3", "--gens", "300", "--out", "/app/calibracion/runs/ga_docker.csv"]

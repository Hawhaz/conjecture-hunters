# Conjecture Hunters — sistema evolutivo caza-contraejemplos (AMD Hackathon ACT II, Track 3)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verificación al construir la imagen: la suite TDD debe estar verde
RUN python -m pytest -q || (echo "pytest rojo: imagen inválida" && exit 1)

# Por defecto: demo del sistema (resultado estrella + gate de 20 carriles + enjambre).
# Otros modos:
#   pytest              -> python -m pytest
#   solo el gate        -> python retos/pack_extra.py --gate
#   run GPU (AMD MI300X)-> bash deploy/run_gpu.sh --trust-amd-proxy --serve-gemma
CMD ["sh", "deploy/demo.sh"]

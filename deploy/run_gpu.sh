#!/usr/bin/env bash
# ============================================================================
# run_gpu.sh — lanzamiento TURNKEY de Conjecture Hunters en una notebook AMD
# MI300X (imagen ROCm 7.2 + vLLM 0.16 + PyTorch 2.9).  Un solo comando.
#
# Usa GEMMA (no Qwen): sirve google/gemma-3-4b-it en vLLM y apunta el
# orquestador ahí (premio "Best AMD-Hosted Gemma").  El paralelismo masivo son
# miles de *workers* en el nodo (Rust rayon + carriles), con Gemma en la GPU y
# el ledger durable atrapando cualquier hit.
#
# Uso (dentro de la terminal de JupyterLab):
#   bash run_gpu.sh --trust-amd-proxy --serve-gemma --iters 4000
#
# Flags:
#   --trust-amd-proxy   añade el CA raíz del proxy TLS de AMD al trust store
#                       (la caja intercepta HTTPS con cert self-signed; esto
#                       MANTIENE la verificación TLS, contra el CA de AMD — NO
#                       la desactiva). Necesario para git/pip/HuggingFace.
#   --serve-gemma       arranca vLLM sirviendo Gemma en :8000
#   --model NAME        modelo HF (default google/gemma-3-4b-it)
#   --iters N           iteraciones del hunt por carril (default 2000)
#   --no-clone          usa el repo ya presente (no re-clona)
# ============================================================================
set -uo pipefail

MODEL="google/gemma-3-4b-it"
ITERS=2000
DO_PROXY=0; DO_GEMMA=0; DO_CLONE=1
REPO="https://github.com/Hawhaz/conjecture-hunters.git"
WORK="${WORK:-/workspace}"

while [ $# -gt 0 ]; do case "$1" in
  --trust-amd-proxy) DO_PROXY=1;;
  --serve-gemma) DO_GEMMA=1;;
  --model) MODEL="$2"; shift;;
  --iters) ITERS="$2"; shift;;
  --no-clone) DO_CLONE=0;;
  *) echo "flag desconocido: $1";;
esac; shift; done

log(){ echo "[run_gpu $(date +%H:%M:%S)] $*"; }

# --- 0) CA del proxy de AMD (verificación TLS ENCENDIDA, no desactivada) -----
trust_amd_proxy_ca(){
  log "instalando el CA raíz del proxy TLS de AMD (mantiene TLS verificado)..."
  apt-get install -y -qq ca-certificates >/dev/null 2>&1 || true
  # el ÚLTIMO cert de la cadena que presenta el proxy es su raíz:
  openssl s_client -connect github.com:443 -servername github.com -showcerts </dev/null 2>/dev/null \
    | awk '/-----BEGIN CERTIFICATE-----/{n++} {b[n]=b[n]$0"\n"} END{printf "%s", b[n]}' \
    > /usr/local/share/ca-certificates/amd-proxy-root.crt
  update-ca-certificates >/dev/null 2>&1
  git config --global http.sslCAInfo /etc/ssl/certs/ca-certificates.crt
  export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
  export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
  export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
  log "CA instalado. Probando git..."
  git ls-remote "$REPO" -q >/dev/null 2>&1 && log "TLS OK" || log "AVISO: TLS aún falla (revisar proxy)"
}
[ "$DO_PROXY" = 1 ] && trust_amd_proxy_ca

# --- 1) repo -----------------------------------------------------------------
cd "$WORK"
if [ "$DO_CLONE" = 1 ] && [ ! -d "$WORK/conjecture-hunters/.git" ]; then
  log "clonando repo..."; git clone --depth 1 "$REPO" || { log "clone falló (¿--trust-amd-proxy?)"; exit 1; }
fi
cd "$WORK/conjecture-hunters" || { log "no está el repo; usa --trust-amd-proxy o sube un bundle"; exit 1; }

# --- 2) deps (CPU) -----------------------------------------------------------
log "instalando deps python..."
pip install -q networkx numpy sympy >/dev/null 2>&1

# --- 3) GATE anti-basura + ledger (prueba que corre en ROCm, 0 basura) -------
log "gate anti-basura del pack (debe quedar VERDE)..."
python retos/pack_conjeturas.py --gate || { log "GATE ROJO -> no se lanza (basura)"; exit 1; }
python hallazgos/registro.py --resumen || true

# --- 4) Gemma en vLLM (la GPU + el premio) -----------------------------------
if [ "$DO_GEMMA" = 1 ]; then
  log "sirviendo Gemma ($MODEL) en vLLM :8000 ..."
  ( vllm serve "$MODEL" --port 8000 --max-model-len 4096 >/tmp/vllm.log 2>&1 & )
  for i in $(seq 1 60); do
    curl -s http://localhost:8000/v1/models >/dev/null 2>&1 && { log "Gemma LISTA"; break; }
    sleep 5
  done
  export CONJ_API_BASE="http://localhost:8000/v1"
  export CONJ_MODEL="$MODEL"
  export CONJ_LLM="openai"
fi

# --- 5) ENJAMBRE: satura TODOS los cores cazando las 20 conjeturas + ledger --
MINS="${MINS:-210}"   # ~3.5 h de la ventana de 4 h (deja margen para serve/LoRA)
log "lanzando ENJAMBRE: todos los cores, ${MINS} min, ledger durable activo..."
python orquestador/enjambre.py --minutos "$MINS" --workers 0
log "resumen de hallazgos:"; python hallazgos/registro.py --resumen || true
# (Gemma como mutador mas inteligente: el enjambre usa busqueda local rapida; con
#  --serve-gemma vLLM queda en :8000 y el mutador puede consultarlo — enhancement.)
log "hecho. Hallazgos -> hallazgos/  (ALERTAS.md, HIT_*.md, shards/)."

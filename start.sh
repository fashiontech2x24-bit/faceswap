#!/usr/bin/env bash
# start.sh — launch the GHOST 2.0 API server
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONNOUSERSITE=1

echo "[INFO] Starting GHOST 2.0 Face Swap API → http://0.0.0.0:${PORT:-8000}"

exec python -m uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}"

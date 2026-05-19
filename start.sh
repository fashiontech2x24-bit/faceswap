#!/usr/bin/env bash
# start.sh — launch the GHOST 2.0 API server
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONNOUSERSITE=1

# Resolve Python: explicit env var > conda ghost2 env > current python
if [ -z "${GHOST_PYTHON:-}" ]; then
    CONDA_BASE=$(conda info --base 2>/dev/null || echo "")
    if [ -n "$CONDA_BASE" ] && [ -x "$CONDA_BASE/envs/ghost2/bin/python" ]; then
        GHOST_PYTHON="$CONDA_BASE/envs/ghost2/bin/python"
    else
        GHOST_PYTHON="$(which python)"
    fi
fi

[ -x "$GHOST_PYTHON" ] || { echo "[ERROR] Python not found: $GHOST_PYTHON" >&2; exit 1; }
echo "[INFO] Python: $GHOST_PYTHON"
echo "[INFO] Starting GHOST 2.0 Face Swap API → http://0.0.0.0:${PORT:-8000}"

exec "$GHOST_PYTHON" -m uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}"

#!/usr/bin/env bash
set -euo pipefail

echo "[start.sh] CWD=$(pwd)"
echo "[start.sh] PORT=${PORT-<unset>}"
echo "[start.sh] PYTHONPATH(before)=${PYTHONPATH-<empty>}"

export PYTHONUNBUFFERED=1
export PYTHONPATH="$(pwd):${PYTHONPATH-}"
echo "[start.sh] PYTHONPATH(after)=$PYTHONPATH"

# Arranca uvicorn usando el PORT que inyecta Railway
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"

#!/usr/bin/env bash
set -e

# Ir a la carpeta backend (donde está app/main.py)
cd "$(dirname "$0")"

# Asegura PYTHONPATH para que 'app' se resuelva
export PYTHONPATH=.

# Toma el PORT de Railway o usa 8000 en local
PORT="${PORT:-8000}"

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

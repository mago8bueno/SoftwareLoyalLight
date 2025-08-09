#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH=.
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

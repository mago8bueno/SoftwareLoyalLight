#!/usr/bin/env bash
set -euo pipefail

# Ir a la carpeta del backend (ajusta si tu estructura difiere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT/backend"

# Variables seguras
export PYTHONUNBUFFERED=1
export PORT="${PORT:-8080}"   # Railway inyecta PORT; si no, 8080

echo "[start.sh] CWD=$(pwd)"
echo "[start.sh] Using PORT=$PORT"

# Lanzar uvicorn (usa el módulo, no rutas relativas)
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

#!/bin/bash
set -e

echo "Iniciando backend..."
# Ya estás en /backend gracias a Railway, no hace falta cd
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

#!/bin/bash
set -e

if [ -d "backend" ]; then
  cd backend
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

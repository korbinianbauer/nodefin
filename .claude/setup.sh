#!/usr/bin/env bash
# Idempotent environment setup for nodefin (run by the SessionStart hook).
set -uo pipefail

echo "[nodefin setup] installing backend dependencies…"
pip install --quiet -r backend/requirements.txt 2>/dev/null \
  || pip install --quiet fastapi "uvicorn[standard]" pandas numpy pydantic httpx pytest

# Frontend deps are optional and slow; only install if node_modules is missing
# and npm is available.
if command -v npm >/dev/null 2>&1 && [ -f frontend/package.json ] && [ ! -d frontend/node_modules ]; then
  echo "[nodefin setup] installing frontend dependencies…"
  ( cd frontend && npm install --silent ) || echo "[nodefin setup] frontend install skipped"
fi

echo "[nodefin setup] done."

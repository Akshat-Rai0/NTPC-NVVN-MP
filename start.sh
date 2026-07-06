#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

"$PYTHON_BIN" manage.py migrate
exec "$PYTHON_BIN" manage.py runserver "$HOST:$PORT"
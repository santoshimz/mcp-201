#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

if [ -f ".env" ]; then
  set -a
  . ".env"
  set +a
fi

exec .venv/bin/python src/mcp_201_server.py "$@"

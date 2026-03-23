#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR/backend"
. .venv/bin/activate
python -m unittest discover -s tests

cd "$ROOT_DIR/frontend"
npm run lint

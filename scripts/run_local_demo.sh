#!/usr/bin/env bash
set -euo pipefail

python3 -m mcp_201.cli --input "${1:-examples/request.json}"

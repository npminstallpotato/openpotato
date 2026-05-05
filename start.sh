#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON=".venv/bin/python"

echo "Starting Utils service…"
$PYTHON -B apps/utils/app.py &
echo $! > /tmp/openpotato-utils.pid
echo "  PID $(cat /tmp/openpotato-utils.pid) — http://localhost:8001"

echo "Starting LLM service…"
$PYTHON -B apps/llm/app.py &
echo $! > /tmp/openpotato-llm.pid
echo "  PID $(cat /tmp/openpotato-llm.pid) — http://localhost:8002"

echo "Starting Gateway service…"
$PYTHON -B apps/gateway/app.py &
echo $! > /tmp/openpotato-gateway.pid
echo "  PID $(cat /tmp/openpotato-gateway.pid) — http://localhost:8000"

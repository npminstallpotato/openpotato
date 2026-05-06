#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON=".venv/bin/python"

if [ ! -f "$PYTHON" ]; then
    echo "Error: virtual environment not found at $PYTHON"
    echo "Run ./install.sh first to set up dependencies."
    exit 1
fi

# Check port availability
for port in 8000 8001 8002; do
    if lsof -i :"$port" &>/dev/null 2>&1; then
        echo "Warning: port $port is already in use — service may fail to bind"
    fi
done

echo "Starting LLM service…"
$PYTHON -B services/llm/app.py &
echo $! > /tmp/openpotato-llm.pid
echo "  PID $(cat /tmp/openpotato-llm.pid) — http://localhost:8002"

echo "Starting Util service…"
$PYTHON -B services/util/app.py &
echo $! > /tmp/openpotato-util.pid
echo "  PID $(cat /tmp/openpotato-util.pid) — http://localhost:8001"

echo "Starting Gateway service…"
$PYTHON -B services/gateway/app.py &
echo $! > /tmp/openpotato-gateway.pid
echo "  PID $(cat /tmp/openpotato-gateway.pid) — http://localhost:8000"

# Wait for services to be ready
sleep 2
echo
echo "Checking services…"
if curl -sf http://127.0.0.1:8001/health >/dev/null 2>&1; then
    echo "  ✓ Util service is healthy"
else
    echo "  ✗ Util service not ready yet — check logs for errors"
fi

if curl -sf http://127.0.0.1:8000/api/llm/health >/dev/null 2>&1; then
    echo "  ✓ LLM service is healthy (via Gateway)"
else
    echo "  ✗ LLM service not ready yet — check logs for errors"
fi

if curl -sf http://127.0.0.1:8000/ >/dev/null 2>&1; then
    echo "  ✓ Gateway is serving"
else
    echo "  ✗ Gateway not ready yet — check logs for errors"
fi

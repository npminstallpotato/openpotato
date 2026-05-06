#!/usr/bin/env bash
set -euo pipefail

for pidfile in /tmp/openpotato-*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile")
  service="$(basename "$pidfile" .pid | sed 's/openpotato-//')"

  if ! kill "$pid" 2>/dev/null; then
    echo "$service (PID $pid) not running"
    rm -f "$pidfile"
    continue
  fi

  # Graceful shutdown: wait up to 3 seconds, then force-kill
  echo "Stopping $service (PID $pid)…"
  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
    if [ "$waited" -ge 3 ]; then
      echo "  Force killing $service…"
      kill -9 "$pid" 2>/dev/null || true
      break
    fi
  done
  echo "  Stopped $service"
  rm -f "$pidfile"
done

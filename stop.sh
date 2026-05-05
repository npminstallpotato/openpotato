#!/usr/bin/env bash
set -euo pipefail

for pidfile in /tmp/openpotato-*.pid; do
  [ -f "$pidfile" ] || continue
  pid=$(cat "$pidfile")
  service="$(basename "$pidfile" .pid | sed 's/openpotato-//')"
  if kill "$pid" 2>/dev/null; then
    echo "Stopped $service (PID $pid)"
  else
    echo "$service (PID $pid) not running"
  fi
  rm -f "$pidfile"
done

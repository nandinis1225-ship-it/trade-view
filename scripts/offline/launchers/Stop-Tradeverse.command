#!/bin/bash
# Stop TRADEVERSE local backend after the event
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$DIR/.tradeverse-backend.pid"

chmod +x "$0" 2>/dev/null || true

echo "Stopping TRADEVERSE backend..."

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    sleep 1
    kill -9 "$PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

# Fallback: any tradeverse-backend in this directory
pkill -f "$DIR/tradeverse-backend" 2>/dev/null || true

echo "TRADEVERSE backend stopped."
echo "Your portfolio data is saved on this computer."
read -r -p "Press Enter to close..."

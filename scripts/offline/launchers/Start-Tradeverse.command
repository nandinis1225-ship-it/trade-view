#!/bin/bash
# TRADEVERSE browser launcher (macOS) — double-click to start
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PORT="${BACKEND_PORT:-8765}"
HEALTH_URL="http://127.0.0.1:${PORT}/api/v1/health"
TERMINAL_URL="http://127.0.0.1:${PORT}/terminal"
PID_FILE="$DIR/.tradeverse-backend.pid"
BACKEND_BIN="$DIR/tradeverse-backend"

chmod +x "$0" 2>/dev/null || true

if [[ ! -x "$BACKEND_BIN" ]]; then
  echo "ERROR: tradeverse-backend not found or not executable in:"
  echo "  $DIR"
  read -r -p "Press Enter to close..."
  exit 1
fi

health_ok() {
  curl -sf --max-time 2 "$HEALTH_URL" >/dev/null 2>&1
}

if health_ok; then
  echo "TRADEVERSE backend is already running."
  open "$TERMINAL_URL"
  echo ""
  echo "Browser opened. Enter your PIN to resume if needed."
  echo "Use Stop-Tradeverse.command when the event is finished."
  exit 0
fi

echo "Starting TRADEVERSE backend..."
nohup "$BACKEND_BIN" >/dev/null 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PID_FILE"

echo "Waiting for backend health check..."
for i in $(seq 1 60); do
  if health_ok; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "ERROR: Backend process exited before becoming healthy."
    rm -f "$PID_FILE"
    read -r -p "Press Enter to close..."
    exit 1
  fi
  sleep 1
done

if ! health_ok; then
  echo ""
  echo "ERROR: Backend did not start within 60 seconds."
  kill "$BACKEND_PID" 2>/dev/null || true
  rm -f "$PID_FILE"
  read -r -p "Press Enter to close..."
  exit 1
fi

echo "Backend is ready."
open "$TERMINAL_URL"
echo ""
echo "TRADEVERSE opened in your browser."
echo ""
echo "  1. Enter your name and event PIN"
echo "  2. Trade until the simulation ends"
echo "  3. Close the browser anytime — reopen this launcher to resume"
echo "  4. When finished, run Stop-Tradeverse.command"
echo ""

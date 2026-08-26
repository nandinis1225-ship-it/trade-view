#!/usr/bin/env bash
# Builds browser-based TRADEVERSE participant package (macOS — no Tauri)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$ROOT/participant-build/macos/TRADEVERSE"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_DIR="$ROOT/backend"
LAUNCHERS_DIR="$ROOT/scripts/offline/launchers"
EVENT_PIN="${EVENT_PIN:-${1:-}}"
TIMELINE_EVENTS="${TIMELINE_EVENTS:-64}"

if [[ -z "$EVENT_PIN" ]]; then
  echo "Event PIN required: set EVENT_PIN environment variable or pass as first argument." >&2
  exit 1
fi

echo "Ensuring protected production timeline ($TIMELINE_EVENTS events)..."
(cd "$BACKEND_DIR" && python3 scripts/ensure_production_timeline_pkg.py --events "$TIMELINE_EVENTS")

echo "Building participant frontend..."
(cd "$FRONTEND_DIR" && npm install && npm run build:participant)

echo "Building backend sidecar (PyInstaller)..."
(cd "$BACKEND_DIR" && pip3 install pyinstaller && pyinstaller --noconfirm tradeverse-backend.spec)

SIDECAR="$BACKEND_DIR/dist/tradeverse-backend"
if [[ ! -f "$SIDECAR" ]]; then
  echo "tradeverse-backend binary not found after PyInstaller build" >&2
  exit 1
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

cp "$SIDECAR" "$OUT_DIR/tradeverse-backend"
chmod +x "$OUT_DIR/tradeverse-backend"
cp -R "$FRONTEND_DIR/out" "$OUT_DIR/ui"
python3 "$BACKEND_DIR/scripts/build_event_env.py" --event-pin "$EVENT_PIN" --output "$OUT_DIR/.env"

echo "Copying browser launchers..."
cp "$LAUNCHERS_DIR/Start-Tradeverse.command" "$OUT_DIR/Start-Tradeverse.command"
cp "$LAUNCHERS_DIR/Stop-Tradeverse.command" "$OUT_DIR/Stop-Tradeverse.command"
chmod +x "$OUT_DIR/Start-Tradeverse.command" "$OUT_DIR/Stop-Tradeverse.command"

if [[ -f "$ROOT/scripts/offline/audit-browser-participant-build.sh" ]]; then
  "$ROOT/scripts/offline/audit-browser-participant-build.sh" "$OUT_DIR"
fi

echo ""
echo "macOS browser participant package ready: $OUT_DIR"
echo "Distribute the TRADEVERSE folder. Participants double-click Start-Tradeverse.command"
echo "(Tauri desktop build remains available via build-participant-macos.sh for future use.)"

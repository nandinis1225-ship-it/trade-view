#!/usr/bin/env bash
# Builds self-contained TRADEVERSE participant package (macOS — run on a Mac)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$ROOT/participant-build/macos"
FRONTEND_DIR="$ROOT/frontend"
BACKEND_DIR="$ROOT/backend"
TIMELINE_JSON="$BACKEND_DIR/app/seed/tradeverse_timeline.json"
EVENT_PIN="${1:-}"
TIMELINE_EVENTS="${TIMELINE_EVENTS:-64}"

if [[ -z "$EVENT_PIN" ]]; then
  echo "Usage: $0 <EVENT_PIN>" >&2
  exit 1
fi

if [[ ! -f "$TIMELINE_JSON" ]]; then
  echo "Production timeline missing: $TIMELINE_JSON" >&2
  exit 1
fi

echo "Protecting production timeline ($TIMELINE_EVENTS events)..."
(cd "$BACKEND_DIR" && python3 scripts/protect_timeline.py --events "$TIMELINE_EVENTS")

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

echo "Building Tauri shell..."
(cd "$ROOT/desktop" && npm install && npm run tauri build)

APP_BUNDLE="$(find "$ROOT/desktop/src-tauri/target/release/bundle/macos" -name 'TRADEVERSE.app' -maxdepth 1 | head -1)"
if [[ -z "$APP_BUNDLE" ]]; then
  echo "TRADEVERSE.app not found in Tauri bundle output" >&2
  exit 1
fi
cp -R "$APP_BUNDLE" "$OUT_DIR/TRADEVERSE.app"

DMG="$(find "$ROOT/desktop/src-tauri/target/release/bundle/dmg" -name 'TRADEVERSE*.dmg' 2>/dev/null | head -1 || true)"
if [[ -n "$DMG" ]]; then
  cp "$DMG" "$OUT_DIR/"
fi

MACOS_DIR="$OUT_DIR/TRADEVERSE.app/Contents/MacOS"
cp "$OUT_DIR/tradeverse-backend" "$MACOS_DIR/"
cp -R "$OUT_DIR/ui" "$MACOS_DIR/"
cp "$OUT_DIR/.env" "$MACOS_DIR/"

if [[ -f "$ROOT/scripts/offline/audit-participant-build.sh" ]]; then
  "$ROOT/scripts/offline/audit-participant-build.sh" "$OUT_DIR"
fi

echo ""
echo "macOS participant build ready: $OUT_DIR"

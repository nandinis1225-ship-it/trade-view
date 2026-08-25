#!/usr/bin/env bash
# Run full event rehearsal gate before building participant package (Linux/macOS).
set -euo pipefail

SPEED="${1:-60}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND="$ROOT/backend"
VENV_PY="$BACKEND/.venv/bin/python"

if [[ "${SKIP_REHEARSAL:-}" == "1" ]]; then
  echo "Skipping developer rehearsal (SKIP_REHEARSAL=1)"
  exit 0
fi

if [[ ! -x "$VENV_PY" ]]; then
  echo "Backend venv missing — create backend/.venv first"
  exit 1
fi

export DEVELOPER_MODE=true
export LOCAL_INSTANCE_MODE=true
export DATABASE_URL="sqlite+pysqlite:///:memory:"
export SIMULATION_SPEED="$SPEED"

cd "$BACKEND"
"$VENV_PY" -m pytest \
  tests/test_phase5_accelerated_rehearsal.py \
  tests/test_phase5_gates.py \
  tests/test_phase3_validation.py \
  tests/test_recovery.py \
  tests/test_participant_privacy.py \
  tests/test_event_mode.py \
  tests/test_pin_security.py \
  tests/test_identity_lock.py \
  tests/test_dissolution.py \
  tests/test_developer_mode_gating.py \
  tests/test_cross_sector_news.py \
  -q

echo "Developer rehearsal gate PASSED at ${SPEED}x speed profile."

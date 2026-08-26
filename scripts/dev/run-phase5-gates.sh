#!/usr/bin/env bash
# Phase 5 — build, test, and audit gates (see tradeverse_final_hardening plan Phase 5).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV_PY="$BACKEND/.venv/bin/python"
FAIL=0

echo "=== Phase 5 Gate 1: Backend pytest ==="
cd "$BACKEND"
if ! "$VENV_PY" -m pytest \
  tests/test_phase5_gates.py \
  tests/test_phase5_accelerated_rehearsal.py \
  tests/test_phase3_validation.py \
  tests/test_recovery.py \
  tests/test_participant_privacy.py \
  tests/test_event_mode.py \
  tests/test_pin_security.py \
  tests/test_identity_lock.py \
  tests/test_dissolution.py \
  tests/test_checkpoint_jump.py \
  tests/test_developer_mode_gating.py \
  tests/test_cross_sector_news.py \
  tests/test_participant_build_audit.py \
  tests/test_projector_build_audit.py \
  tests/test_phase35_packaging.py \
  tests/test_production_timeline_bootstrap.py \
  tests/test_event_e2e_rehearsal.py \
  tests/test_browser_launcher_packaging.py \
  -q; then
  FAIL=1
fi

echo "=== Phase 5 Gate 2: Frontend lint + builds ==="
cd "$FRONTEND"
if ! npm run lint; then FAIL=1; fi
if ! npm run build:participant; then FAIL=1; fi
if ! npm run build:projector; then FAIL=1; fi
if ! npx tsc --noEmit; then FAIL=1; fi

echo "=== Phase 5 Gate 3: Static build audits ==="
cd "$BACKEND"
if ! "$VENV_PY" -m pytest tests/test_participant_build_audit.py tests/test_projector_build_audit.py -q; then
  FAIL=1
fi

echo "=== Phase 5 Gate 4: Accelerated rehearsal ==="
if ! SKIP_REHEARSAL=0 bash "$ROOT/scripts/dev/run-event-rehearsal.sh" 60; then
  FAIL=1
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "PHASE 5 GATES: FAILED"
  exit 1
fi

echo "PHASE 5 GATES: PASSED"
echo "Note: Windows Build-Participant.ps1 + audit-participant-build.ps1 require organizer Windows machine."

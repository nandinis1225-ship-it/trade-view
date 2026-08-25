#!/usr/bin/env bash
# Audit projector static build for forbidden participant/admin/developer content
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
UI="${ROOT}/ui"
failures=()

forbidden_patterns=(
  "TIMELINE_DECRYPT_KEY"
  "tradeverse_timeline.json"
  "tradeverse_timeline.baked.json"
  "tradeverse_timeline.pkg"
  "SUPABASE"
  "supabase.co"
  "railway.app"
  "leaderboard"
  "EUPHORIA"
  "CRASH"
  "RECOVERY"
  "PHASE 1"
  "PHASE 2"
  "PHASE 3"
  "PHASE 4"
  "AI_TICK"
  "sector_impacts"
  "effective_impact"
  "stop_loss"
  "take_profit"
  "current_phase"
  "OrganizerDebugPanel"
  "/developer"
  "adminLogin"
  "fair_value"
  "PinGateOverlay"
  "RecoveryScreen"
  "EventCompleteScreen"
)

forbidden_dirs=(admin market-screen developer terminal)

if [[ ! -d "$UI" ]]; then
  echo "AUDIT SKIPPED — no ui/ directory at $ROOT"
  exit 0
fi

for dir in "${forbidden_dirs[@]}"; do
  if [[ -d "$UI/$dir" ]]; then
    failures+=("$UI/$dir: forbidden route directory")
  fi
done

while IFS= read -r -d '' file; do
  for pat in "${forbidden_patterns[@]}"; do
    if grep -qF "$pat" "$file" 2>/dev/null; then
      failures+=("$file: contains '$pat'")
    fi
  done
done < <(find "$UI" -type f -print0)

if ((${#failures[@]} > 0)); then
  echo "PROJECTOR AUDIT FAILED"
  printf '  %s\n' "${failures[@]}"
  exit 1
fi

echo "PROJECTOR AUDIT PASSED"

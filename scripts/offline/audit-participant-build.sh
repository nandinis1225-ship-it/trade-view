#!/usr/bin/env bash
# Audit participant package for forbidden content (aligned with audit-participant-build.ps1)
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
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
  "MARKET_PULSE"
  "sector_impacts"
  "effective_impact"
  "stop_loss"
  "take_profit"
  "current_phase"
  "OrganizerDebugPanel"
  "/developer"
  "adminLogin"
)

forbidden_dirs=(admin market-screen developer)
forbidden_db=(mse_dev.db mse_dev.db-shm mse_dev.db-wal)

for db in "${forbidden_db[@]}"; do
  if find "$ROOT" -name "$db" -print -quit 2>/dev/null | grep -q .; then
    failures+=("Development database must not be shipped: $db")
  fi
done

scan() {
  local path="$1"
  [[ -e "$path" ]] || return 0
  if [[ -d "$path" ]]; then
    for dir in "${forbidden_dirs[@]}"; do
      if [[ -d "$path/$dir" ]]; then
        failures+=("$path/$dir: forbidden route directory")
      fi
    done
    while IFS= read -r -d '' file; do
      for pat in "${forbidden_patterns[@]}"; do
        if grep -qF "$pat" "$file" 2>/dev/null; then
          failures+=("$file: contains '$pat'")
        fi
      done
    done < <(find "$path" -type f -print0)
  else
    for pat in "${forbidden_patterns[@]}"; do
      if grep -qF "$pat" "$path" 2>/dev/null; then
        failures+=("$path: contains '$pat'")
      fi
    done
  fi
}

scan "$ROOT/ui"
scan "$ROOT/.env"

if ((${#failures[@]} > 0)); then
  echo "AUDIT FAILED"
  printf '  %s\n' "${failures[@]}"
  exit 1
fi

echo "AUDIT PASSED"

#!/usr/bin/env bash
# Audit browser-based TRADEVERSE participant package
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)/participant-build/macos/TRADEVERSE}"
failures=()

required_files=(
  "Start-Tradeverse.command"
  "Stop-Tradeverse.command"
  "tradeverse-backend"
  "ui/terminal/index.html"
)

forbidden_patterns=(
  "TIMELINE_DECRYPT_KEY"
  "tradeverse_timeline.json"
  "tradeverse_timeline.baked.json"
  "mse_dev.db"
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
)

forbidden_dirs=(admin market-screen developer)
forbidden_db=(mse_dev.db mse_dev.db-shm mse_dev.db-wal)

for file in "${required_files[@]}"; do
  if [[ ! -e "$ROOT/$file" ]]; then
    failures+=("Missing required file: $file")
  fi
done

for db in "${forbidden_db[@]}"; do
  if find "$ROOT" -name "$db" -print -quit 2>/dev/null | grep -q .; then
    failures+=("Development database must not be shipped: $db")
  fi
done

scan_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  for pat in "${forbidden_patterns[@]}"; do
    if grep -qF "$pat" "$file" 2>/dev/null; then
      failures+=("$file: contains '$pat'")
    fi
  done
}

scan_dir() {
  local path="$1"
  [[ -d "$path" ]] || return 0
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
}

scan_dir "$ROOT/ui"
scan_file "$ROOT/.env"
scan_file "$ROOT/Start-Tradeverse.command"
scan_file "$ROOT/Stop-Tradeverse.command"

if ((${#failures[@]} > 0)); then
  echo "BROWSER PACKAGE AUDIT FAILED"
  printf '  %s\n' "${failures[@]}"
  exit 1
fi

echo "BROWSER PACKAGE AUDIT PASSED"

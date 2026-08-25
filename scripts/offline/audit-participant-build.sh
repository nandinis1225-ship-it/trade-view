#!/usr/bin/env bash
# Audit participant package for forbidden content
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
failures=()

forbidden_patterns=(
  "TIMELINE_DECRYPT_KEY"
  "tradeverse_timeline.json"
  "tradeverse_timeline.baked.json"
  "SUPABASE"
  "supabase.co"
  "railway.app"
  "leaderboard"
  "/developer"
  "adminLogin"
  "OrganizerDebugPanel"
)

forbidden_dirs=(admin market-screen developer)

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
        if grep -q "$pat" "$file" 2>/dev/null; then
          failures+=("$file: contains '$pat'")
        fi
      done
    done < <(find "$path" -type f -print0)
  else
    for pat in "${forbidden_patterns[@]}"; do
      if grep -q "$pat" "$path" 2>/dev/null; then
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

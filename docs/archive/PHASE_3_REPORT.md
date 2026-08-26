# PHASE 3 REPORT — Validation + Simulation Correctness

**Date:** 2026-08-25  
**Branch:** `main`  
**Scope:** Phase 3 only (no participant UI redesign, no projector build)

---

## 1. TypeScript / Build Status

| Item | Status |
|------|--------|
| `PARTICIPANT_BUILD=1 npm run build` | **PASS** |
| ESLint during build | **PASS** (fixed unused imports, `released_at` nullability, portfolio ticker typing) |
| `npx tsc --noEmit` | **PASS** (after production build generates `.next/types`) |

**Fixes applied:**
- `frontend/src/lib/api.ts` — removed unused imports; `supabaseEventControlTable` added to runtime config type
- `frontend/src/lib/runtimeConfig.ts` — `supabaseEventControlTable` field
- `frontend/src/app/terminal/page.tsx` — removed unused `reloadCharts`; safe ticker mapping
- `frontend/src/app/market-screen/page.tsx` — `released_at` accepts `null`

---

## 2. Tests Run

```bash
cd backend && .venv/bin/python -m pytest \
  tests/test_phase3_validation.py \
  tests/test_recovery.py \
  tests/test_pin_security.py \
  tests/test_identity_lock.py \
  tests/test_event_mode.py \
  tests/test_participant_privacy.py \
  tests/test_dissolution.py \
  tests/test_checkpoint_jump.py \
  tests/test_developer_mode_gating.py \
  tests/test_participant_build_audit.py \
  -q
```

```bash
cd frontend && PARTICIPANT_BUILD=1 npm run build
cd frontend && npx tsc --noEmit
```

---

## 3. Tests Passed

**40 passed**, **1 skipped** (`test_production_timeline_structure` — requires `TIMELINE_DECRYPT_KEY`)

Phase 3 validation module (`tests/test_phase3_validation.py`):
- News sector impact ±5% deterministic variation
- Fair value authority without instant LTP snap
- AI movement toward fair value target
- News hierarchy over participant trading
- AI tick 30s interval (recovery path)
- Market pulse disabled in participant event mode (source inspection)
- IPO full path + replay idempotency
- Dissolution replay idempotency
- Recovery integration (news, AI ticks, IPO lifecycle, dissolution)
- Identity recovery + name-change block
- Participant REST leak audit
- Offline startup URL scan (participant paths)
- Performance smoke (120 × 30s sim steps)

---

## 4. Tests Failed

**None** in the Phase 3 suite above.

Legacy full-suite tests not re-run (known pre-existing failures when `TIMELINE_DECRYPT_KEY` absent and mini-timeline autouse removed).

---

## 5. News Impact Validation

| Check | Result |
|-------|--------|
| Sector +10% → stock targets in [+9.5%, +10.5%] | **PASS** |
| Sector −10% → stock targets in [−10.5%, −9.5%] | **PASS** |
| Deterministic `seeded_variation` ∈ [−0.05, +0.05] | **PASS** |
| `fair_value` set from `NewsStockImpact.target_price` | **PASS** |
| No unconditional LTP snap on release | **PASS** (LTP unchanged at release; fair_value updated) |
| AI moves LTP toward target | **PASS** (distance to target decreases over AI ticks) |

Formula unchanged: `target_pct = sector_pct × (1 + variation)`.

---

## 6. AI Tick Validation

| Check | Result |
|-------|--------|
| `AI_TICK_INTERVAL_SEC = 30.0` | **PASS** |
| Recovery catch-up fires ticks at 30, 60, 90, 120 sim-seconds | **PASS** |
| 3-second market pulse gated by `not participant_event_mode` | **PASS** (source inspection of `simulation_engine._loop`) |
| Events at same timestamp can defer an AI tick to next interval | **Observed** (chronological event priority) |

---

## 7. Recovery Integration Results

| Check | Result |
|-------|--------|
| Chronological catch-up after simulated downtime | **PASS** |
| NEWS processed once | **PASS** |
| AI ticks during catch-up | **PASS** (≥2 ticks) |
| IPO open → close → allot via timeline | **PASS** |
| Dissolution executed once | **PASS** |
| Second recovery pass processes 0 duplicate events | **PASS** |

---

## 8. IPO Results

| Step | Result |
|------|--------|
| Open → apply → cash blocked | **PASS** |
| Close → allot → blocked cash released | **PASS** |
| Allocated shares created on list | **PASS** |
| Replay allot/list → `already_allotted` / `already_listed` | **PASS** |
| Tradable only after listing | **PASS** (stock created at list) |

---

## 9. Dissolution Results

| Check | Result |
|-------|--------|
| Holdings liquidated at checkpoint | **PASS** |
| P&L updated | **PASS** |
| Replay → `already_dissolved`, no duplicate payout | **PASS** |

---

## 10. Information Leak Audit

### REST (event mode)
- `test_participant_privacy.py` — **PASS**
- `test_participant_api_leak_audit` — **PASS** (no phase/sector_impacts/EUPHORIA strings; stocks mask `fair_value` as LTP)

### Static participant build (`frontend/out` after route prune)
| Finding | Severity |
|---------|----------|
| Pruned route dirs (`admin`, `developer`, `market-screen`) absent | **PASS** |
| `_next/static/chunks/*developer*` still contains `/developer`, `effective_impact` | **HIGH** — dead chunks not tree-shaken |
| Shared chunk contains `SUPABASE`, `leaderboard` strings | **MEDIUM** — organizer code in bundle; runtime gated off in event mode |
| Terminal chunk references `MARKET_PULSE` handler | **LOW** — WS event suppressed server-side in event mode |

**Action:** Full chunk purge requires `PARTICIPANT_BUILD` to exclude developer/admin/market-screen pages at compile time (packaging polish — not done in Phase 3).

---

## 11. Offline Dependency Audit

| Check | Result |
|-------|--------|
| `main.py`, `terminal/page.tsx`, `api.ts`, `runtimeConfig.ts`, Tauri `main.rs` — no hardcoded external URLs | **PASS** |
| Participant startup uses `127.0.0.1:8765` only | **PASS** |
| Supabase/remote leaderboard gated by env/runtime config | **PASS** (not called when unset) |

**Note:** Live offline capture (Wi-Fi off packet trace) not performed in Linux dev VM — see clean-machine procedure.

---

## 12. Participant Executable Build Status

| Item | Status |
|------|--------|
| `Build-Participant.ps1` on Linux CI | **NOT RUN** (Windows + PyInstaller + Tauri required) |
| Frontend static export | **PASS** |
| Backend PyInstaller spec present | **Ready** |
| Tauri shell present | **Ready** |

**Cannot claim clean-machine or `.exe` validation passed** from this environment.

---

## 13. Remaining Blockers

1. **Clean-machine Windows test not performed** — see `docs/CLEAN_MACHINE_TEST.md`
2. **`TIMELINE_DECRYPT_KEY` not available in CI** — production timeline tests skipped; organizer must run locally with key
3. **Participant static bundle still contains developer chunk strings** after directory prune — needs compile-time page exclusion
4. **Tauri icon / Windows toolchain** — unverified on this agent
5. **Event-ready declaration** — **blocked** until clean-machine test completes

### Test timeline discrepancy (§15)

**Resolution: A — mini timeline is TEST ONLY.**

- `TEST_TIMELINE_MINI` in `backend/tests/conftest.py` (2 events) — explicit `mini_timeline` fixture
- Production timeline tests use `production_timeline` fixture (requires `TIMELINE_DECRYPT_KEY`)
- `test_timeline_integration.py` / `test_simulation_control.py` updated to use `production_timeline`
- Production `tradeverse_timeline.enc` is **not modified**

---

## 14. Exact Commands Used

```bash
# Frontend production build
cd frontend && PARTICIPANT_BUILD=1 npm run build

# Typecheck
cd frontend && npx tsc --noEmit

# Phase 3 + core backend tests
cd backend && .venv/bin/python -m pytest \
  tests/test_phase3_validation.py \
  tests/test_recovery.py \
  tests/test_pin_security.py \
  tests/test_identity_lock.py \
  tests/test_event_mode.py \
  tests/test_participant_privacy.py \
  tests/test_dissolution.py \
  tests/test_checkpoint_jump.py \
  tests/test_developer_mode_gating.py \
  tests/test_participant_build_audit.py \
  -q

# Route prune (post-build, mirrors Build-Participant.ps1)
rm -rf frontend/out/admin frontend/out/market-screen frontend/out/developer
```

### Windows build (manual — not executed here)

```powershell
.\scripts\offline\Build-Participant.ps1 -TimelineKey "<key>" -EventPin "<pin>"
.\scripts\offline\audit-participant-build.ps1
```

---

## Phase 4 Not Started

Per instructions: participant UI redesign, projector build, and final packaging polish remain deferred unless required to clear blockers above.

# TRADEVERSE — Final Implementation Audit

**Phase:** 1 (audit only — no application code modified)  
**Date:** 2026-08-25  
**Scope:** Full repository inspection against the final production hardening specification  
**Approved plan corrections incorporated:** news target (no unconditional LTP snap), chronological recovery, genuinely self-contained Windows build

---

## Executive Summary

The repository has a working offline participant **prototype** (Python + Node launcher, SQLite, static UI export) with partial event-mode gating, privacy tests, and a developer dashboard. It is **not yet production-ready** for a 50-participant college event.

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Packaging / self-contained exe | 3 | 2 | 2 | 2 |
| Recovery / simulation clock | 2 | 3 | 2 | 0 |
| News / price authority | 1 | 2 | 2 | 0 |
| API / WebSocket information leaks | 0 | 6 | 3 | 1 |
| Identity / PIN security | 0 | 2 | 1 | 0 |
| Cloud / network (participant runtime) | 0 | 2 | 4 | 8 |
| UI / build / TypeScript | 0 | 2 | 4 | 3 |
| Documentation conflicts | 0 | 3 | 2 | 0 |
| **Total findings** | **6** | **22** | **18** | **14** |

**Top blockers before event day:**
1. No `TRADEVERSE.exe` — participants still need Python + Node/npm
2. No wall-clock recovery or chronological missed-event catch-up
3. Market pulse directly mutates LTP, undermining news authority
4. Participant package build script broken (`Build-Participant-Zip.bat` missing required params)
5. Frontend production build fails (ESLint)

---

## Approved Corrections (Design Constraints for Phase 2+)

These override any prior plan language:

### Correction 1 — News Price Movement
- News establishes an **authoritative target** (`fair_value`), not an unconditional instant LTP jump
- Flow: NEWS → sector ±5% target → set `fair_value` → AI ticks move LTP toward target → price reaches target within tolerance
- No unrealistic instant 10–20% visible jumps unless timeline explicitly requires them

### Correction 2 — Recovery
- Process missed simulation time **chronologically** (events + AI ticks in order)
- Do NOT set clock to final time and jump to end state
- Do NOT rewind financial state; do NOT duplicate events
- IPO/news/dissolution must remain deterministic and idempotent

### Correction 3 — Self-Contained Windows Build
- `TRADEVERSE.exe` → bundled Tauri frontend → bundled `tradeverse-backend.exe` → local SQLite
- Localhost backend is allowed (same machine only)
- Zero external machine communication

---

## 1. Packaging & Self-Contained Participant Build

### AUDIT-001 — No production participant executable
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`scripts/offline/start-participant.ps1`](scripts/offline/start-participant.ps1), [`Start-TRADEVERSE.bat`](Start-TRADEVERSE.bat), [`desktop/`](desktop/) |
| **Explanation** | Participant flow requires system Python 3.11–3.13, Node.js, npm, and first-run `pip install` into `%LOCALAPPDATA%\Tradeverse\backend-venv`. No PyInstaller spec exists. Tauri skeleton (`desktop/src-tauri/`) has empty `beforeBuildCommand`, no sidecar, dev URL `http://127.0.0.1:3000/terminal`, empty icon array. |
| **Proposed fix** | Implement PyInstaller `tradeverse-backend.spec`, Tauri sidecar spawn in `main.rs`, `Build-Participant.ps1` producing `participant-build/TRADEVERSE.exe`. |
| **Requirement conflict** | Direct conflict with spec §3, §35, §36, §47 (no Python/Node/npm on participant machine). |

### AUDIT-002 — `Build-Participant-Zip.bat` cannot succeed
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`Build-Participant-Zip.bat`](Build-Participant-Zip.bat), [`scripts/offline/build-share-package.ps1`](scripts/offline/build-share-package.ps1) |
| **Explanation** | `build-share-package.ps1` requires mandatory `-TimelineKey` and `-EventPin`. Bat file invokes script with no arguments → immediate failure. |
| **Proposed fix** | Delegate to `Build-Participant.ps1` with env/prompt params; fix organizer API in `participant_package_service.py` similarly. |
| **Requirement conflict** | Blocks spec §36 automated participant package build. |

### AUDIT-003 — Organizer zip API has same missing-params bug
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`backend/app/services/participant_package_service.py`](backend/app/services/participant_package_service.py), [`backend/app/api/routes/simulation_local.py`](backend/app/api/routes/simulation_local.py) |
| **Explanation** | `build_participant_zip()` calls PowerShell without `-TimelineKey`/`-EventPin`. |
| **Proposed fix** | Read keys from organizer settings; return 400 if missing. |
| **Requirement conflict** | Blocks organizer self-service packaging. |

### AUDIT-004 — Frontend production build fails
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`frontend/src/app/terminal/page.tsx`](frontend/src/app/terminal/page.tsx) (line 160), [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) (lines 3, 25) |
| **Explanation** | `PARTICIPANT_BUILD=1 npm run build` fails ESLint: unused `reloadCharts`, `isAuthError`, `isProductionBuild`. Static export cannot ship. |
| **Proposed fix** | Remove or use unused bindings in Phase 4/5. |
| **Requirement conflict** | Spec §47 frontend production build must succeed. |

### AUDIT-005 — Participant audit script not wired into build
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`scripts/offline/audit-participant-build.ps1`](scripts/offline/audit-participant-build.ps1) |
| **Explanation** | Audit exists but is never called from `build-share-package.ps1`, CI, or organizer API. Forbidden patterns incomplete vs spec §37. |
| **Proposed fix** | Run audit after package assembly; expand forbidden list (`CRASH`, `RECOVERY`, `PHASE 1-4`, `AI_TICK`, `stop_loss`, etc.). |
| **Requirement conflict** | Spec §37 participant build audit gate. |

### AUDIT-006 — Developer artifacts still copied into participant zip
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`scripts/offline/build-share-package.ps1`](scripts/offline/build-share-package.ps1) `excludePaths` |
| **Explanation** | Static routes pruned (`admin`, `market-screen`, `developer`) but source tree still includes `developer-launch.bat`, `start-developer.ps1`, `backend/app/api/routes/developer.py`, stale `HOW-TO-RUN.md`. |
| **Proposed fix** | Extend exclude list; audit scans full package tree. |
| **Requirement conflict** | Spec §2B — developer functionality must not merely be hidden. |

### AUDIT-007 — Tauri launcher still requires Python/Node
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`desktop/launcher.mjs`](desktop/launcher.mjs), [`desktop/src-tauri/tauri.conf.json`](desktop/src-tauri/tauri.conf.json) |
| **Explanation** | `launcher.mjs` creates venv, runs pip, optionally spawns `npm run dev`. Not a bundled runtime. |
| **Proposed fix** | Replace with Tauri sidecar + static `frontend/out`; remove Node dependency from participant path. |
| **Requirement conflict** | Correction 3 / spec §3. |

### AUDIT-008 — PyInstaller documented but not implemented
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | [`HOW-TO-RUN.md`](HOW-TO-RUN.md) |
| **Explanation** | Docs reference one-file exe; no spec in repo. |
| **Proposed fix** | Add `backend/tradeverse-backend.spec` or remove misleading doc. |
| **Requirement conflict** | Spec §3. |

### AUDIT-009 — Debug instrumentation in participant paths
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`scripts/offline/start-participant.ps1`](scripts/offline/start-participant.ps1) (lines 146–161), [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) (lines 253–266), [`frontend/src/hooks/useGlobalResetPoll.ts`](frontend/src/hooks/useGlobalResetPoll.ts) |
| **Explanation** | Writes `debug-ac2555.log`; POSTs to `http://127.0.0.1:7751/ingest/...`. Harmless offline but unprofessional in distribution. |
| **Proposed fix** | Remove or gate behind `DEVELOPER_MODE`. |
| **Requirement conflict** | None critical; hygiene issue. |

### AUDIT-010 — Hardcoded Vercel URL in participant launcher
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | [`scripts/offline/start-participant.ps1`](scripts/offline/start-participant.ps1) line 412 |
| **Explanation** | `$marketUrl = "https://frontend-azure-three-51.vercel.app/market-screen"` printed in non-event mode. |
| **Proposed fix** | Remove external URL; projector is separate build. |
| **Requirement conflict** | Spec §1 — no Vercel dependency in participant runtime. |

---

## 2. Recovery & Authoritative Simulation Clock

### AUDIT-011 — `clock_anchor_real` written but never read
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`backend/app/models/simulation_state.py`](backend/app/models/simulation_state.py), [`backend/app/services/simulation_controller.py`](backend/app/services/simulation_controller.py) (lines 174, 251) |
| **Explanation** | Anchor set on start, cleared on reset. No code computes elapsed from `(now - anchor)`. `paused_at_real` also never read. |
| **Proposed fix** | Implement `recovery_service.sync_authoritative_elapsed()` using anchor + speed; persist `anchor_sim_elapsed_sec` at start. |
| **Requirement conflict** | Spec §7–9, Correction 2. |

### AUDIT-012 — No wall-clock catch-up on reopen/crash
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`backend/app/services/simulation_engine.py`](backend/app/services/simulation_engine.py) (lines 172–191), [`backend/app/main.py`](backend/app/main.py) |
| **Explanation** | Engine only advances via 0.25s asyncio deltas from stored `sim_elapsed_sec`. 5 min downtime → sim stays 5 min behind wall clock. No startup reconciliation hook. |
| **Proposed fix** | On engine start + bootstrap: compute authoritative elapsed, run chronological catch-up. |
| **Requirement conflict** | Spec §8 — closing app must not pause market. |

### AUDIT-013 — No chronological missed-event processing
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/services/event_processor.py`](backend/app/services/event_processor.py), no `recovery_service.py` |
| **Explanation** | Timeline events process when `sim_elapsed` crosses offsets incrementally. No step-by-step replay of NEWS → AI TICK → NEWS sequence after downtime. Dev `_fast_forward_to` exists but is developer-only. |
| **Proposed fix** | Recovery loop: for each sim-time step up to authoritative elapsed, run due events then AI tick if 30s boundary crossed. |
| **Requirement conflict** | Correction 2 — must not jump to 01:16 final state. |

### AUDIT-014 — Session bootstrap does not trigger catch-up
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/api/routes/session.py`](backend/app/api/routes/session.py) `/bootstrap` |
| **Explanation** | Returns snapshot only; does not fast-forward missed sim time or events. |
| **Proposed fix** | Call recovery service before building bootstrap payload. |
| **Requirement conflict** | Spec §7 recovery flow. |

### AUDIT-015 — AI tick catch-up limited to one per loop iteration
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/simulation_engine.py`](backend/app/services/simulation_engine.py) (lines 260–261) |
| **Explanation** | After large elapsed jump, only one AI tick fires per 0.25s loop. Recovery must backfill all missed 30s intervals. |
| **Proposed fix** | Recovery service runs AI ticks in chronological loop during catch-up. |
| **Requirement conflict** | Correction 2 example (01:12, 01:13, 01:15 AI ticks). |

### AUDIT-016 — Failed timeline events retry forever
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/event_processor.py`](backend/app/services/event_processor.py) (lines 76–85) |
| **Explanation** | Failed events stay `PENDING`; retried every tick with no `FAILED` terminal state. |
| **Proposed fix** | Add `FAILED` status; log and skip after N attempts. |
| **Requirement conflict** | Spec §33 crash safety / idempotency. |

### AUDIT-017 — Resume overwrites anchor without elapsed snapshot
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/services/simulation_controller.py`](backend/app/services/simulation_controller.py) line 174 |
| **Explanation** | `clock_anchor_real = datetime.now()` on every start/resume without pairing to `anchor_sim_elapsed_sec`, making catch-up math impossible. |
| **Proposed fix** | Store both anchor wall time and anchor sim elapsed at start; only reset anchor on fresh event start. |
| **Requirement conflict** | Spec §8 authoritative clock. |

---

## 3. News & Price Authority

### AUDIT-018 — News only soft-nudges fair_value (35% multiplier)
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/services/news_service.py`](backend/app/services/news_service.py) (lines 87–105) |
| **Explanation** | `release_news` applies `factor = 1 + (pct * news_fundamental_multiplier / 100 * 0.35)` to fair_value. Comment says "does NOT set LTP". Target not fully authoritative. |
| **Proposed fix** | Set `fair_value = target_price` from `news_impact_resolver` ±5% formula. Strengthen AI pull toward target. No unconditional LTP snap (per Correction 1). |
| **Requirement conflict** | Spec §11–12; Correction 1. |

### AUDIT-019 — Market pulse directly mutates LTP
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **File** | [`backend/app/services/market_pulse_service.py`](backend/app/services/market_pulse_service.py) (line 79), [`backend/app/services/simulation_engine.py`](backend/app/services/simulation_engine.py) (lines 238–251) |
| **Explanation** | Every 3s (local mode) pulse sets `stock.last_traded_price` without trades. Competes with news/AI hierarchy. Uses internal phase bias (`PHASE 1`–`PHASE 4`). |
| **Proposed fix** | Disable pulse in `participant_event_mode`. Developer mode may retain for chart animation. |
| **Requirement conflict** | Spec §13 — remove pulse as primary price driver in participant event mode. |

### AUDIT-020 — `effective_impact()` uses wall-clock decay, not sim time
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/news_service.py`](backend/app/services/news_service.py) (lines 32–45) |
| **Explanation** | Impact decay based on `datetime.now() - released_at`, not simulation elapsed. After recovery catch-up, decay may be wrong. |
| **Proposed fix** | Use sim-time for decay in event mode, or rely on fair_value target model instead of decay for participant mode. |
| **Requirement conflict** | Spec §8 sim-time authority. |

### AUDIT-021 — Duplicate `compute_stock_impacts_for_news` in event processor
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | [`backend/app/services/event_processor.py`](backend/app/services/event_processor.py), [`backend/app/services/news_service.py`](backend/app/services/news_service.py) |
| **Explanation** | `_handle_news` calls impact computation after `release_news` already did. |
| **Proposed fix** | Remove duplicate call. |
| **Requirement conflict** | None; code hygiene. |

### AUDIT-022 — News re-release not idempotent
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/news_service.py`](backend/app/services/news_service.py) (lines 72–105) |
| **Explanation** | No early return if `is_released`; re-calling re-applies fair_value multiplier. |
| **Proposed fix** | Guard: if already released, return existing event unchanged. |
| **Requirement conflict** | Spec §42 event idempotency; Correction 2. |

### AUDIT-023 — No automated news hierarchy validation test
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | Missing `backend/tests/test_news_authority.py` |
| **Explanation** | No test verifying ±5% stock variation, target reach via AI, or participant order cannot override scenario. |
| **Proposed fix** | Add test per spec §40. |
| **Requirement conflict** | Spec §40, §47. |

---

## 4. API, WebSocket & Information Leaks

### AUDIT-024 — `GET /ipos` exposes all IPOs including future
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/api/routes/ipos.py`](backend/app/api/routes/ipos.py) (lines 52–54) |
| **Explanation** | Unauthenticated list returns all IPOs with `application_start`, `application_end`, `listing_time`, `total_lots`, `winning_lots`. |
| **Proposed fix** | Participant DTO: only `open` or `listed` IPOs visible at current sim time; strip future schedule fields. |
| **Requirement conflict** | Spec §16, §27 — no future IPO discovery. |

### AUDIT-025 — `GET /stocks` exposes `fair_value` and internal fields
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/schemas/__init__.py`](backend/app/schemas/__init__.py) `StockRead` (line 132), [`backend/app/api/routes/stocks.py`](backend/app/api/routes/stocks.py) |
| **Explanation** | `StockRead` includes `fair_value`, `starting_price`, etc. No participant-safe filter in event mode. |
| **Proposed fix** | `ParticipantStockRead` schema stripping internal pricing model fields. |
| **Requirement conflict** | Spec §16 participant information filtering. |

### AUDIT-026 — `GET /leaderboard` ungated in event mode
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/api/routes/market.py`](backend/app/api/routes/market.py) (lines 47–61) |
| **Explanation** | Leaderboard endpoint always mounted; not blocked when `participant_event_mode=true`. Bootstrap correctly omits it; direct API call still works. |
| **Proposed fix** | Return 404 in event mode. |
| **Requirement conflict** | Spec §20 — no live leaderboard in participant mode. |

### AUDIT-027 — WebSocket broadcasts `AI_TICK`, `LEADERBOARD_UPDATE`, `MARKET_PULSE`
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/services/simulation_engine.py`](backend/app/services/simulation_engine.py) (lines 70–71, 249–250), [`backend/app/realtime/ws_manager.py`](backend/app/realtime/ws_manager.py) |
| **Explanation** | All clients receive internal events. `ws_manager` only filters private wallet/portfolio events. |
| **Proposed fix** | Suppress forbidden event types in event mode at broadcast source or manager. |
| **Requirement conflict** | Spec §26 WebSocket safety. |

### AUDIT-028 — Stop-loss / take-profit API still mounted
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/api/routes/conditionals.py`](backend/app/api/routes/conditionals.py), [`backend/app/main.py`](backend/app/main.py) line 103 |
| **Explanation** | Conditional order routes always included; no `participant_event_mode` gate. UI may not expose them but API allows creation. |
| **Proposed fix** | Return 404 for all `/conditionals` routes in event mode. |
| **Requirement conflict** | Spec §19 — participants do not have stop loss / take profit. |

### AUDIT-029 — `TIMELINE_DECRYPT_KEY` baked into participant `.env`
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/scripts/build_event_env.py`](backend/scripts/build_event_env.py) (line 39) |
| **Explanation** | Participant package contains decrypt key; any participant can decrypt full timeline and discover future events. |
| **Proposed fix** | Build-time decrypt + embed timeline in backend binary/SQLite seed; omit key from participant `.env`. |
| **Requirement conflict** | Spec §16, §27 — no future timeline discovery. |

### AUDIT-030 — Plaintext `EVENT_PIN` in participant `.env`
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/scripts/build_event_env.py`](backend/scripts/build_event_env.py) (line 40), [`backend/app/api/routes/auth.py`](backend/app/api/routes/auth.py) (lines 122–126) |
| **Explanation** | PIN stored plaintext; trivial to discover in config file. |
| **Proposed fix** | Ship `EVENT_PIN_HASH` only; validate with bcrypt/scrypt locally. |
| **Requirement conflict** | Spec §5 PIN security. |

### AUDIT-031 — Developer routes gated but simulation_local organizer endpoints remain
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/api/routes/simulation_local.py`](backend/app/api/routes/simulation_local.py) |
| **Explanation** | `/organizer/*` gated to localhost + passkey. Acceptable for dev but must not ship callable paths in participant exe without passkey. |
| **Proposed fix** | Disable organizer routes entirely in participant build (`DEVELOPER_MODE=false` + compile-time or env). |
| **Requirement conflict** | Spec §21 — no participant admin. |

### AUDIT-032 — `useGlobalResetPoll` dead code references Supabase
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | [`frontend/src/hooks/useGlobalResetPoll.ts`](frontend/src/hooks/useGlobalResetPoll.ts) |
| **Explanation** | Polls Supabase event control; not imported anywhere. Still in bundle if not tree-shaken. |
| **Proposed fix** | Delete file or exclude from participant build. |
| **Requirement conflict** | Spec §1 cloud removal. |

---

## 5. Identity & Persistence

### AUDIT-033 — Identity lock bypass via `humans[0]` fallback
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`backend/app/api/routes/auth.py`](backend/app/api/routes/auth.py) (lines 69–78) |
| **Explanation** | New `session_id` rebinds first human trader and overwrites `name`. User can change name and keep same portfolio. |
| **Proposed fix** | Create trader once; lock name; reject name change on rejoin; require matching `session_id`. |
| **Requirement conflict** | Spec §6 participant identity lock. |

### AUDIT-034 — Financial state in SQLite (good) but session identity in localStorage
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts), [`backend/app/api/routes/auth.py`](backend/app/api/routes/auth.py) |
| **Explanation** | Portfolio in SQLite ✅. `session_id` and token in `localStorage` — clearing storage triggers AUDIT-033 bypass. |
| **Proposed fix** | Bind identity to SQLite trader row; recovery restores same trader by machine-local ID file. |
| **Requirement conflict** | Spec §2, §6 — identity must survive recovery. |

### AUDIT-035 — SQLite persistence exists and is used correctly
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/app/core/config.py`](backend/app/core/config.py) (`local_instance_mode` → SQLite), [`scripts/offline/start-participant.ps1`](scripts/offline/start-participant.ps1) |
| **Explanation** | `%LOCALAPPDATA%\Tradeverse\data\trader.db` used. Meets spec §2 local persistence requirement. |
| **Proposed fix** | Ensure PyInstaller backend uses same path. |
| **Requirement conflict** | None — foundation is correct. |

---

## 6. Event Idempotency (IPO / Dissolution)

### AUDIT-036 — Timeline checkpoint idempotency works
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/app/services/event_processor.py`](backend/app/services/event_processor.py), [`backend/tests/test_timeline_idempotency.py`](backend/tests/test_timeline_idempotency.py) |
| **Explanation** | `EXECUTED` status prevents replay. Tests exist. |
| **Proposed fix** | Extend to recovery catch-up path. |
| **Requirement conflict** | None. |

### AUDIT-037 — IPO close/allot/list handlers fail on replay
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/ipo_service.py`](backend/app/services/ipo_service.py) (lines 138–139, 154–155, 301–304) |
| **Explanation** | Second call raises `IPOServiceError` if status already advanced. Recovery re-processing could fail unless handlers are idempotent. |
| **Proposed fix** | Return success no-op when already in target state. |
| **Requirement conflict** | Correction 2 — no duplicate allocation; spec §17, §42. |

### AUDIT-038 — Dissolution idempotency works
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/app/services/dissolution_service.py`](backend/app/services/dissolution_service.py), [`backend/tests/test_dissolution.py`](backend/tests/test_dissolution.py) |
| **Explanation** | `already_dissolved` short-circuit exists. |
| **Proposed fix** | Verify in recovery integration test. |
| **Requirement conflict** | None. |

### AUDIT-039 — IPO personal allotment in local event mode
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/ipo_service.py`](backend/app/services/ipo_service.py) (lines 148–150, 231–293) |
| **Explanation** | `local_instance_mode` uses per-trader lottery (`allot_ipo_personal`). Intentional for independent laptops; differs from shared-server lottery. |
| **Proposed fix** | Document as expected for offline event; ensure single authoritative algorithm per participant instance. |
| **Requirement conflict** | Spec §17 "ONE authoritative algorithm" — OK per-machine, not globally. |

---

## 7. Cloud / Network Dependencies

### AUDIT-040 — Leaderboard sync disabled in event mode (good)
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/app/services/leaderboard_sync_service.py`](backend/app/services/leaderboard_sync_service.py) (lines 131–134) |
| **Explanation** | `leaderboard_sync_configured()` returns false when `participant_event_mode`. |
| **Proposed fix** | Also skip `start_leaderboard_sync()` in `main.py` for clarity. |
| **Requirement conflict** | None. |

### AUDIT-041 — Supabase code remains in shared frontend bundle
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) |
| **Explanation** | Supabase fetch functions bundled; gated dead at runtime via `hasRemoteLeaderboard()`. Strings may fail audit. |
| **Proposed fix** | Split dev-only API module; tree-shake from participant build. |
| **Requirement conflict** | Spec §37 audit strings. |

### AUDIT-042 — Documentation contradicts participant offline model
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`EVENT-DAY.md`](EVENT-DAY.md), [`Build-Participant-Zip.bat`](Build-Participant-Zip.bat), [`HOW-TO-RUN.md`](HOW-TO-RUN.md) vs [`PARTICIPANT-README.md`](PARTICIPANT-README.md) |
| **Explanation** | `EVENT-DAY.md` tells participants to add Supabase keys; bat says share Supabase URL; `HOW-TO-RUN.md` describes LAN/ngrok. `PARTICIPANT-README.md` correctly says no network. |
| **Proposed fix** | Mark cloud docs obsolete; single `FINAL_EVENT_GUIDE.md` source of truth. |
| **Requirement conflict** | Spec §45 documentation. |

### AUDIT-043 — TIMELINE_DECRYPT_KEY doc conflict
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`EVENT-DAY.md`](EVENT-DAY.md), [`PARTICIPANT-README.md`](PARTICIPANT-README.md), [`build_event_env.py`](backend/scripts/build_event_env.py) |
| **Explanation** | Some docs say announce key verbally; build script bakes key into zip. |
| **Proposed fix** | Align with build-time embed strategy (AUDIT-029). |
| **Requirement conflict** | Spec §5, §16. |

### AUDIT-044 — PostgreSQL/cloud paths exist but gated off for participant
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **File** | [`backend/app/core/config.py`](backend/app/core/config.py), `docker-compose*.yml`, cloud deploy docs |
| **Explanation** | Cloud infrastructure is developer/deploy only. `local_instance_mode` forces SQLite. |
| **Proposed fix** | No code removal needed; document as developer-only. |
| **Requirement conflict** | None for participant if `LOCAL_INSTANCE_MODE=true`. |

---

## 8. UI / Participant Experience

### AUDIT-045 — Terminal UI has extra panels vs final spec
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`frontend/src/app/terminal/page.tsx`](frontend/src/app/terminal/page.tsx) |
| **Explanation** | Includes `WalletPanel`, `showWallet`, `showNewsBriefs`, IPO lot controls, WS status display, dissolved stocks sidebar. Spec §10/§31 wants minimal: top bar, sector sidebar, trade panel, news. |
| **Proposed fix** | Simplify in Phase 4; keep IPO application only when timeline opens IPO. |
| **Requirement conflict** | Spec §10, §31 final participant UI. |

### AUDIT-046 — StockSidebar sector expand/collapse exists (good)
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`frontend/src/components/StockSidebar.tsx`](frontend/src/components/StockSidebar.tsx) |
| **Explanation** | Sector groups with `sector_change_pct`, expand/collapse, scrollable list. Matches spec §10. |
| **Proposed fix** | Wire as primary navigation; remove redundant stock list if any. |
| **Requirement conflict** | None. |

### AUDIT-047 — Event complete screen exists (good)
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`frontend/src/components/terminal/EventCompleteScreen.tsx`](frontend/src/components/terminal/EventCompleteScreen.tsx), [`frontend/src/app/terminal/page.tsx`](frontend/src/app/terminal/page.tsx) |
| **Explanation** | Shows final P&L when `simStatus === "completed"`. |
| **Proposed fix** | Block restart/re-entry to trading after completion. |
| **Requirement conflict** | Spec §32 — partial; verify persistence on reopen. |

### AUDIT-048 — PIN gate and countdown exist (good)
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`frontend/src/components/terminal/PinGateOverlay.tsx`](frontend/src/components/terminal/PinGateOverlay.tsx), [`frontend/src/components/terminal/StartCountdown.tsx`](frontend/src/components/terminal/StartCountdown.tsx) |
| **Explanation** | PIN + name + countdown flow implemented. |
| **Proposed fix** | Recovery path: skip countdown on resume; PIN only. |
| **Requirement conflict** | Spec §4 — partial (recovery flow missing). |

### AUDIT-049 — Market projector exposes internal information
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`frontend/src/app/market-screen/page.tsx`](frontend/src/app/market-screen/page.tsx) |
| **Explanation** | Shows `current_phase`, `SectorImpactMatrix`, `OrganizerDebugPanel`, Supabase leaderboard, remote probes. Pruned from participant zip but projector build needs separate public-only variant. |
| **Proposed fix** | `Build-Projector.ps1` with `PROJECTOR_MODE`; participant-safe APIs only. |
| **Requirement conflict** | Spec §23 market projector. |

---

## 9. TypeScript & Build Quality

### AUDIT-050 — TypeScript errors block clean typecheck
| Field | Value |
|-------|-------|
| **Severity** | High |
| **File** | [`frontend/src/app/market-screen/page.tsx`](frontend/src/app/market-screen/page.tsx) line 94, [`frontend/src/app/terminal/page.tsx`](frontend/src/app/terminal/page.tsx) line 87, [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) line 577 |
| **Explanation** | `released_at: null` vs `undefined`; `ticker` undefined vs `string|null`; missing `supabaseEventControlTable` on runtime config type. |
| **Proposed fix** | Shared `frontend/src/types/api.ts`; normalize at API boundary with `?? undefined`. |
| **Requirement conflict** | Spec §24 — no `any`/`as` shortcuts. |

### AUDIT-051 — `developer/page.tsx` nullable news fixed
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`frontend/src/app/developer/page.tsx`](frontend/src/app/developer/page.tsx) |
| **Explanation** | Prior fix uses `?? undefined` for nullable fields. No current tsc errors. |
| **Proposed fix** | Apply same pattern to market-screen. |
| **Requirement conflict** | None. |

### AUDIT-052 — Participant privacy tests exist (good)
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/tests/test_participant_privacy.py`](backend/tests/test_participant_privacy.py), [`backend/tests/test_event_mode.py`](backend/tests/test_event_mode.py), [`backend/tests/test_participant_build_audit.py`](backend/tests/test_participant_build_audit.py) |
| **Explanation** | Tests verify news/status shape, no phase in bootstrap, developer gating. |
| **Proposed fix** | Extend for IPO/stock/WS leaks. |
| **Requirement conflict** | None — good foundation. |

---

## 10. Internal Regime Labels (Must Not Reach Participants)

### AUDIT-053 — Phase labels in backend services (internal only — OK if filtered)
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **File** | [`backend/app/services/timeline_service.py`](backend/app/services/timeline_service.py), [`backend/app/services/market_pulse_service.py`](backend/app/services/market_pulse_service.py), [`backend/app/seed/tradeverse_universe.json`](backend/app/seed/tradeverse_universe.json) |
| **Explanation** | `PHASE 1 — EUPHORIA`, `CRASH`, `RECOVERY` used internally for AI/pulse bias. Must never appear in participant API/WS/UI. |
| **Proposed fix** | Keep internal; verify `participant_status_dict` and `participant_news_dict` never expose. Audit participant build strings. |
| **Requirement conflict** | Spec §15, §30 — internal OK, exposure not OK. |

### AUDIT-054 — `participant_status_dict` correctly strips phase
| Field | Value |
|-------|-------|
| **Severity** | Low (positive) |
| **File** | [`backend/app/services/simulation_clock.py`](backend/app/services/simulation_clock.py) (lines 65–76) |
| **Explanation** | Participant status omits `current_phase` and `sim_speed_multiplier`. |
| **Proposed fix** | None. |
| **Requirement conflict** | None. |

---

## 11. Conflicts With Final Requirements (Summary)

| Requirement | Current State | Blocking Findings |
|-------------|---------------|-------------------|
| Self-contained `TRADEVERSE.exe` | Zip + bat + Python/Node | AUDIT-001, 002, 003, 007 |
| Offline / no cloud | Runtime mostly local; docs wrong | AUDIT-042, 043 |
| Wall-clock recovery | Not implemented | AUDIT-011, 012, 013, 014, 017 |
| Chronological catch-up | Not implemented | AUDIT-013, 015 |
| News authoritative (no instant snap) | Soft nudge + pulse overrides | AUDIT-018, 019 |
| News ±5% formula | Implemented correctly | None — preserve [`news_impact_resolver.py`](backend/app/services/news_impact_resolver.py) |
| No future info leaks | IPO/timeline key/stocks leak | AUDIT-024, 025, 029 |
| Identity lock | Bypass exists | AUDIT-033 |
| PIN security | Plaintext in .env | AUDIT-030 |
| No stop-loss in participant mode | API mounted | AUDIT-028 |
| No leaderboard | API ungated | AUDIT-026 |
| WS participant-safe | AI_TICK etc. broadcast | AUDIT-027 |
| Production build green | ESLint fails | AUDIT-004, 050 |
| Developer/projector separation | Partial (route prune) | AUDIT-006, 049 |
| 3-hour auto event + final P&L | Partially implemented | AUDIT-012, 047 |
| Event idempotency on recovery | Partial | AUDIT-022, 037 |

---

## 12. Recommended Phase 2 Implementation Order

Based on dependency and risk:

1. **Recovery service** (AUDIT-011–017) — unblocks event correctness
2. **News authority + disable pulse** (AUDIT-018, 019, 022) — per Correction 1
3. **API/WS hardening** (AUDIT-024–031) — security before distribution
4. **Identity + PIN hash** (AUDIT-033, 030) — participant trust
5. **Timeline key build-time embed** (AUDIT-029) — prevent future event discovery
6. **Self-contained exe pipeline** (AUDIT-001–003, 007) — per Correction 3
7. **Build/TS fixes** (AUDIT-004, 005, 050) — ship gate
8. **UI simplification + projector** (AUDIT-045, 049) — Phase 4

---

## 13. What Is Already Working (Do Not Rewrite)

- SQLite local persistence for portfolio, trades, simulation state
- Timeline event processor with ordered execution and `EXECUTED` status
- `news_impact_resolver.py` ±5% sector→stock variation (deterministic)
- `participant_news_dict` / `participant_status_dict` privacy shaping
- Developer mode route gating (`DEVELOPER_MODE`, `developer_guard.py`)
- Static participant frontend export with route pruning
- PIN gate UI, countdown, event complete screen
- AI tick interval constant (30 sim seconds)
- Dissolution idempotency
- Core matching engine / order book (preserve)

---

## 14. Phase 1 Completion Statement

- **Application code modified:** None
- **Audit document created:** This file
- **Plan updated:** Corrections 1–3 incorporated in plan Phase 2A, 2F, 3B
- **Ready for Phase 2:** Pending explicit approval

---

*End of Phase 1 audit. Awaiting approval before beginning Phase 2 implementation.*

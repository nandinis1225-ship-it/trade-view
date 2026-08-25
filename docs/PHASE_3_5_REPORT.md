# Phase 3.5 — Production Packaging Report

**Date:** 2026-08-25  
**Scope:** Offline participant desktop packaging (Windows + macOS pipelines, timeline protection, Tauri shell, audits, tests)

---

## Verdict

| Stage | Status |
|-------|--------|
| **SOURCE READY** | **YES** — packaging code, scripts, tests, and docs in repo |
| **PACKAGE BUILT** | **NO** — requires Windows/macOS build machines (Linux CI cannot produce `.exe`/`.app`) |
| **CLEAN-MACHINE VERIFIED** | **NO** |
| **OFFLINE VERIFIED** | **NO** |
| **RECOVERY VERIFIED** | **NO** (on packaged binary) |
| **EVENT READY** | **NO** |

Phase 3.5 implementation is complete at the **source** level. Actual packaged applications must be built and tested on real Windows and macOS hardware before event distribution.

---

## Implementation summary

### Timeline protection (replaces Fernet / `TIMELINE_DECRYPT_KEY`)

- New `timeline_protection.py`: build-time `tradeverse_timeline.json` → `tradeverse_timeline.pkg` (zlib + embedded obfuscation)
- No participant decrypt key; timeline embedded in PyInstaller backend binary
- `protect_timeline.py` verifies **64 events** before packaging
- Participant packages must not contain plaintext JSON

### Packaged backend

- `run_backend.py` — PyInstaller entry, packaged cwd, localhost defaults
- `app/paths.py` — resolves `ui/` static dir beside sidecar; configures packaged runtime
- `main.py` — serves static UI from packaged `ui/` directory
- `config.py` — macOS SQLite path (`~/Library/Application Support/Tradeverse/data/`)
- `tradeverse-backend.spec` — bundles `.pkg` + `tradeverse_universe.json`

### Desktop wrapper (Tauri 2)

- `desktop/src-tauri/src/main.rs` — cross-platform backend spawn, health wait, webview → `/terminal`, cleanup on exit
- `tauri.conf.json` — Windows (msi/nsis) + macOS (app/dmg) targets

### Build pipelines

- `scripts/offline/Build-Participant.ps1` → `participant-build/windows/`
- `scripts/offline/build-participant-macos.sh` → `participant-build/macos/`
- `scripts/offline/audit-participant-build.ps1` / `.sh` — forbidden content scan
- `build_event_env.py` — event PIN hash only (no timeline key)

---

## Files created

| File | Purpose |
|------|---------|
| `backend/app/services/timeline_protection.py` | Timeline obfuscation load/protect |
| `backend/app/paths.py` | Packaged static UI + runtime setup |
| `backend/scripts/protect_timeline.py` | Build-time timeline protection CLI |
| `backend/tests/test_phase35_packaging.py` | Packaging unit/integration tests |
| `scripts/offline/build-participant-macos.sh` | macOS build pipeline |
| `scripts/offline/audit-participant-build.sh` | macOS/Linux package audit |
| `docs/PHASE_3_5_PRODUCTION_GUIDE.md` | Build and verification guide |
| `docs/PHASE_3_5_REPORT.md` | This report |
| `desktop/src-tauri/icons/icon.ico` | Tauri icon (from favicon) |

## Files modified

| File | Change |
|------|--------|
| `backend/app/services/timeline_crypto.py` | Shim → `timeline_protection` (no Fernet) |
| `backend/app/services/timeline_service.py` | Load via `timeline_protection` |
| `backend/scripts/build_event_env.py` | Removed `--timeline-key` |
| `backend/scripts/encrypt_timeline.py` | Deprecated |
| `backend/run_backend.py` | Packaged runtime configuration |
| `backend/app/main.py` | Packaged static UI path |
| `backend/app/core/config.py` | macOS DB path |
| `backend/tradeverse-backend.spec` | Bundle `.pkg` not baked JSON |
| `desktop/src-tauri/src/main.rs` | Full participant shell |
| `desktop/src-tauri/Cargo.toml` | Added `ureq` for health check |
| `desktop/src-tauri/tauri.conf.json` | macOS + Windows bundle targets |
| `scripts/offline/Build-Participant.ps1` | Phase 3.5 pipeline (no timeline key) |
| `scripts/offline/audit-participant-build.ps1` | Updated forbidden patterns |
| `backend/tests/conftest.py` | Production timeline from JSON or `.pkg` |
| `backend/tests/test_phase3_validation.py` | 64-event expectation |
| `backend/app/services/participant_package_service.py` | No timeline key |

---

## Build commands

### Windows

```powershell
.\scripts\offline\Build-Participant.ps1 -EventPin "<EVENT_PIN>"
```

### macOS

```bash
./scripts/offline/build-participant-macos.sh "<EVENT_PIN>"
```

---

## Tests run

```bash
cd backend
.venv/bin/python -m pytest tests/test_phase35_packaging.py -q
.venv/bin/python -m pytest tests/test_phase3_validation.py tests/test_cross_sector_news.py tests/test_recovery.py -q
```

**Result:** Phase 3.5 tests **9 passed, 1 skipped** (`test_production_timeline_event_count` — requires `tradeverse_timeline.json` or `.pkg` on disk). Regression suites **pass**.

---

## Known limitations

1. **Production JSON required on build machine** — `backend/app/seed/tradeverse_timeline.json` must exist locally (gitignored); not committed to repo in this environment
2. **PyInstaller + Tauri not executed here** — Linux CI cannot produce Windows `.exe` or macOS `.app`
3. **Tauri icons** — minimal `icon.ico` only; production builds may want proper multi-resolution icons
4. **Legacy `tradeverse_timeline.enc`** may still exist in repo from earlier work; new pipeline uses `.pkg` only
5. **Obfuscation is not cryptographic** — deters casual inspection only

---

## Remaining blockers

1. Place production `tradeverse_timeline.json` (64 events) on Windows/macOS build machines
2. Run full Windows build + clean-machine offline test
3. Run full macOS build on Mac + clean-machine offline test
4. Verify recovery and final P&L on packaged binaries
5. Code-sign / notarize for distribution (optional, not implemented)

---

## Platform status

| Platform | Pipeline | Binary built | Clean-machine |
|----------|----------|--------------|---------------|
| Windows | **Ready** | **Not in CI** | **Not verified** |
| macOS | **Ready** | **Not in CI** | **Not verified** |

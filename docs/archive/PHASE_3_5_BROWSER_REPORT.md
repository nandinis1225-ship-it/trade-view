# Phase 3.5 Browser Distribution Report

**Date:** 2026-08-25  
**Branch:** `cursor/browser-launcher-9965`  
**Distribution model:** Browser launcher (PyInstaller backend + default browser)  
**Tauri desktop app:** Deferred — files preserved, not required

---

## Status summary

| Area | Status |
|------|--------|
| **SOURCE STATUS** | **IMPLEMENTED** |
| **PACKAGE STATUS** | **NOT BUILT** (requires Windows/macOS build machines) |
| **WINDOWS STATUS** | **SOURCE READY** — `Build-Browser-Participant.ps1` + launchers |
| **MACOS STATUS** | **SOURCE READY** — `build-browser-participant-macos.sh` + launchers |
| **OFFLINE STATUS** | **NOT TESTED** on clean machine (manual checklist pending) |
| **RECOVERY STATUS** | **TESTS PASS** (unit/integration); packaged launcher not tested on hardware |

**EVENT READY: NO** — source implemented; packaged clean-machine and Wi-Fi-off validation pending.

---

## What was implemented

### Browser launchers

| File | Platform |
|------|----------|
| `scripts/offline/launchers/Start-Tradeverse.bat` | Windows |
| `scripts/offline/launchers/Stop-Tradeverse.bat` | Windows |
| `scripts/offline/launchers/Start-Tradeverse.command` | macOS |
| `scripts/offline/launchers/Stop-Tradeverse.command` | macOS |

Behavior:
- Start bundled backend if not already healthy
- Poll `http://127.0.0.1:8765/api/v1/health`
- Open `http://127.0.0.1:8765/terminal` in default browser
- Backend persists after browser close (resume via re-launch + PIN)
- Explicit stop via `Stop-Tradeverse.*`

### Build scripts (no Tauri)

| Script | Output |
|--------|--------|
| `scripts/offline/Build-Browser-Participant.ps1` | `participant-build/windows/TRADEVERSE/` |
| `scripts/offline/build-browser-participant-macos.sh` | `participant-build/macos/TRADEVERSE/` |

Pipeline reuses Phase 3.5:
- Timeline protection (`protect_timeline.py` → `.pkg` in PyInstaller binary)
- `npm run build:participant`
- PyInstaller `tradeverse-backend[.exe]`
- `build_event_env.py` for participant `.env`
- Static UI served by FastAPI (`SERVE_STATIC_UI=true`)

### Backend hardening (distribution only)

- [`backend/run_backend.py`](backend/run_backend.py) — packaged backend refuses `0.0.0.0` bind
- [`backend/app/paths.py`](backend/app/paths.py) — packaged defaults for event mode + admin hidden

### Audits

- `scripts/offline/audit-browser-participant-build.ps1`
- `scripts/offline/audit-browser-participant-build.sh`
- Extended `audit-participant-build.sh` with dev DB checks

### Tests

- `backend/tests/test_browser_launcher_packaging.py` — 13 tests (1 skipped without production timeline)

---

## Package layout (expected)

**Windows** — `participant-build/windows/TRADEVERSE/`:

```
TRADEVERSE/
├── Start-Tradeverse.bat
├── Stop-Tradeverse.bat
├── tradeverse-backend.exe
├── ui/
└── .env
```

**macOS** — `participant-build/macos/TRADEVERSE/`:

```
TRADEVERSE/
├── Start-Tradeverse.command
├── Stop-Tradeverse.command
├── tradeverse-backend
├── ui/
└── .env
```

---

## Tests executed

```bash
cd backend && .venv/bin/python -m pytest tests/test_browser_launcher_packaging.py -q
# Result: 13 passed, 1 skipped

cd frontend && npm run build:participant && npx tsc --noEmit
# Result: PASS (when run as part of gate suite)
```

---

## Regression checks

| Check | Result |
|-------|--------|
| Simulation engine unchanged | **YES** |
| Timeline protection unchanged | **YES** |
| Tauri source preserved | **YES** (`desktop/src-tauri/` untouched) |
| `Build-Participant.ps1` (Tauri path) preserved | **YES** |
| Participant privacy tests | **PASS** |
| Recovery tests | **PASS** |
| Phase 3.5 packaging tests | **PASS** |

---

## Phase 3.5 protected files

| File | Changed? |
|------|----------|
| `scripts/offline/Build-Participant.ps1` | **NO** |
| `scripts/offline/build-participant-macos.sh` | **NO** |
| `scripts/offline/audit-participant-build.ps1` | **NO** |
| `backend/scripts/protect_timeline.py` | **NO** |
| `backend/app/services/timeline_protection.py` | **NO** |
| `backend/tradeverse-backend.spec` | **NO** |
| `desktop/src-tauri/` | **NO** |

**Modified (browser distribution only):**
- `backend/run_backend.py` — localhost bind guard
- `backend/app/paths.py` — packaged event-mode defaults

---

## Remaining blockers

1. **Windows package not built** — PyInstaller must run on Windows with production timeline JSON
2. **macOS package not built** — PyInstaller must run on Mac
3. **Clean-machine double-click test** — not performed in Linux CI
4. **Wi-Fi-off test** — manual checklist in `docs/BROWSER_EVENT_GUIDE.md`
5. **Packaged recovery via launcher restart** — unit tests pass; hardware validation pending
6. **Production timeline** — `tradeverse_timeline.json` (64 events) required on build machine

---

## Build commands

**Windows:**

```powershell
.\scripts\offline\Build-Browser-Participant.ps1 -EventPin "<EVENT_PIN>"
```

**macOS:**

```bash
./scripts/offline/build-browser-participant-macos.sh "<EVENT_PIN>"
```

**Quick build (root):**

```bat
Build-Participant-Zip.bat
```

---

## Final verdict

**SOURCE IMPLEMENTED — PACKAGE NOT VERIFIED**

Browser launcher distribution is ready at source level. Event safety requires building and testing the `TRADEVERSE/` folder on real Windows and macOS participant laptops with Wi-Fi disabled.

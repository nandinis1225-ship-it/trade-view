# TRADEVERSE Build Guide

Browser-local participant and projector packages for offline events.

## Prerequisites

### Windows build machine

- Windows 10/11 x64
- Python 3.11–3.13 with `backend/.venv` (or system Python on PATH)
- Node.js 18+ and npm
- PyInstaller (`pip install pyinstaller`)

### macOS build machine (participant only)

- macOS with Python 3.11+, Node.js, PyInstaller
- Run `scripts/offline/build-browser-participant-macos.sh`

## Repository timeline artifacts

| File | Purpose |
|------|---------|
| `backend/app/seed/tradeverse_timeline.enc` | Committed Fernet-encrypted production timeline (64 events) |
| `backend/app/seed/timeline_manifest.json` | Checksum + event count metadata |
| `backend/app/seed/tradeverse_timeline.pkg` | Build-time protected package (generated or committed) |

The build **never** requires copying `tradeverse_timeline.json` from another project.

### First-time timeline bootstrap

If `tradeverse_timeline.pkg` is not present:

```powershell
$env:TIMELINE_DECRYPT_KEY = "<your-organizer-key>"
cd backend
python scripts/ensure_production_timeline_pkg.py --events 64
```

This decrypts the committed `.enc`, validates exactly 64 events, and writes `.pkg`. Commit `.pkg` to the repo so future builds do not need the decrypt key.

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `EVENT_PIN` | Yes (participant build) | Event PIN baked as hash into participant `.env` |
| `TIMELINE_DECRYPT_KEY` | Only if `.pkg` missing | One-time bootstrap from `.enc` |

Optional override: `-EventPin` on `Build-Browser-Participant.ps1`.

## Windows participant build

```powershell
cd <repo-root>
$env:EVENT_PIN = "<EVENT_PIN>"
# Only if tradeverse_timeline.pkg is missing:
# $env:TIMELINE_DECRYPT_KEY = "<TIMELINE_DECRYPT_KEY>"

.\scripts\offline\Build-Browser-Participant.ps1
```

Output: `participant-build\windows\TRADEVERSE\`

Contents:

- `tradeverse-backend.exe` (timeline embedded inside binary)
- `ui/` (participant static frontend)
- `.env` (hashed PIN, localhost bind)
- `Start-Tradeverse.bat` / `Stop-Tradeverse.bat`

Skip developer rehearsal gate (not recommended):

```powershell
.\scripts\offline\Build-Browser-Participant.ps1 -SkipRehearsal
```

## Windows projector build

```powershell
cd <repo-root>
# TIMELINE_DECRYPT_KEY only if .pkg missing
.\scripts\offline\Build-Projector.ps1
```

Output: `projector-build\TRADEVERSE\`

Open `http://127.0.0.1:8765/projector` after starting the backend.

## macOS participant build

```bash
cd <repo-root>
export EVENT_PIN="<EVENT_PIN>"
export TIMELINE_DECRYPT_KEY="<TIMELINE_DECRYPT_KEY>"   # only if .pkg missing
./scripts/offline/build-browser-participant-macos.sh
```

Output: `participant-build/macos/TRADEVERSE/`

## Audits

After build, packaging audits run automatically. Manual audit:

```powershell
.\scripts\offline\audit-browser-participant-build.ps1 participant-build\windows\TRADEVERSE
```

```bash
./scripts/offline/audit-browser-participant-build.sh participant-build/macos/TRADEVERSE
```

## What must NOT appear in participant packages

- `tradeverse_timeline.json` (plaintext)
- `TIMELINE_DECRYPT_KEY`
- `mse_dev.db` or other dev databases
- Supabase / Railway credentials
- `admin/`, `developer/`, `market-screen/` routes

## Tests before shipping

```bash
cd backend && .venv/bin/python -m pytest -q
bash scripts/dev/run-phase5-gates.sh
cd frontend && npm run lint && npm run build:participant && npm run build:projector && npx tsc --noEmit
```

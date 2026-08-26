# TRADEVERSE

Offline browser-based mock stock exchange for live events (~40 participants).

**Primary distribution:** double-click launcher → local backend → browser terminal at `http://127.0.0.1:8765/terminal`

## Quick start (organizer)

1. Read [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md)
2. Build the Windows participant package:

```powershell
$env:EVENT_PIN = "<EVENT_PIN>"
.\scripts\offline\Build-Browser-Participant.ps1
```

3. Copy `participant-build\windows\TRADEVERSE\` to each laptop
4. Participants double-click `Start-Tradeverse.bat`

Event-day instructions: [docs/BROWSER_EVENT_GUIDE.md](docs/BROWSER_EVENT_GUIDE.md)

## Quick start (developer)

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Architecture

```
Browser → 127.0.0.1:8765 → FastAPI → SQLite → Simulation engine
```

- **Participant mode:** PIN-gated, privacy-filtered API, embedded protected timeline
- **Projector mode:** public display at `/projector` (market %, sectors, news)
- **Recovery:** wall-clock catch-up replay on restart (see [docs/RECOVERY_GUIDE.md](docs/RECOVERY_GUIDE.md))

## Key docs

| Doc | Purpose |
|-----|---------|
| [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) | Build participant/projector packages |
| [docs/BROWSER_EVENT_GUIDE.md](docs/BROWSER_EVENT_GUIDE.md) | Event-day organizer + participant steps |
| [docs/RECOVERY_GUIDE.md](docs/RECOVERY_GUIDE.md) | Recovery behavior and troubleshooting |
| [FINAL_IMPLEMENTATION_STATUS.md](FINAL_IMPLEMENTATION_STATUS.md) | Current validation status |

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
bash scripts/dev/run-phase5-gates.sh
```

## Legacy

Older cloud/LAN/Tauri distribution artifacts are under [`legacy/`](legacy/README.md) (Docker, Supabase, pre-browser launchers). They are **not** used for browser-local events. Historical phase reports are in `docs/archive/`.

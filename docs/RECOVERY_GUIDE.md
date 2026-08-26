# TRADEVERSE Recovery Guide

## What recovery does

When a participant closes the browser or the backend restarts, TRADEVERSE **replays missed simulation time** instead of jumping to the final state.

On startup and on `/api/v1/session/bootstrap`, the recovery service:

1. Calculates elapsed wall-clock time since `event_start_real`
2. Determines authoritative simulation elapsed seconds
3. Replays missed timeline events in chronological order (each exactly once)
4. Replays missed AI ticks (30 simulation-second intervals)
5. Processes IPO and dissolution events in order
6. Restores the current tradable state

Persisted clock fields include:

- `event_start_real`
- `anchor_sim_elapsed_sec`
- `last_processed_elapsed_sec`
- `last_ai_tick_elapsed_sec`

## Participant experience

1. Double-click `Start-Tradeverse.bat` (Windows) or `Start-Tradeverse.command` (macOS)
2. Enter **name** (first time on this laptop) and **event PIN**
3. If returning after a closure, tap **Resume** after PIN entry
4. Portfolio, cash, and holdings are restored from local SQLite

Participants do **not** need to reinstall or copy files again.

## Organizer troubleshooting

### Backend will not start

- Check port `8765` is free
- Run `Stop-Tradeverse.bat` then start again
- Ensure `tradeverse-backend.exe` is present in the TRADEVERSE folder

### PIN rejected

- PIN is announced verbally at event start; it is not stored in plaintext in the package
- Re-announce the correct PIN

### Simulation appears behind schedule

- Recovery catches up automatically on next bootstrap
- Do not reset participant packages mid-event

### Build machine: timeline missing

```powershell
$env:TIMELINE_DECRYPT_KEY = "<organizer-key>"
cd backend
python scripts/ensure_production_timeline_pkg.py --events 64
```

Validates exactly **64** production events before writing `tradeverse_timeline.pkg`.

## Verification tests

```bash
cd backend
.venv/bin/python -m pytest tests/test_recovery.py tests/test_event_e2e_rehearsal.py -q
```

Recovery tests pass without production timeline. E2E rehearsal tests require committed `tradeverse_timeline.pkg`.

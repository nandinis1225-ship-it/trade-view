# TRADEVERSE — Final Event Guide

## Build matrix

| Build | Command | Output |
|-------|---------|--------|
| **Developer** | `scripts/offline/start-developer.ps1` | Full dashboard at `/developer` |
| **Participant** | `scripts/offline/Build-Participant.ps1 -TimelineKey "<key>" -EventPin "<pin>"` | `participant-build/TRADEVERSE.exe` |
| **Projector** | `scripts/offline/Build-Projector.ps1 -TimelineKey "<key>"` | `projector-build/` (backend + `ui/projector`) |

Frontend-only (dev/CI):

```bash
cd frontend && npm run build:participant   # terminal only
cd frontend && npm run build:projector     # projector only
```

## Before event

- [ ] Production timeline verified (`TIMELINE_DECRYPT_KEY` decrypts `tradeverse_timeline.enc`)
- [ ] Event PIN verified and announced verbally at start
- [ ] Participant executable built (`Build-Participant.ps1`)
- [ ] Projector package built (`Build-Projector.ps1`) on display machine
- [ ] Clean-machine test passed (see `docs/CLEAN_MACHINE_TEST.md`)
- [ ] Offline test passed (Wi-Fi off, app launches and trades)
- [ ] Developer accelerated rehearsal passed (`scripts/dev/run-event-rehearsal.ps1`)
- [ ] IPO, dissolution, recovery tested in rehearsal
- [ ] Final P&L screen tested at `03:00:00`
- [ ] Participant build audit passed (`audit-participant-build.ps1`)
- [ ] 50-device distribution package ready

## Event start

1. Everyone opens **TRADEVERSE.exe**
2. Everyone enters **participant name**
3. Organizer announces **event PIN**
4. Everyone enters PIN → **3 · 2 · 1** countdown
5. Simulation starts automatically (no participant START button)

## During event

- No organizer software controls required
- Participants trade via BUY / SELL only
- News appears when released (breaking alert + news panel)
- IPO applications when timeline opens an IPO
- Simulation clock visible as `HH:MM:SS / 03:00:00`

## After event

- Trading stops at `03:00:00`
- Final P&L screen shown and persisted locally
- Organizers manually collect final P&L from participants
- Preserve event package and any exported result files

## Emergency procedures

### Participant closed app accidentally

1. Reopen **TRADEVERSE.exe**
2. Enter **event PIN** on recovery screen
3. Tap **Resume**

### Laptop restarted

Same as above — identity and portfolio are tied to this machine.

### Application crashed

Reopen → PIN → Resume. Recovery processes missed timeline events chronologically.

### Cannot recover

Do **not** create a second portfolio on the same machine. Contact organizer/developer for troubleshooting outside the participant UI.

## Projector

1. Run projector backend package on the display machine (same timeline seed as participants)
2. Open `http://127.0.0.1:8765/projector` full screen
3. Display-only — no participant or admin controls

## What participants never see

Admin, developer tools, timeline checkpoints, future events, AI internals, phases (EUPHORIA/CRASH/RECOVERY), leaderboard, fair value, sector impact configuration.

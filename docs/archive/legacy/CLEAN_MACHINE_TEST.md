# Clean-Machine Participant Validation (Manual)

This procedure must be run on a **Windows PC without Python, Node, npm, pip, Docker, or Git** installed. The Linux CI/dev environment cannot substitute for this test.

## Prerequisites (organizer machine only)

- Windows 10/11 x64
- Timeline decrypt key and event PIN
- Network available **only for the build step** on the build machine

## Build (on build machine)

```powershell
cd <repo-root>
.\scripts\offline\Build-Participant.ps1 -TimelineKey "<TIMELINE_DECRYPT_KEY>" -EventPin "<EVENT_PIN>"
```

Expected output folder: `participant-build\`

Must contain:

- `TRADEVERSE.exe`
- `tradeverse-backend.exe`
- `ui\` (static frontend)
- `.env` (no plaintext `EVENT_PIN`, no `TIMELINE_DECRYPT_KEY`)
- `tradeverse_timeline.baked.json`

Run audit on build machine:

```powershell
.\scripts\offline\audit-participant-build.ps1
```

## Transfer

Copy the entire `participant-build\` folder to a USB drive. Do **not** copy the git repo or `node_modules`.

## Clean-machine test

1. Use a Windows VM or spare laptop with dev tools **uninstalled**.
2. Disable Wi-Fi, Ethernet, and Bluetooth.
3. Copy `participant-build\` to `C:\Tradeverse\`.
4. Double-click `TRADEVERSE.exe`.
5. Enter event PIN → participant name → confirm countdown → trading terminal loads.
6. Verify in Task Manager / Resource Monitor: **no outbound connections** except `127.0.0.1`.
7. Place a small trade; confirm portfolio updates.
8. Close app; reopen; confirm same participant identity and portfolio.
9. Attempt to change display name → must be **blocked**.

## Pass criteria

| Check | Pass |
|-------|------|
| App starts offline | |
| No external HTTP(S) at startup | |
| PIN gate works | |
| Identity lock works | |
| Trading works | |
| Recovery after restart | |
| Audit script passed on package | |

Record results in the event runbook. **Do not mark the project event-ready until this table is completed on a real clean machine.**

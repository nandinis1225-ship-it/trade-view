# Phase 3.5 — Production Packaging Guide

## Browser distribution (recommended)

Participants double-click a launcher; the **bundled backend** starts and the **default browser** opens the trading terminal. No Tauri, Rust, or desktop app required.

| Platform | Build command | Participant starts |
|----------|---------------|-------------------|
| Windows | `.\scripts\offline\Build-Browser-Participant.ps1 -EventPin "<PIN>"` | `Start-Tradeverse.bat` |
| macOS | `./scripts/offline/build-browser-participant-macos.sh "<PIN>"` | `Start-Tradeverse.command` |

Output: `participant-build/{windows,macos}/TRADEVERSE/`

See **[BROWSER_EVENT_GUIDE.md](BROWSER_EVENT_GUIDE.md)** for organizer and participant instructions.

> **Tauri desktop app (deferred):** `Build-Participant.ps1` / `build-participant-macos.sh` still build `TRADEVERSE.exe` / `TRADEVERSE.app` for future native-shell packaging. Tauri source is preserved in `desktop/src-tauri/`.

---

## Overview (Tauri desktop — deferred)

Each participant can alternatively receive **one desktop application** that runs fully offline:

| Platform | Deliverable | Backend sidecar |
|----------|-------------|-----------------|
| Windows | `TRADEVERSE.exe` (+ folder) | `tradeverse-backend.exe` |
| macOS | `TRADEVERSE.app` (+ optional `.dmg`) | `tradeverse-backend` |

The app starts the local FastAPI backend, serves the participant UI from `http://127.0.0.1:8765/terminal`, and stores all data in a per-user SQLite database.

---

## Prerequisites

### Source (all platforms)

- `backend/app/seed/tradeverse_timeline.json` — production timeline (**64 events**, do not modify for packaging)
- Node.js 20+ and npm (build machine only)
- Python 3.11–3.13 with project venv (build machine only)

### Windows build machine

- Windows 10/11 x64
- Rust toolchain + Visual Studio Build Tools (for Tauri)
- PyInstaller (`pip install pyinstaller`)

### macOS build machine

- macOS 12+ (Apple Silicon or Intel matching target laptops)
- Xcode Command Line Tools
- Rust toolchain
- PyInstaller (`pip3 install pyinstaller`)

> **Do not cross-compile.** Build Windows packages on Windows and macOS packages on macOS.

---

## Timeline protection (build time)

The production JSON is **never shipped** to participants. Build transforms it into an embedded `tradeverse_timeline.pkg` (zlib + obfuscation) bundled inside the PyInstaller backend binary.

```bash
cd backend
python scripts/protect_timeline.py --events 64
```

Verification:

- Loads successfully at runtime
- Event count = 64
- Participant folder contains **no** `tradeverse_timeline.json`, `.baked.json`, or `TIMELINE_DECRYPT_KEY`

---

## Windows build

```powershell
cd <repo-root>
.\scripts\offline\Build-Participant.ps1 -EventPin "<EVENT_PIN>"
```

Optional flags:

- `-SkipRehearsal` — skip developer rehearsal gate
- `-SkipTauri` — backend + UI only (no `TRADEVERSE.exe` shell)
- `-SkipPyInstaller` — reuse existing `dist\tradeverse-backend.exe`

### Output

```
participant-build/windows/
  TRADEVERSE.exe
  tradeverse-backend.exe
  ui/
  .env
```

Distribute the **entire folder**. Announce `EVENT_PIN` verbally at event start (hash is baked into `.env`).

### Audit

```powershell
.\scripts\offline\audit-participant-build.ps1 participant-build\windows
```

---

## macOS build

```bash
cd <repo-root>
./scripts/offline/build-participant-macos.sh "<EVENT_PIN>"
```

### Output

```
participant-build/macos/
  TRADEVERSE.app
  TRADEVERSE.dmg          # if Tauri bundle succeeded
  tradeverse-backend
  ui/
  .env
```

Sidecar + UI + `.env` are copied into `TRADEVERSE.app/Contents/MacOS/` for the shell to spawn.

### Audit

```bash
./scripts/offline/audit-participant-build.sh participant-build/macos
```

---

## Runtime layout

```
TRADEVERSE (Tauri)
  → tradeverse-backend (PyInstaller, 127.0.0.1:8765)
  → SQLite at:
      Windows: %LOCALAPPDATA%\Tradeverse\data\trader.db
      macOS:   ~/Library/Application Support/Tradeverse/data/trader.db
  → Static UI from ./ui (served by backend)
```

First launch: schema init, universe seed, timeline seed, session state.  
Subsequent launches: same DB, identity preserved, recovery enabled.

---

## Offline verification checklist

Perform on a **clean machine** (no Python, Node, Docker, Git) with **Wi-Fi disabled**:

1. [ ] Double-click `TRADEVERSE.exe` / `TRADEVERSE.app`
2. [ ] Backend health responds at `http://127.0.0.1:8765/api/v1/health`
3. [ ] Terminal opens — name + PIN + countdown
4. [ ] BUY/SELL works; wallet updates
5. [ ] News appears when released
6. [ ] Simulation clock advances (AI ticks)
7. [ ] Close app → reopen → PIN → Resume → portfolio restored
8. [ ] At `03:00:00` — trading disabled, final P&L shown
9. [ ] No outbound network requests (browser devtools / firewall log)

---

## Clean-machine test

1. Copy `participant-build/windows/` (or macOS equivalent) to a USB drive
2. On a machine with **no dev tools**, copy folder locally
3. Run the application with network disabled
4. Complete the checklist above
5. Run package audit script on the build machine before distribution

---

## Distribution

- Ship **Windows builds to Windows laptops**, **macOS builds to Macs**
- One folder per participant (or signed installer / `.dmg`)
- Do **not** include `tradeverse_timeline.json`, dev databases (`mse_dev.db`), or organizer tooling
- Event PIN is announced verbally — not embedded in plaintext in the package (only hash in `.env`)

---

## Tests (developer machine)

```bash
cd backend
.venv/bin/python -m pytest tests/test_phase35_packaging.py -q
```

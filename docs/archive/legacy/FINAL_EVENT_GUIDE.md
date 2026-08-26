# TRADEVERSE — Final Event Guide

## Platform support

TRADEVERSE participant builds must support **both Windows and macOS**. The participant experience is identical on every platform:

**Open application → Name → PIN → Countdown → Trade → Final P&L**

| Platform | Participant shell | Backend sidecar | Distribution |
|----------|-------------------|-----------------|--------------|
| **Windows** | `TRADEVERSE.exe` (Tauri installer: MSI/NSIS) | `tradeverse-backend.exe` (PyInstaller on Windows) | `.exe` + installer |
| **macOS** | `TRADEVERSE.app` (Tauri `.dmg`) | `tradeverse-backend` (PyInstaller on macOS) | `.app` inside `.dmg` |

**Rules**

- Shared application code (frontend, backend Python, timeline logic) stays **platform-independent**.
- Package the FastAPI backend **separately on each target OS** with PyInstaller in that OS’s build environment.
- A Windows `.exe` **cannot** run on macOS (and vice versa). Build and distribute per platform.
- Do **not** add platform-specific participant features unless absolutely necessary.
- Both builds run **fully offline** after packaging — no cloud, LAN sync, or organizer server.

> **Current repo status:** Windows build scripts exist (`Build-Participant.ps1`). macOS packaging scripts and Tauri bundle targets are **planned** — see [Platform-specific build instructions](#platform-specific-build-instructions) below. Do not ship macOS participants until those steps are implemented and verified on a Mac.

---

## Build matrix

| Build | Command | Output |
|-------|---------|--------|
| **Developer** | `scripts/offline/start-developer.ps1` | Full dashboard at `/developer` |
| **Participant (Windows)** | `scripts/offline/Build-Participant.ps1 -TimelineKey "<key>" -EventPin "<pin>"` | `participant-build/TRADEVERSE.exe` |
| **Participant (macOS)** | *Planned:* `scripts/offline/build-participant.sh` (not yet in repo) | `participant-build/TRADEVERSE.app` + `.dmg` |
| **Projector** | `scripts/offline/Build-Projector.ps1 -TimelineKey "<key>"` | `projector-build/` (backend + `ui/projector`) |

Frontend-only (dev/CI — platform-independent):

```bash
cd frontend && npm run build:participant   # terminal only
cd frontend && npm run build:projector     # projector only
```

---

## Platform-specific build instructions

Build each participant package **on the target OS**. Cross-compiling the PyInstaller sidecar or Tauri bundle from Linux is not supported for event distribution.

### Architecture (all platforms)

```
TRADEVERSE (Tauri shell)
  → tradeverse-backend (PyInstaller sidecar, OS-specific binary name)
  → SQLite (local per machine)
  → http://127.0.0.1:8765/terminal
```

The Tauri app spawns the backend sidecar from the same folder as the app, serves the baked static UI, and opens the participant terminal. No Python or Node is required on participant laptops after packaging.

### Windows

**Build machine requirements:** Windows 10/11 x64, Python 3.11–3.13, Node.js/npm, Rust (for Tauri), timeline decrypt key, event PIN.

```powershell
cd <repo-root>
.\scripts\offline\Build-Participant.ps1 -TimelineKey "<TIMELINE_DECRYPT_KEY>" -EventPin "<EVENT_PIN>"
```

**Pipeline (automated by script):**

1. `npm run build:participant` — static terminal UI
2. `build_event_env.py` — bake timeline + participant `.env`
3. **PyInstaller on Windows** → `tradeverse-backend.exe`
4. **Tauri on Windows** → `TRADEVERSE.exe` (+ MSI/NSIS installer under `desktop/src-tauri/target/release/bundle/`)

**Expected `participant-build/` contents:**

- `TRADEVERSE.exe`
- `tradeverse-backend.exe`
- `ui/` (static frontend)
- `.env` (no plaintext `EVENT_PIN`, no `TIMELINE_DECRYPT_KEY`)
- `tradeverse_timeline.baked.json`

**Audit:**

```powershell
.\scripts\offline\audit-participant-build.ps1
```

**Distribute:** `TRADEVERSE.exe` installer (or portable folder with both binaries in the same directory).

### macOS

**Build machine requirements:** macOS (Apple Silicon or Intel matching target laptops), Python 3.11–3.13, Node.js/npm, Rust + Xcode CLI tools, timeline decrypt key, event PIN.

> macOS build automation is **not implemented yet**. Follow this procedure when `build-participant.sh` is added; until then, run the steps manually on a Mac.

**Planned pipeline:**

1. `npm run build:participant` — same static export as Windows
2. `build_event_env.py` — same bake step as Windows
3. **PyInstaller on macOS** → `tradeverse-backend` (no `.exe` extension)
4. **Tauri on macOS** → `TRADEVERSE.app` + `.dmg` (configure `tauri.conf.json` bundle targets for `dmg`)

**Expected `participant-build/` contents:**

- `TRADEVERSE.app`
- `tradeverse-backend` (executable, alongside or inside the app bundle per Tauri sidecar layout)
- `ui/`, `.env`, `tradeverse_timeline.baked.json` (same semantics as Windows)

**Distribute:** `.dmg` (or notarized `.app` zip) built on macOS for the same CPU architecture as participant Macs (arm64 vs x64).

### What not to do

- Do not copy `tradeverse-backend.exe` from Windows onto Macs.
- Do not assume one zip serves both platforms — ship **Windows packages to Windows laptops** and **macOS packages to Macs**.
- Do not require participants to install Python, Node, or pip.

---

## Before event

- [ ] Production timeline verified (`TIMELINE_DECRYPT_KEY` decrypts `tradeverse_timeline.enc`)
- [ ] Event PIN verified and announced verbally at start
- [ ] **Windows** participant package built (`Build-Participant.ps1`) if any Windows laptops attend
- [ ] **macOS** participant package built on a Mac (when script exists) if any Mac laptops attend
- [ ] Projector package built (`Build-Projector.ps1`) on display machine
- [ ] Clean-machine test passed on **each platform** you distribute (see `docs/CLEAN_MACHINE_TEST.md`)
- [ ] Offline test passed (Wi-Fi off, app launches and trades) on Windows **and** macOS samples
- [ ] Developer accelerated rehearsal passed (`scripts/dev/run-event-rehearsal.ps1`)
- [ ] IPO, dissolution, recovery tested in rehearsal
- [ ] Final P&L screen tested at `03:00:00`
- [ ] Participant build audit passed (`audit-participant-build.ps1` on Windows; macOS equivalent when added)
- [ ] 50-device distribution packages ready (**split by OS**)

---

## Event start

1. Everyone opens **TRADEVERSE** (`TRADEVERSE.exe` on Windows, `TRADEVERSE.app` on macOS)
2. Everyone enters **participant name**
3. Organizer announces **event PIN**
4. Everyone enters PIN → **3 · 2 · 1** countdown
5. Simulation starts automatically (no participant START button)

---

## During event

- No organizer software controls required
- Participants trade via BUY / SELL only
- News appears when released (breaking alert + news panel)
- IPO applications when timeline opens an IPO
- Simulation clock visible as `HH:MM:SS / 03:00:00`

---

## After event

- Trading stops at `03:00:00`
- Final P&L screen shown and persisted locally
- Organizers manually collect final P&L from participants
- Preserve event package and any exported result files

---

## Emergency procedures

### Participant closed app accidentally

1. Reopen **TRADEVERSE**
2. Enter **event PIN** on recovery screen
3. Tap **Resume**

### Laptop restarted

Same as above — identity and portfolio are tied to this machine.

### Application crashed

Reopen → PIN → Resume. Recovery processes missed timeline events chronologically.

### Cannot recover

Do **not** create a second portfolio on the same machine. Contact organizer/developer for troubleshooting outside the participant UI.

---

## Projector

1. Run projector backend package on the display machine (same timeline seed as participants)
2. Open `http://127.0.0.1:8765/projector` full screen
3. Display-only — no participant or admin controls

---

## What participants never see

Admin, developer tools, timeline checkpoints, future events, AI internals, phases (EUPHORIA/CRASH/RECOVERY), leaderboard, fair value, sector impact configuration.

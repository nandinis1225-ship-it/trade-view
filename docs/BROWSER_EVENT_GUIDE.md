# TRADEVERSE — Browser Event Guide

Simple instructions for running TRADEVERSE on participant laptops using a **browser launcher** (no Tauri, no Python, no Node on participant machines).

---

## What participants need

- Windows 10/11 **or** macOS
- Chrome, Edge, Safari, or another modern browser
- The `TRADEVERSE` folder copied to their laptop

## What participants do NOT need

- Python, Node.js, npm, Rust, Git, Docker
- Internet or Wi-Fi (after the package is copied)
- Any organizer server or cloud account

---

## What the organizer does

### 1. Build the package (on your build machine)

**Windows:**

```powershell
cd <repo-root>
$env:EVENT_PIN = "<EVENT_PIN>"
$env:TIMELINE_DECRYPT_KEY = "<TIMELINE_DECRYPT_KEY>"   # organizer .env — build-time only
.\scripts\offline\Build-Browser-Participant.ps1
```

Or pass the PIN explicitly (overrides `EVENT_PIN`):

```powershell
.\scripts\offline\Build-Browser-Participant.ps1 -EventPin "<EVENT_PIN>"
```

The build uses the committed `backend/app/seed/tradeverse_timeline.enc` (64 events). It creates a protected `tradeverse_timeline.pkg` at build time and embeds it in the backend binary. You do **not** need `tradeverse_timeline.json` from another project.

Output: `participant-build\windows\TRADEVERSE\`

**macOS (on a Mac):**

```bash
cd <repo-root>
export EVENT_PIN="<EVENT_PIN>"
export TIMELINE_DECRYPT_KEY="<TIMELINE_DECRYPT_KEY>"   # organizer .env — build-time only
./scripts/offline/build-browser-participant-macos.sh
```

Output: `participant-build/macos/TRADEVERSE/`

### 2. Copy the package to each laptop

Copy the entire `TRADEVERSE` folder to each participant computer (USB drive, shared folder, etc.).

### 3. Tell participants how to start

- **Windows:** double-click `Start-Tradeverse.bat`
- **macOS:** double-click `Start-Tradeverse.command` (right-click → Open if Gatekeeper warns the first time)

### 4. Announce the event PIN verbally

Do not email the PIN in the package. Say it at the start of the event.

### 5. After the event

Ask participants to run `Stop-Tradeverse.bat` (Windows) or `Stop-Tradeverse.command` (macOS) when finished.

Collect final P&L from each participant (shown on screen at 03:00:00).

---

## What the participant does

1. **Double-click** `Start-Tradeverse.bat` (Windows) or `Start-Tradeverse.command` (macOS)
2. **Wait** a few seconds — your browser opens automatically
3. **Enter your name** (first time only on this laptop)
4. **Enter the event PIN** (announced by the organizer)
5. **Watch the countdown** — 3 · 2 · 1
6. **Trade** until the simulation ends
7. **View final P&L** when time reaches 03:00:00

### If you closed the browser by accident

1. Double-click the launcher again
2. Enter your **PIN**
3. Tap **Resume** — your portfolio is still there

### When you are finished for the day

Run `Stop-Tradeverse.bat` or `Stop-Tradeverse.command` to stop the local backend.

---

## How the launcher works

```
Double-click Start-Tradeverse
        ↓
tradeverse-backend starts on 127.0.0.1:8765
        ↓
Health check: /api/v1/health
        ↓
Browser opens: http://127.0.0.1:8765/terminal
        ↓
Name → PIN → Countdown → Trade → Final P&L
```

- Closing the browser **does not** delete your portfolio
- The backend keeps running so you can reopen and resume
- All data stays in a local SQLite database on your laptop
- No data is sent to the internet

---

## Windows instructions

| File | Purpose |
|------|---------|
| `Start-Tradeverse.bat` | Start backend + open browser |
| `Stop-Tradeverse.bat` | Stop backend after event |
| `tradeverse-backend.exe` | Local simulation server (do not delete) |
| `ui/` | Trading interface (do not delete) |
| `.env` | Event configuration (do not edit) |

**Troubleshooting**

- “Backend did not start” — make sure port 8765 is free; restart the laptop and try again
- Browser did not open — manually go to `http://127.0.0.1:8765/terminal`
- Invalid PIN — check with organizer

---

## macOS instructions

| File | Purpose |
|------|---------|
| `Start-Tradeverse.command` | Start backend + open browser |
| `Stop-Tradeverse.command` | Stop backend after event |
| `tradeverse-backend` | Local simulation server (do not delete) |
| `ui/` | Trading interface (do not delete) |
| `.env` | Event configuration (do not edit) |

**First launch:** If macOS blocks the file, right-click → **Open** → **Open** again.

**Troubleshooting**

- Same as Windows — use `http://127.0.0.1:8765/terminal` if browser does not open automatically

---

## Offline test (organizer checklist)

Before the event, on a clean laptop with **Wi-Fi off**:

1. Copy `TRADEVERSE` folder
2. Double-click launcher
3. Browser opens
4. Enter name + PIN
5. Countdown runs
6. Buy and sell a stock
7. News appears
8. Close browser, reopen launcher, resume with PIN
9. Final P&L at end of simulation (or accelerated test)

---

## Tauri desktop app (deferred)

A native `TRADEVERSE.exe` / `TRADEVERSE.app` desktop shell is still available for future use via `Build-Participant.ps1`. The **browser launcher** is the recommended distribution for the event.

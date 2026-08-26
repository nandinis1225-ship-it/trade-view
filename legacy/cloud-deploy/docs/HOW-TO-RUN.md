# How to run TRADEVERSE (offline edition)

**Want one URL for everyone (Vercel) instead of per-laptop offline?** See **[DEPLOY-VERCEL.md](DEPLOY-VERCEL.md)** — frontend on Vercel, API on Railway, leaderboard on Supabase.

## Leaderboard: Supabase (recommended) vs LAN IP

| | **Supabase** | **LAN IP + Organizer.bat** |
|--|--|--|
| Setup | Free cloud project, one SQL script | Organizer runs collector, everyone needs your IP |
| Wi‑Fi | Any internet | Same room Wi‑Fi usually required |
| Organizer | Open market-screen only | Run Organizer.bat + market-screen |

**Trading always runs locally on each laptop.** Only the **score snapshot** goes to the cloud (Supabase) or organizer PC — not the full game.

---

## Supabase setup (5 minutes, do this once)

1. Go to [supabase.com](https://supabase.com) → New project (free tier is fine).
2. **SQL Editor** → paste and run [`supabase/leaderboard_schema.sql`](supabase/leaderboard_schema.sql).
3. **Project Settings → API** → copy:
   - Project URL → `SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` `public` key → `SUPABASE_ANON_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Put those four values in `.env` (use `.env.offline-participant.example` as template).
5. **Share the same `.env` values** with every participant (same anon key is OK for a club event).

You do **not** need `Start-TRADEVERSE-Organizer.bat` if you use Supabase.

**Projector:** run participant stack on your laptop + open http://127.0.0.1:3000/market-screen (leaderboard pulls from Supabase).

---

## What runs where

| Machine | What it does | How to start |
|---------|----------------|--------------|
| **Organizer laptop** (projector) | Leaderboard only — collects scores | Double-click `Start-TRADEVERSE-Organizer.bat` |
| **Each participant laptop** | Full game locally — no shared server | Double-click `Start-TRADEVERSE-Participant.bat` |

Trading does **not** use the internet. Only small leaderboard updates go to the organizer (same Wi‑Fi).

---

## Before the event (organizer)

1. Install **Python 3.11+** and **Node.js 20+** on your laptop (one time).
2. Double-click **`Start-TRADEVERSE-Organizer.bat`**.
3. Find your LAN IP: `ipconfig` → look for IPv4 (e.g. `192.168.1.10`).
4. Tell participants to use:
   `LEADERBOARD_SYNC_URL=http://192.168.1.10:9000/api/v1/snapshot`
   (replace with your IP).

Optional projector UI: run participant stack on organizer too for `/market-screen`, with `NEXT_PUBLIC_LEADERBOARD_URL=http://127.0.0.1:9000`.

---

## Before the event (each participant)

### Option A — you send them a zip

From your dev machine:

```powershell
.\scripts\offline\build-share-package.ps1
```

Send **`Tradeverse-Participant.zip`** (USB, Teams, Google Drive, etc.).

On each laptop:

1. Install **Python 3.11+** and **Node.js 20+** (one time).
2. Unzip the folder anywhere (e.g. `C:\Tradeverse`).
3. Edit `.env` — set `LEADERBOARD_SYNC_URL` to the organizer URL from step above.
4. Double-click **`Start-TRADEVERSE-Participant.bat`**.
5. First run installs dependencies (5–10 minutes). Later runs are faster.
6. Browser opens → **http://127.0.0.1:3000/terminal**
7. Enter name → **Waiting to start** → when organizer says go, press **Start now** or **30s countdown**.

### Option B — everyone clones/copies the same folder

Same steps as Option A without the zip script.

---

## Day of event flow

1. Organizer starts **Organizer.bat** first.
2. Everyone starts **Participant.bat** and opens the terminal.
3. Organizer: “Starting in 30 seconds…” — everyone hits countdown or Start now.
4. Trade for 3 hours. Leaderboard updates on organizer every ~45 seconds.
5. If Wi‑Fi fails, trading still works; collect `export-snapshot` JSON at the end if needed.

---

## About a single `.exe`

There is **no pre-built exe in this repo yet**. A true one-file exe would bundle Python + Node + the app (~200MB+) and must be **built on a Windows PC** (PyInstaller / Tauri). What you have now:

- **Double-click `.bat` files** — same idea for non-technical users, but requires Python + Node installed once.
- **`desktop/launcher.mjs`** — `cd desktop && npm install && npm run participant`

If you want a real exe next step: build Tauri on a machine with Rust (`cd desktop && npm run tauri:build`) or we can add a PyInstaller backend + static UI bundle.

---

## Your `.env` right now

If your `.env` still has `ngrok` / `POSTGRES` / no `LOCAL_INSTANCE_MODE`, it is the **old shared-server mode**. For offline per-laptop play, replace it:

```powershell
Copy-Item .env.offline-participant.example .env -Force
```

Then edit `LEADERBOARD_SYNC_URL` only.

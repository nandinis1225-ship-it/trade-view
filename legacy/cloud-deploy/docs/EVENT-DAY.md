# Event day (Option 1 — offline + Supabase)

## You (organizer)

1. **Encrypt timeline** (once per event, or when timeline changes):
   ```powershell
   .\scripts\offline\encrypt-timeline.ps1
   ```
   Save `TIMELINE_DECRYPT_KEY` in your `.env`. Do **not** put it in the participant zip.

2. **Build participant zip** (either way):
   ```powershell
   .\scripts\offline\build-share-package.ps1
   ```
   Or double-click **`Build-Participant-Zip.bat`**, or use **Build participant zip** in organizer controls on `/market-screen`.
   Send `Tradeverse-Participant.zip` only.

3. **Double-click `Start-TRADEVERSE.bat`** on your laptop.

4. Browser → enter name → **Start** when everyone is ready.

5. **Announce at event start:** `TIMELINE_DECRYPT_KEY` so participants can paste into `.env` and restart if needed.

6. **Projector:** open **http://127.0.0.1:3000/market-screen** on the organizer laptop. Unlock organizer controls with passkey `finclub123` (or one-time URL `?organizer=finclub123`). Use **Reset everyone's progress & charts** to zero all portfolios, price charts, and the timer on every device.

7. **Supabase (once):** run `scripts/supabase/event_control.sql` in the SQL editor so global reset signals work.

## Participants

1. Install **Python 3** + **Node.js** once (if not already).
2. Unzip `Tradeverse-Participant.zip`.
3. Copy `.env.offline-participant.example` → `.env`; add **Supabase** keys (organizer shares before event).
4. At **event start**, add `TIMELINE_DECRYPT_KEY` to `.env` (organizer announces verbally / on slide).
5. **Double-click `Start-TRADEVERSE.bat`**.

No Railway. No LAN IP. Scores sync to Supabase automatically.

See [PARTICIPANT-README.md](PARTICIPANT-README.md) for the full participant manifest.

## What to send participants

**In the zip:** app code, `Start-TRADEVERSE.bat`, encrypted `tradeverse_timeline.enc`, stock universe JSON, offline start scripts.

**Share separately:**

| Item | When |
|------|------|
| Supabase URL + anon key | Before event |
| `TIMELINE_DECRYPT_KEY` | At event start |

**Never send:** `tradeverse_timeline.json`, news brief `.docx`, organizer `.env`, `Start-TRADEVERSE-Organizer.bat`.

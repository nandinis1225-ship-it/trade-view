# TRADEVERSE — Participant setup

## Before the event

1. Install **Python 3.11–3.13** and **Node.js 18+** once on your laptop.
2. **Do not run from WhatsApp’s transfer folder.** Extract the zip to `C:\Tradeverse` (or `Documents\Tradeverse`).
3. Unzip `Tradeverse-Participant.zip` to that folder.
3. Copy `.env.offline-participant.example` to `.env` in the same folder.
4. Paste the **Supabase** URL and anon key from your organizer into `.env`.
5. At **event start**, the organizer will announce `TIMELINE_DECRYPT_KEY`. Add it to `.env`:
   ```
   TIMELINE_DECRYPT_KEY=your-key-here
   ```
6. Double-click **`Start-TRADEVERSE.bat`**. If you added the timeline key after first launch, restart once.

## During the event

1. Browser opens → enter your name → **Continue**.
2. When told to start, press **Start now** or **30s countdown**.
3. Trade stocks; open **Wallet** for holdings and **News briefs** for released headlines.
4. Scores sync to the live leaderboard automatically.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Event key required" | Add `TIMELINE_DECRYPT_KEY` to `.env` and restart |
| Failed to fetch | Wait for backend to finish starting; check Python/Node installed |
| Leaderboard empty | Confirm Supabase keys in `.env` and internet connection |

## What is not in this package

The organizer does **not** ship future news spoilers (no plaintext timeline JSON, no phase schedule, no IPO/dissolution timing in the universe file). News appears only as it is released in the simulation.

The encrypted timeline seed (`tradeverse_timeline.enc`) is required for the local engine to run; it is not exposed through the participant UI or public APIs.

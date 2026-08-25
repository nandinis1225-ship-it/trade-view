# TRADEVERSE — Participant setup

## Organizer: before building the participant package

Run the full event in **developer mode** first:

1. Double-click **`developer-launch.bat`** (or `npm run dev` with backend `DEVELOPER_MODE=true`).
2. Open **http://127.0.0.1:3000/developer** — not the participant terminal.
3. Use accelerated speed (e.g. 60x) and the scenario checklist to verify news, AI, IPO, dissolution, and recovery.
4. Build the zip only after rehearsal passes: `.\scripts\offline\build-share-package.ps1 -TimelineKey ... -EventPin ...`

Use `-SkipRehearsal` only for CI or when repeating a known-good build.

## Before the event

1. Extract `Tradeverse-Participant.zip` to `C:\Tradeverse` (not WhatsApp transfer folder).
2. Double-click **`Start-TRADEVERSE.bat`**. No configuration required — keys are baked in.

## During the event

1. Terminal opens automatically.
2. Enter your **name** and the **event PIN** (organizer announces verbally).
3. Watch the **3-2-1** countdown — the simulation starts automatically.
4. Trade stocks; open **Wallet** for holdings and **News briefs** for released headlines.

## At the end

When simulation time reaches 03:00:00, an **EVENT COMPLETE** screen shows your final P&L. Use **Export result** to save a local JSON file for the organizer.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Invalid PIN | Check the PIN announced by the organizer |
| Failed to fetch | Wait for backend to finish starting; restart TRADEVERSE |
| Market closed | Simulation ended — review final P&L screen |

## What is not in this package

- No leaderboard or network sync
- No admin controls for participants
- No plaintext future timeline or phase schedule spoilers

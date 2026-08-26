# TRADEVERSE Local / Offline Edition

Per-participant simulation on each laptop (SQLite). Central leaderboard DB on the organizer machine only.

## Quick start (participant)

```powershell
Copy-Item .env.offline-participant.example .env
# Set LEADERBOARD_SYNC_URL=http://<organizer-ip>:9000/api/v1/snapshot if using live sync
.\scripts\offline\start-participant.ps1
```

Open http://127.0.0.1:3000/terminal — enter name, wait for start countdown, trade.

## Organizer (leaderboard collector)

```powershell
.\scripts\offline\start-organizer.ps1
```

Collector API: `http://0.0.0.0:9000/api/v1/leaderboard`  
Participants POST snapshots to `http://<organizer-ip>:9000/api/v1/snapshot`

Run market-screen against a local sim backend for phase/news UI; set `NEXT_PUBLIC_LEADERBOARD_URL=http://<organizer-ip>:9000` on that frontend.

## Desktop launcher

```powershell
cd desktop
npm install
npm run participant   # backend + frontend dev
npm run organizer     # collector only
```

With Rust installed: `npm run tauri:build` for a native window.

## Data files (verbatim)

- `backend/app/seed/tradeverse_universe.json`
- `backend/app/seed/tradeverse_timeline.json`

## Key env vars

| Variable | Purpose |
|----------|---------|
| `LOCAL_INSTANCE_MODE=true` | SQLite, single user, personal IPO lottery, no AI ticks |
| `LEADERBOARD_SYNC_URL` | POST target for live leaderboard sync |
| `NEXT_PUBLIC_LOCAL_INSTANCE=true` | Frontend waiting-to-start UI |
| `NEXT_PUBLIC_LEADERBOARD_URL` | Projector reads collector leaderboard |

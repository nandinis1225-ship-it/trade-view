# Legacy (not event critical path)

This directory holds **frozen** artifacts from earlier TRADEVERSE distribution models. The current event path is **browser-local**: `scripts/offline/Build-Browser-Participant.ps1` → `Start-Tradeverse.bat` → `http://127.0.0.1:8765/terminal`.

Do not use these for live events unless you are explicitly maintaining an older deployment.

| Path | What it was |
|------|-------------|
| `cloud-deploy/` | Docker Compose, Nginx, Supabase, OCI deploy scripts, LAN/ngrok docs |
| `launchers/` | Pre-browser `Start-TRADEVERSE*.bat` and zip helpers |
| `offline-scripts/` | Python-on-PATH participant/organizer starters, share-package builder |
| `leaderboard-collector/` | Supabase leaderboard sidecar for cloud/LAN mode |

**Still in active tree (frozen, not moved):**

- `desktop/` — Tauri shell source (`Build-Participant.ps1` in `scripts/offline/`)
- `scripts/offline/Build-Participant.ps1` — legacy native desktop build

See [docs/BUILD_GUIDE.md](../docs/BUILD_GUIDE.md) for the supported browser packaging workflow.

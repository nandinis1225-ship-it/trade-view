# Deploy TRADEVERSE: Vercel + Railway + Supabase

Everyone opens **one URL** (your Vercel app). The game runs on a **cloud API** (Railway). **Supabase** stores the live leaderboard for the projector.

```
Participants / organizer browser  →  Vercel (Next.js UI)
Trading + simulation + WebSockets →  Railway (FastAPI)
Leaderboard scores                →  Supabase (cloud table)
```

This is **not** the per-laptop offline model — it is one shared market (like the original TRADEVERSE server). Supabase only replaces “find my LAN IP for leaderboard.”

---

## 1. Supabase (5 min)

1. [supabase.com](https://supabase.com) → new project  
2. SQL Editor → run [`supabase/leaderboard_schema.sql`](supabase/leaderboard_schema.sql)  
3. Copy **Project URL** and **anon public key**

---

## 2. Railway — backend API

1. [railway.app](https://railway.app) → New Project → **Deploy from GitHub** (this repo)  
2. Set **Root directory** to `backend` (or deploy service from `backend/`)  
3. Add **PostgreSQL** plugin → Railway sets `DATABASE_URL`  
4. Variables (from `.env.cloud.example`):

   | Variable | Value |
   |----------|--------|
   | `ENVIRONMENT` | `production` |
   | `JWT_SECRET` | long random string |
   | `ADMIN_SECRET` | your event admin password |
   | `SUPABASE_URL` | from Supabase |
   | `SUPABASE_ANON_KEY` | from Supabase |
   | `CORS_ORIGINS` | `https://YOUR-APP.vercel.app` (add after step 3) |
   | `FRONTEND_URL` | same Vercel URL |
   | `BACKEND_URL` | your Railway public URL |

5. Deploy → copy public URL, e.g. `https://tradeverse-api.up.railway.app`  
6. Health check: `https://YOUR-RAILWAY-URL/api/v1/health`

**Start the event (organizer):** open `https://YOUR-APP.vercel.app/admin` → login with `ADMIN_SECRET` → bootstrap universe → **Start simulation**.

---

## 3. Vercel — frontend

1. [vercel.com](https://vercel.com) → Add New Project → import this repo  
2. **Root Directory:** `frontend`  
3. Environment variables:

   | Variable | Value |
   |----------|--------|
   | `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-URL` |
   | `NEXT_PUBLIC_WS_URL` | `wss://YOUR-RAILWAY-URL` |
   | `NEXT_PUBLIC_API_PREFIX` | `/api/v1` |
   | `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

   Do **not** set `NEXT_PUBLIC_LOCAL_INSTANCE` (that is only for offline laptops).

4. Deploy → you get `https://your-app.vercel.app`

5. Update Railway `CORS_ORIGINS` and `FRONTEND_URL` to that Vercel URL if you did not already.

---

## 4. Event day URLs

| Who | URL |
|-----|-----|
| Traders | `https://your-app.vercel.app/terminal` |
| Projector / market screen | `https://your-app.vercel.app/market-screen` |
| Organizer controls | `https://your-app.vercel.app/admin` |

Leaderboard on market-screen reads from **Supabase** automatically.

---

## CLI deploy (optional)

```bash
# Backend — from repo root, link Railway to backend service
cd backend
railway login
railway link
railway up

# Frontend
cd frontend
npx vercel login
npx vercel --prod
```

---

## Limits

- **Vercel** hosts the UI only (no Python simulation).  
- **~50 concurrent players** still load the Railway API + WebSockets; use a Railway plan that can handle it, or keep the offline-per-laptop model for huge rooms.  
- **Supabase** handles leaderboard only; trades still go through Railway.

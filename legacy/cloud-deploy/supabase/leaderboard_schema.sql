-- TRADEVERSE leaderboard (cloud sync — no LAN IP needed)
-- Run in Supabase SQL editor: https://supabase.com/dashboard → SQL → New query

create table if not exists public.participant_snapshots (
  session_id text primary key,
  display_name text not null,
  cash numeric default 0,
  holdings_json jsonb default '[]'::jsonb,
  realized_pnl numeric default 0,
  unrealized_pnl numeric default 0,
  portfolio_value numeric default 0,
  return_pct numeric default 0,
  trade_count integer default 0,
  updated_at timestamptz default now()
);

alter table public.participant_snapshots enable row level security;

-- Club-event policy: anyone with the anon key can read/write scores.
-- For a locked-down event, replace with auth or use service_role only on organizer.
drop policy if exists "tradeverse_snapshots_read" on public.participant_snapshots;
create policy "tradeverse_snapshots_read"
  on public.participant_snapshots for select
  to anon, authenticated
  using (true);

drop policy if exists "tradeverse_snapshots_insert" on public.participant_snapshots;
create policy "tradeverse_snapshots_insert"
  on public.participant_snapshots for insert
  to anon, authenticated
  with check (true);

drop policy if exists "tradeverse_snapshots_update" on public.participant_snapshots;
create policy "tradeverse_snapshots_update"
  on public.participant_snapshots for update
  to anon, authenticated
  using (true);

create index if not exists participant_snapshots_return_idx
  on public.participant_snapshots (return_pct desc);

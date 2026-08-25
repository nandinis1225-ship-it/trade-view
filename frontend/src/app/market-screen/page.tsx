"use client";

import { useCallback, useEffect, useState } from "react";
import { CurrentEventPanel } from "@/components/market-screen/CurrentEventPanel";
import { OrganizerDebugPanel } from "@/components/market-screen/OrganizerDebugPanel";
import { MarketScreenHeader } from "@/components/market-screen/MarketScreenHeader";
import { SectorImpactMatrix } from "@/components/market-screen/SectorImpactMatrix";
import { SectorSummaryGrid } from "@/components/market-screen/SectorSummaryGrid";
import { Leaderboard, type LeaderboardRow } from "@/components/Leaderboard";
import type { SectorGroup } from "@/components/StockSidebar";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import {
  apiGet,
  fetchLeaderboardWithDiagnostics,
  getApiBaseUrl,
  getSupabaseLeaderboardConfig,
  hasRemoteLeaderboard,
  organizerMarketDashboard,
  probeMarketApi,
  type LeaderboardDiagnostics,
} from "@/lib/api";
import { getRuntimeConfig } from "@/lib/runtimeConfig";
import { getStoredOrganizerPasskey, isOrganizerUnlocked, tryUnlockFromUrl } from "@/lib/organizerAuth";
import type { NewsImpactRow } from "@/lib/sectorImpactUtils";

type MarketStatus = {
  elapsed: string;
  current_phase?: string;
  status: string;
  market_change_pct: string;
  latest_news: {
    id: number;
    title: string;
    description: string;
    released_at: string | null;
    sector_impacts?: Record<string, number>;
  } | null;
};

type NewsItem = NewsImpactRow & {
  description?: string;
  released_at?: string;
};

type ApiProbe = { ok: boolean; url: string; error?: string };

export default function MarketScreenPage() {
  const [status, setStatus] = useState<MarketStatus | null>(null);
  const [sectors, setSectors] = useState<SectorGroup[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardRow[]>([]);
  const [lastRefresh, setLastRefresh] = useState<string>("—");
  const [marketProbe, setMarketProbe] = useState<ApiProbe | null>(null);
  const [lbDiag, setLbDiag] = useState<LeaderboardDiagnostics | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [organizerMode, setOrganizerMode] = useState(false);

  const showRemoteLeaderboard = hasRemoteLeaderboard();

  useEffect(() => {
    tryUnlockFromUrl();
    setOrganizerMode(isOrganizerUnlocked());
  }, []);

  const refresh = useCallback(async () => {
    setRefreshError(null);
    const probe = await probeMarketApi("/market/status");
    setMarketProbe(probe);

    if (!probe.ok) {
      setRefreshError(probe.error ?? "Market API unreachable");
      if (showRemoteLeaderboard) {
        const lb = await fetchLeaderboardWithDiagnostics();
        setLbDiag(lb);
        setLeaderboard(lb.rows);
      }
      setLastRefresh(new Date().toLocaleTimeString());
      return;
    }

    const unlocked = isOrganizerUnlocked();
    const passkey = getStoredOrganizerPasskey();

    try {
      if (unlocked && passkey) {
        const dashboard = await organizerMarketDashboard(passkey);
        setStatus({
          elapsed: dashboard.elapsed,
          current_phase: dashboard.current_phase,
          status: dashboard.status,
          market_change_pct: dashboard.market_change_pct,
          latest_news: dashboard.latest_news,
        });
        setNews(dashboard.news);
      } else {
        const [st, nw] = await Promise.all([
          apiGet<MarketStatus>("/market/status"),
          apiGet<NewsItem[]>("/news"),
        ]);
        setStatus(st);
        setNews(nw);
      }
      const sec = await apiGet<SectorGroup[]>("/market/sectors");
      setSectors(sec);
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : "Market data fetch failed");
    }

    if (showRemoteLeaderboard) {
      const lb = await fetchLeaderboardWithDiagnostics();
      setLbDiag(lb);
      setLeaderboard(lb.rows);
      if (!lb.ok && lb.error) {
        setRefreshError((prev) => prev ?? `Supabase: ${lb.error}`);
      }
    }

    setLastRefresh(new Date().toLocaleTimeString());
  }, [showRemoteLeaderboard]);

  useEffect(() => {
    refresh();
    const id = window.setInterval(refresh, 5000);
    return () => window.clearInterval(id);
  }, [refresh]);

  useMarketWebSocket({
    onMessage: (msg) => {
      if (
        msg.event === "NEWS_RELEASED" ||
        msg.event === "PRICE_UPDATED" ||
        msg.event === "TRADE_EXECUTED" ||
        msg.event === "SIMULATION_STATUS" ||
        msg.event === "SIMULATION_CLOCK"
      ) {
        refresh();
      }
    },
  });

  const latest = status?.latest_news;

  const organizerDebugLines = organizerMode
    ? (() => {
        const supa = getSupabaseLeaderboardConfig();
        const rt = getRuntimeConfig();
        const onLocalHost =
          window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost";
        return [
          { label: "Page host", value: window.location.host },
          {
            label: "API base",
            value: getApiBaseUrl(),
            ok: marketProbe?.ok,
          },
          {
            label: "Market /status",
            value: marketProbe
              ? marketProbe.ok
                ? `OK ${marketProbe.url}`
                : `${marketProbe.error ?? "failed"}`
              : "—",
            ok: marketProbe?.ok,
          },
          {
            label: "Simulation",
            value: status ? `${status.status} · ${status.elapsed} · ${status.current_phase}` : "no data",
          },
          {
            label: "Supabase configured",
            value: supa ? `yes (${supa.table})` : "no",
            ok: Boolean(supa),
          },
          {
            label: "Supabase fetch",
            value: lbDiag
              ? lbDiag.ok
                ? `OK · ${lbDiag.rowCount} rows · ${lbDiag.endpoint}`
                : `${lbDiag.status ?? ""} ${lbDiag.error ?? "failed"}`
              : showRemoteLeaderboard
                ? "not fetched yet"
                : "disabled",
            ok: lbDiag?.ok,
          },
          { label: "Last refresh", value: lastRefresh },
          { label: "Runtime config", value: rt ? "loaded from tradeverse-runtime.json" : "env vars only" },
          {
            label: "Tip",
            value: onLocalHost
              ? "Organizer market-screen: phases + Supabase leaderboard + reset controls"
              : "Vercel URL: leaderboard only — open http://127.0.0.1:3000/market-screen for live phases",
          },
        ];
      })()
    : [];

  return (
    <div className="min-h-screen bg-black p-4 font-mono text-white md:p-8">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
        <MarketScreenHeader
          elapsed={status?.elapsed ?? "00:00:00"}
          phase={status?.current_phase ?? "—"}
          marketChangePct={status?.market_change_pct ?? "0"}
        />

        {refreshError && (
          <div className="border border-red-500/50 bg-red-950/40 p-3 text-sm text-red-200">
            {refreshError}
          </div>
        )}

        {latest && organizerMode && latest.sector_impacts && (
          <CurrentEventPanel
            title={latest.title}
            description={latest.description}
            sectorImpacts={latest.sector_impacts}
          />
        )}

        {latest && !organizerMode && (
          <CurrentEventPanel
            title={latest.title}
            description={latest.description}
            sectorImpacts={{}}
          />
        )}

        {showRemoteLeaderboard && (
          <div className="border border-white/15 p-4">
            <p className="mb-3 text-xs uppercase tracking-wider text-white/50">
              Live leaderboard (Supabase) · {leaderboard.length} players
            </p>
            {leaderboard.length > 0 ? (
              <Leaderboard rows={leaderboard} variant="admin" maxRows={20} />
            ) : (
              <p className="text-sm text-white/40">
                No scores yet — traders must join on /terminal and trade (scores sync every ~45s).
              </p>
            )}
          </div>
        )}

        <SectorSummaryGrid sectors={sectors} />

        {organizerMode && <SectorImpactMatrix news={news} />}

        <OrganizerDebugPanel
          lines={organizerDebugLines}
          simulationStatus={status?.status}
          simulationElapsed={status?.elapsed}
          onResetComplete={() => void refresh()}
        />
      </div>
    </div>
  );
}

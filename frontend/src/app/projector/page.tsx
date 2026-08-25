"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import type { SectorGroup } from "@/components/StockSidebar";
import { fmtPct, signClass } from "@/lib/marketFormat";
import { apiGet } from "@/lib/participant-api";

type NewsRow = {
  id: number;
  title: string;
  description?: string;
  released_at?: string;
};

type MarketStatus = {
  elapsed: string;
  duration?: string;
  status: string;
  market_change_pct: string;
};

type TickerRow = {
  ticker: string;
  last_traded_price: string;
  percent_change: string | null;
};

export default function ProjectorPage() {
  const [status, setStatus] = useState<MarketStatus | null>(null);
  const [sectors, setSectors] = useState<SectorGroup[]>([]);
  const [news, setNews] = useState<NewsRow[]>([]);
  const [tickers, setTickers] = useState<TickerRow[]>([]);
  const [headline, setHeadline] = useState<NewsRow | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [st, sec, nw, stocks] = await Promise.all([
        apiGet<MarketStatus>("/market/status"),
        apiGet<SectorGroup[]>("/market/sectors"),
        apiGet<NewsRow[]>("/news"),
        apiGet<Array<{ ticker: string; last_traded_price: string; percent_change: string | null }>>(
          "/stocks",
        ),
      ]);
      setStatus(st);
      setSectors(sec);
      setNews(nw);
      setTickers(
        stocks.map((s) => ({
          ticker: s.ticker,
          last_traded_price: s.last_traded_price,
          percent_change: s.percent_change,
        })),
      );
      if (nw[0]) setHeadline((prev) => prev ?? nw[0]);
    } catch {
      /* backend may still be starting */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(id);
  }, [refresh]);

  useMarketWebSocket({
    onMessage: (msg) => {
      if (msg.event === "NEWS_RELEASED") {
        const raw = (msg.payload ?? msg) as Record<string, unknown>;
        const item: NewsRow = {
          id: Number(raw.id ?? 0),
          title: String(raw.title ?? raw.headline ?? ""),
          description: String(raw.description ?? ""),
          released_at: raw.released_at ? String(raw.released_at) : undefined,
        };
        if (item.title) {
          setHeadline(item);
          setNews((prev) => [item, ...prev.filter((n) => n.id !== item.id)].slice(0, 12));
        }
      }
      if (msg.event === "SIMULATION_CLOCK" || msg.event === "SIMULATION_STATUS") {
        const payload = (msg.payload ?? msg) as MarketStatus;
        setStatus((prev) => ({ ...(prev ?? { status: "running", market_change_pct: "0" }), ...payload }));
      }
      if (msg.event === "PRICE_UPDATED" || msg.event === "MARKET_PULSE") {
        void refresh();
      }
    },
  });

  const simLabel = useMemo(() => {
    if (!status?.elapsed) return "—";
    const duration = status.duration ?? "03:00:00";
    return `${status.elapsed} / ${duration}`;
  }, [status]);

  const tickerLine = useMemo(
    () =>
      tickers
        .slice(0, 40)
        .map((t) => `${t.ticker} ${fmtPct(t.percent_change)}`)
        .join("   ·   "),
    [tickers],
  );

  return (
    <div className="min-h-screen bg-black px-6 py-8 text-white">
      <header className="text-center">
        <h1 className="font-sans text-5xl font-bold tracking-[0.4em] md:text-7xl">TRADEVERSE</h1>
        <p className="mt-6 font-mono text-2xl tabular-nums text-white/70 md:text-4xl">{simLabel}</p>
      </header>

      <section className="mx-auto mt-12 max-w-6xl">
        <h2 className="text-center text-sm uppercase tracking-[0.35em] text-white/50">Market overview</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sectors.map((sector) => (
            <div
              key={sector.slug}
              className="flex items-center justify-between rounded border border-white/10 bg-white/5 px-6 py-5"
            >
              <span className="text-lg font-medium uppercase tracking-wide md:text-xl">{sector.name}</span>
              <span className={`font-mono text-2xl tabular-nums md:text-3xl ${signClass(sector.sector_change_pct)}`}>
                {fmtPct(sector.sector_change_pct)}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-12 max-w-5xl rounded border border-[#ef4444]/40 bg-[#ef4444]/10 px-8 py-10 text-center">
        <p className="text-sm uppercase tracking-[0.35em] text-[#ef4444]">Breaking news</p>
        <p className="mt-4 font-sans text-2xl font-semibold leading-snug md:text-4xl">
          {headline?.title ?? "Awaiting market news…"}
        </p>
        {headline?.description && (
          <p className="mt-4 text-lg text-white/70 md:text-2xl">{headline.description}</p>
        )}
      </section>

      <section className="mx-auto mt-10 max-w-6xl overflow-hidden border-y border-white/10 py-4">
        <p className="animate-pulse whitespace-nowrap font-mono text-xl tabular-nums md:text-2xl">
          {tickerLine || "Loading prices…"}
        </p>
      </section>

      {news.length > 1 && (
        <section className="mx-auto mt-10 max-w-4xl">
          <h3 className="text-xs uppercase tracking-[0.3em] text-white/40">Earlier headlines</h3>
          <ul className="mt-4 space-y-3">
            {news.slice(1, 6).map((item) => (
              <li key={item.id} className="text-lg text-white/80">
                {item.title}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

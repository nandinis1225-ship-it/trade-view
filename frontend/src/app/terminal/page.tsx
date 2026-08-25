"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BreakingNewsAlert } from "@/components/BreakingNewsAlert";
import type { NewsItem } from "@/components/NewsPanel";
import { StockSidebar, type SectorGroup, type SidebarStock } from "@/components/StockSidebar";
import { TradePanel } from "@/components/TradePanel";
import { WalletBar } from "@/components/WalletBar";
import { EventCompleteScreen, type EventResult } from "@/components/terminal/EventCompleteScreen";
import { NewsFeedPanel } from "@/components/terminal/NewsFeedPanel";
import { PinGateOverlay } from "@/components/terminal/PinGateOverlay";
import { RecoveryScreen } from "@/components/terminal/RecoveryScreen";
import { StartCountdown } from "@/components/terminal/StartCountdown";
import { WalletPanel } from "@/components/terminal/WalletPanel";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import {
  usePriceChart,
  type MarketPulseStock,
  type PriceUpdatePayload,
} from "@/hooks/usePriceChart";
import {
  apiGet,
  apiPost,
  fetchHealthConfig,
  fetchSessionBootstrap,
  isParticipantEventMode,
  joinSession,
  startLocalSimulation,
  validateEventPin,
} from "@/lib/participant-api";
import { isAuthError } from "@/lib/runtimeConfig";
import {
  markWalletToMarket,
  type PortfolioSnapshot,
  type WalletSnapshot,
} from "@/lib/portfolioValuation";

type Wallet = WalletSnapshot;
type Portfolio = PortfolioSnapshot;

type IPO = {
  id: number;
  company_name: string;
  ticker: string;
  issue_price: string;
  lot_size: number;
  maximum_lots_per_user: number;
};

type SimulationState = {
  status?: string;
  trading_enabled?: boolean;
  elapsed?: string;
  duration?: string;
  elapsed_sec?: number;
};

type GatePhase = "loading" | "start" | "recovery" | "countdown" | "ready";

function asMoney(v: unknown): string {
  if (v == null) return "0";
  return String(v);
}

function newsFromPayload(raw: Record<string, unknown> | undefined): NewsItem | null {
  if (!raw) return null;
  const title = String(raw.title ?? raw.headline ?? "").trim();
  if (!title) return null;
  return {
    id: Number(raw.id ?? 0),
    title,
    description: String(raw.description ?? ""),
    released_at: raw.released_at ? String(raw.released_at) : undefined,
  };
}

function mapPortfolioHoldings(
  holdings: Array<{
    ticker?: string | null;
    quantity: number;
    avg_cost?: string | number | null;
    market_price?: string | number | null;
    market_value?: string | number | null;
    unrealized_pnl?: string | number | null;
  }>,
): Portfolio["holdings"] {
  return (holdings ?? []).map((h) => ({
    ticker: h.ticker ?? null,
    quantity: h.quantity,
    avg_cost: h.avg_cost != null ? asMoney(h.avg_cost) : undefined,
    market_price: h.market_price != null ? asMoney(h.market_price) : undefined,
    market_value: h.market_value != null ? asMoney(h.market_value) : undefined,
    unrealized_pnl: h.unrealized_pnl != null ? asMoney(h.unrealized_pnl) : undefined,
  }));
}

function mapNewsItems(
  items: Array<{
    id: number;
    title: string;
    description?: string;
    released_at?: string;
    brief_points?: string[];
  }>,
): NewsItem[] {
  return items.map((n) => ({
    id: n.id,
    title: n.title,
    description: n.description ?? "",
    released_at: n.released_at,
    brief_points: n.brief_points,
  }));
}

export default function TerminalPage() {
  const eventMode = isParticipantEventMode();
  const [pinRequired, setPinRequired] = useState(eventMode);
  const [gatePhase, setGatePhase] = useState<GatePhase>("loading");

  const [traderId, setTraderId] = useState<number | null>(null);
  const [traderName, setTraderName] = useState("Trader");
  const [eventPin, setEventPin] = useState("");
  const [pinError, setPinError] = useState<string | null>(null);
  const [pinLoading, setPinLoading] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [startingSim, setStartingSim] = useState(false);
  const validatedPinRef = useRef("");

  const [stocks, setStocks] = useState<SidebarStock[]>([]);
  const [sectors, setSectors] = useState<SectorGroup[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [tradeCount, setTradeCount] = useState(0);
  const [breaking, setBreaking] = useState<NewsItem | null>(null);
  const [newsFeed, setNewsFeed] = useState<NewsItem[]>([]);
  const [showHoldings, setShowHoldings] = useState(false);
  const [ipos, setIpos] = useState<IPO[]>([]);
  const [ipoLots, setIpoLots] = useState(1);
  const [qty, setQty] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmSide, setConfirmSide] = useState<"buy" | "sell" | null>(null);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [tradingEnabled, setTradingEnabled] = useState(false);
  const [simStatus, setSimStatus] = useState<string>("not_started");
  const [simElapsed, setSimElapsed] = useState<string | null>(null);
  const [simDuration, setSimDuration] = useState<string | null>(null);

  const selected = useMemo(
    () => stocks.find((s) => s.id === selectedId) ?? null,
    [stocks, selectedId],
  );

  const { priceSeries, chartLoading, handlePriceUpdate, handleMarketPulse } =
    usePriceChart(selectedId, selected?.last_traded_price);

  const displayWallet = useMemo(
    () => markWalletToMarket(wallet, portfolio, stocks),
    [wallet, portfolio, stocks],
  );

  const holdingQty = useMemo(() => {
    if (!selected || !portfolio) return 0;
    return portfolio.holdings.find((h) => h.ticker === selected.ticker)?.quantity ?? 0;
  }, [selected, portfolio]);

  const dissolvedStocks = useMemo(
    () => stocks.filter((s) => s.is_open === false),
    [stocks],
  );

  const eventComplete = simStatus === "completed";

  const eventResult = useMemo<EventResult | null>(() => {
    if (!eventComplete || !displayWallet) return null;
    const cash = Number(displayWallet.available_cash ?? 0);
    const portfolioValue = Number(displayWallet.portfolio_value ?? 0);
    const holdingsValue = Math.max(0, portfolioValue - cash);
    return {
      participantName: traderName,
      startingCapital: displayWallet.starting_capital ?? "500000",
      finalCash: displayWallet.available_cash ?? "0",
      holdingsValue: String(holdingsValue),
      finalPortfolioValue: displayWallet.portfolio_value ?? "0",
      pnl: displayWallet.total_pnl ?? "0",
      returnPct: displayWallet.return_pct ?? "0",
      tradeCount,
    };
  }, [eventComplete, displayWallet, traderName, tradeCount]);

  const patchStockPrice = useCallback(
    (stockId: number, ltp: string, percentChange?: string) => {
      setStocks((prev) =>
        prev.map((s) =>
          s.id === stockId
            ? {
                ...s,
                last_traded_price: ltp,
                ...(percentChange != null ? { percent_change: percentChange } : {}),
              }
            : s,
        ),
      );
      setSectors((prev) =>
        prev.map((sector) => ({
          ...sector,
          stocks: sector.stocks.map((s) =>
            s.stock_id === stockId
              ? {
                  ...s,
                  last_traded_price: ltp,
                  ...(percentChange != null ? { percent_change: percentChange } : {}),
                }
              : s,
          ),
        })),
      );
    },
    [],
  );

  const applySimulationState = useCallback((sim: SimulationState | undefined) => {
    if (!sim) return;
    if (sim.status) setSimStatus(String(sim.status));
    if (sim.elapsed) setSimElapsed(String(sim.elapsed));
    if (sim.duration) setSimDuration(String(sim.duration));
    if (typeof sim.trading_enabled === "boolean") {
      setTradingEnabled(sim.trading_enabled);
    } else if (sim.status) {
      setTradingEnabled(sim.status === "running");
    }
  }, []);

  const showBreaking = useCallback((item: NewsItem) => {
    setBreaking(item);
    setNewsFeed((prev) => {
      const without = prev.filter((n) => n.id !== item.id);
      return [item, ...without].slice(0, 30);
    });
  }, []);

  const applyBootstrap = useCallback(
    (data: Awaited<ReturnType<typeof fetchSessionBootstrap>>) => {
      setTraderId(data.trader_id);
      if (data.trader_name) setTraderName(data.trader_name);
      if (data.trade_count != null) setTradeCount(data.trade_count);
      setWallet({
        available_cash: asMoney(data.wallet.available_cash),
        portfolio_value: asMoney(data.wallet.portfolio_value),
        total_pnl: asMoney(data.wallet.total_pnl ?? "0"),
        return_pct: asMoney(data.wallet.return_pct ?? "0"),
        starting_capital: data.wallet.starting_capital
          ? asMoney(data.wallet.starting_capital)
          : undefined,
      });
      setPortfolio({
        holdings: mapPortfolioHoldings(data.portfolio.holdings ?? []),
        starting_capital:
          data.portfolio.starting_capital != null
            ? asMoney(data.portfolio.starting_capital)
            : undefined,
        realized_pnl:
          data.portfolio.realized_pnl != null ? asMoney(data.portfolio.realized_pnl) : undefined,
        cash_blocked_ipo:
          data.portfolio.cash_blocked_ipo != null
            ? asMoney(data.portfolio.cash_blocked_ipo)
            : undefined,
      });
      applySimulationState(data.simulation as SimulationState);
      if (data.stocks?.length) {
        setStocks(
          data.stocks.map((s) => ({
            id: s.id,
            ticker: s.ticker,
            company_name: s.company_name ?? s.ticker,
            last_traded_price: s.ltp ?? s.last_traded_price ?? "0",
            percent_change: s.percent_change ?? null,
            is_open: s.is_open ?? true,
          })),
        );
        setSelectedId((prev) => {
          if (prev) return prev;
          return data.stocks.find((s) => s.is_open !== false)?.id ?? data.stocks[0].id;
        });
      }
      if (data.sectors?.length) setSectors(data.sectors);
      if (data.open_ipos?.length) setIpos(data.open_ipos);
      else setIpos([]);
      if (data.released_news?.length) {
        setNewsFeed(mapNewsItems(data.released_news));
      }
      return data;
    },
    [applySimulationState],
  );

  const resyncBootstrap = useCallback(async () => {
    const token = localStorage.getItem("mse_access_token");
    if (!token) return null;
    try {
      const data = await fetchSessionBootstrap();
      return applyBootstrap(data);
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      if (isAuthError(message)) {
        localStorage.removeItem("mse_access_token");
        localStorage.removeItem("mse_trader_id");
        setTraderId(null);
        setWallet(null);
        setPortfolio(null);
      }
      return null;
    }
  }, [applyBootstrap]);

  const refreshWallet = useCallback(async (explicitTraderId?: number) => {
    const id = explicitTraderId ?? traderId;
    if (!id) return;
    try {
      const [w, p] = await Promise.all([
        apiGet<Wallet>(`/traders/${id}/wallet`),
        apiGet<Portfolio>(`/traders/${id}/portfolio`),
      ]);
      setWallet({
        available_cash: asMoney(w.available_cash),
        portfolio_value: asMoney(w.portfolio_value),
        total_pnl: asMoney(w.total_pnl ?? "0"),
        return_pct: asMoney(w.return_pct ?? "0"),
        starting_capital: w.starting_capital ? asMoney(w.starting_capital) : undefined,
      });
      setPortfolio({
        holdings: mapPortfolioHoldings(p.holdings ?? []),
        starting_capital: p.starting_capital != null ? asMoney(p.starting_capital) : undefined,
        realized_pnl: p.realized_pnl != null ? asMoney(p.realized_pnl) : undefined,
        cash_blocked_ipo: p.cash_blocked_ipo != null ? asMoney(p.cash_blocked_ipo) : undefined,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : "";
      if (isAuthError(message)) {
        localStorage.removeItem("mse_access_token");
        localStorage.removeItem("mse_trader_id");
        setTraderId(null);
      }
    }
  }, [traderId]);

  const refresh = useCallback(async () => {
    if (gatePhase !== "ready" && gatePhase !== "countdown") return;
    try {
      const s = await apiGet<SidebarStock[]>("/stocks");
      setStocks(s);
      setSelectedId((prev) => prev ?? (s.length ? s[0].id : null));
      const data = await apiGet<SectorGroup[]>("/market/sectors");
      setSectors(data);
      const openIpos = await apiGet<IPO[]>("/ipos/open").catch(() => [] as IPO[]);
      setIpos(openIpos);
      if (traderId) await refreshWallet(traderId);
      const news = await apiGet<NewsItem[]>("/news").catch(() => [] as NewsItem[]);
      if (news.length) setNewsFeed(mapNewsItems(news.slice(0, 30)));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load data");
    }
  }, [refreshWallet, traderId, gatePhase]);

  useEffect(() => {
    void fetchHealthConfig()
      .then(async (health) => {
        const needsPin = Boolean(health.pin_required ?? health.participant_event_mode);
        setPinRequired(needsPin);

        const token = localStorage.getItem("mse_access_token");
        const savedName = localStorage.getItem("mse_trader_name");
        if (savedName) setTraderName(savedName);

        if (!needsPin) {
          if (token) {
            await resyncBootstrap();
            setGatePhase("ready");
          } else {
            setGatePhase("start");
          }
          return;
        }

        if (token) {
          const data = await resyncBootstrap();
          const sim = data?.simulation as SimulationState | undefined;
          const status = sim?.status ?? "not_started";
          const elapsedSec = Number(sim?.elapsed_sec ?? 0);
          const hasProgress =
            status === "running" || status === "completed" || elapsedSec > 0 || Boolean(data?.trader_id);

          if (hasProgress) {
            setGatePhase(status === "completed" ? "ready" : "recovery");
            if (status === "completed") return;
          } else {
            setGatePhase("start");
          }
        } else {
          setGatePhase("start");
        }
      })
      .catch(() => setGatePhase("start"));
  }, [resyncBootstrap]);

  useEffect(() => {
    if (gatePhase === "ready") void refresh();
  }, [gatePhase, refresh]);

  useEffect(() => {
    if (!breaking) return;
    const id = window.setTimeout(() => setBreaking(null), 18_000);
    return () => window.clearTimeout(id);
  }, [breaking]);

  const { connected } = useMarketWebSocket({
    enabled: gatePhase === "ready",
    onReconnect: () => void resyncBootstrap(),
    onMessage: (msg) => {
      if (msg.event === "NEWS_RELEASED") {
        const raw = (msg.payload ?? msg) as Record<string, unknown>;
        const item = newsFromPayload(raw);
        if (item) showBreaking(item);
      }
      if (msg.event === "SIMULATION_CLOCK" || msg.event === "SIMULATION_STATUS") {
        applySimulationState((msg.payload ?? msg) as SimulationState);
      }
      if (msg.event === "MARKET_PULSE") {
        const payload = (msg.payload ?? msg) as { stocks?: MarketPulseStock[] };
        const rows = payload.stocks ?? [];
        handleMarketPulse(rows);
        for (const row of rows) {
          patchStockPrice(row.stock_id, row.ltp, row.percent_change);
        }
      }
      if (msg.event === "PRICE_UPDATED") {
        const payload = (msg.payload ?? msg) as PriceUpdatePayload & { percent_change?: string };
        handlePriceUpdate(payload);
        const stockId = payload.stock_id;
        if (stockId) {
          const ltp =
            payload.ltp ??
            (payload.trades?.length ? payload.trades[payload.trades.length - 1].price : undefined);
          if (ltp) patchStockPrice(stockId, ltp, payload.percent_change);
        }
      }
      if (msg.event === "TRADE_EXECUTED") {
        void refreshWallet();
        setTradeCount((c) => c + 1);
      }
      if (msg.event === "WALLET_UPDATED" || msg.event === "PORTFOLIO_UPDATED") {
        void refreshWallet();
      }
      if (msg.event === "IPO_OPENED" || msg.event === "IPO_RESULT" || msg.event === "IPO_LISTED") {
        apiGet<IPO[]>("/ipos/open").then(setIpos).catch(() => []);
        void refreshWallet();
      }
    },
  });

  useEffect(() => {
    if (!connected || gatePhase !== "ready") return;
    const id = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(id);
  }, [connected, gatePhase, refresh]);

  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(id);
  }, [toast]);

  const beginEventStart = useCallback(async () => {
    const pin = validatedPinRef.current;
    setStartingSim(true);
    setError(null);
    try {
      await joinSession(traderName || "Trader");
      const data = await resyncBootstrap();
      const status = (data?.simulation as SimulationState | undefined)?.status;
      if (status !== "running" && status !== "completed") {
        await startLocalSimulation(pin);
        setSimStatus("running");
        setTradingEnabled(true);
      }
      await resyncBootstrap();
      await refresh();
      setGatePhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start simulation");
      setGatePhase("start");
    } finally {
      setStartingSim(false);
    }
  }, [traderName, resyncBootstrap, refresh]);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown < 0) {
      setCountdown(null);
      void beginEventStart();
      return;
    }
    const id = window.setTimeout(() => setCountdown((c) => (c === null ? null : c - 1)), 1000);
    return () => window.clearTimeout(id);
  }, [countdown, beginEventStart]);

  async function handleStartSubmit() {
    setPinLoading(true);
    setPinError(null);
    try {
      await validateEventPin(eventPin.trim());
      validatedPinRef.current = eventPin.trim();
      window.sessionStorage.setItem("tradeverse_pin_ok", "1");
      setCountdown(3);
      setGatePhase("countdown");
    } catch (e) {
      setPinError(e instanceof Error ? e.message : "Invalid PIN");
    } finally {
      setPinLoading(false);
    }
  }

  async function handleResumeSubmit() {
    setPinLoading(true);
    setPinError(null);
    try {
      await validateEventPin(eventPin.trim());
      validatedPinRef.current = eventPin.trim();
      window.sessionStorage.setItem("tradeverse_pin_ok", "1");
      await joinSession(traderName);
      const data = await resyncBootstrap();
      const status = (data?.simulation as SimulationState | undefined)?.status;
      if (status === "running" || status === "completed") {
        setGatePhase("ready");
        setToast("Simulation resumed");
      } else {
        setCountdown(3);
        setGatePhase("countdown");
      }
    } catch (e) {
      setPinError(e instanceof Error ? e.message : "Invalid PIN");
    } finally {
      setPinLoading(false);
    }
  }

  async function joinDev() {
    try {
      await joinSession(traderName || "Trader");
      await resyncBootstrap();
      setGatePhase("ready");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not join session");
    }
  }

  function openConfirm(side: "buy" | "sell") {
    setConfirmError(null);
    setConfirmSide(side);
  }

  function closeConfirm() {
    if (confirmLoading) return;
    setConfirmSide(null);
    setConfirmError(null);
  }

  async function executeOrder() {
    if (!traderId || !selectedId || !confirmSide || eventComplete) return;
    setConfirmLoading(true);
    setConfirmError(null);
    try {
      const res = await apiPost<{
        execution_summary?: { executed: boolean; message: string };
      }>("/orders", {
        trader_id: traderId,
        stock_id: selectedId,
        side: confirmSide,
        order_type: "market",
        quantity: qty,
        price: null,
      });
      if (res.execution_summary && !res.execution_summary.executed) {
        setConfirmError(res.execution_summary.message);
        return;
      }
      setToast(res.execution_summary?.message ?? `${confirmSide.toUpperCase()} order placed`);
      setConfirmSide(null);
      await refreshWallet(traderId);
    } catch (e) {
      setConfirmError(e instanceof Error ? e.message : "Order failed");
    } finally {
      setConfirmLoading(false);
    }
  }

  async function applyIpo() {
    if (!traderId || !ipos[0] || eventComplete) return;
    try {
      await apiPost(`/ipos/${ipos[0].id}/apply`, { trader_id: traderId, requested_lots: ipoLots });
      setToast("IPO application submitted");
      await refreshWallet(traderId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "IPO failed");
    }
  }

  if (gatePhase === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-[var(--muted)]">
        Loading…
      </div>
    );
  }

  if (!pinRequired && gatePhase === "start") {
    return (
      <div className="min-h-screen font-sans text-[var(--foreground)]">
        <div className="mx-auto max-w-sm px-4 py-16">
          <h1 className="text-xl font-bold tracking-widest">TRADEVERSE</h1>
          <p className="mt-2 text-sm text-[var(--muted)]">Enter your name to join the simulation.</p>
          <input
            className="mt-6 w-full rounded border border-[var(--line)] bg-[var(--background)] px-3 py-2.5"
            value={traderName}
            onChange={(e) => setTraderName(e.target.value)}
            placeholder="Your name"
          />
          <button
            type="button"
            className="mt-4 w-full rounded border border-[var(--accent)] py-2.5 text-[var(--accent)]"
            onClick={() => void joinDev()}
          >
            Continue
          </button>
          {error && <p className="mt-3 text-sm text-[#ef4444]">{error}</p>}
        </div>
      </div>
    );
  }

  const tradingLocked = eventComplete || gatePhase !== "ready";

  return (
    <div className="flex min-h-screen flex-col text-sm text-[var(--foreground)]">
      <WalletBar
        cash={displayWallet?.available_cash}
        portfolio={displayWallet?.portfolio_value}
        pnl={displayWallet?.total_pnl}
        elapsed={simElapsed}
        duration={simDuration}
        onHoldings={() => setShowHoldings((v) => !v)}
        showHoldings={showHoldings}
      />

      <WalletPanel
        open={showHoldings}
        portfolio={portfolio}
        availableCash={displayWallet?.available_cash}
        portfolioValue={displayWallet?.portfolio_value}
        stocks={stocks}
      />

      <BreakingNewsAlert news={breaking} onDismiss={() => setBreaking(null)} />

      <div
        className={`grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-[minmax(200px,260px)_1fr] xl:grid-cols-[minmax(220px,280px)_1fr_minmax(220px,300px)] ${
          tradingLocked && !eventComplete ? "pointer-events-none opacity-60" : ""
        }`}
      >
        <StockSidebar
          sectors={sectors}
          dissolved={dissolvedStocks}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <TradePanel
          stock={selected}
          priceSeries={priceSeries}
          chartLoading={chartLoading}
          qty={qty}
          onQtyChange={setQty}
          holdingQty={holdingQty}
          tradingEnabled={tradingEnabled && !eventComplete}
          onBuy={() => openConfirm("buy")}
          onSell={() => openConfirm("sell")}
          confirmSide={confirmSide}
          confirmLoading={confirmLoading}
          confirmError={confirmError}
          onConfirm={() => void executeOrder()}
          onCancelConfirm={closeConfirm}
          ipo={ipos[0] ?? null}
          ipoLots={ipoLots}
          onIpoLotsChange={setIpoLots}
          onIpoApply={ipos[0] && !eventComplete ? applyIpo : undefined}
        />
        <NewsFeedPanel news={newsFeed} />
      </div>

      {error && <p className="px-4 py-2 text-xs text-[#ef4444]">{error}</p>}

      {toast && (
        <div className="fixed bottom-4 left-4 max-w-sm rounded border border-[var(--line)] bg-[var(--panel)] p-3 text-xs shadow-lg">
          {toast}
        </div>
      )}

      {gatePhase === "start" && pinRequired && (
        <PinGateOverlay
          name={traderName}
          pin={eventPin}
          error={pinError}
          loading={pinLoading || startingSim}
          onNameChange={setTraderName}
          onPinChange={setEventPin}
          onSubmit={() => void handleStartSubmit()}
        />
      )}

      {gatePhase === "recovery" && (
        <RecoveryScreen
          participantName={traderName}
          elapsed={simElapsed ?? "00:00:00"}
          duration={simDuration ?? "03:00:00"}
          pnl={displayWallet?.total_pnl ?? "0"}
          returnPct={displayWallet?.return_pct ?? "0"}
          pin={eventPin}
          error={pinError}
          loading={pinLoading}
          onPinChange={setEventPin}
          onResume={() => void handleResumeSubmit()}
        />
      )}

      {gatePhase === "countdown" && countdown !== null && <StartCountdown value={countdown} />}

      {eventResult && <EventCompleteScreen result={eventResult} />}
    </div>
  );
}

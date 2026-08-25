"use client";

import { useCallback, useEffect, useState } from "react";
import { NewsPanel, type NewsItem } from "@/components/NewsPanel";
import { useMarketWebSocket } from "@/hooks/useMarketWebSocket";
import {
  SCENARIO_STEPS,
  devAiSeed,
  devAiTick,
  devJumpCheckpoint,
  devReleaseNextNews,
  devSetSpeed,
  devSimAction,
  devVerifyIdempotency,
  devGet,
  fetchDevAiState,
  fetchDevDissolution,
  fetchDevIpos,
  fetchDevLogs,
  fetchDevMarketState,
  fetchDevPortfolio,
  fetchDevStatus,
  fetchDevTraders,
  isDeveloperMode,
  type DevCheckpoint,
  type DevLogEntry,
  type DevSimStatus,
} from "@/lib/developerApi";

const TABS = [
  "Simulation",
  "Speed",
  "Timeline",
  "News",
  "AI",
  "IPO",
  "Dissolution",
  "Market",
  "Portfolio",
  "Logs",
  "Recovery",
  "Scenarios",
] as const;

type Tab = (typeof TABS)[number];

const SPEED_PRESETS = [1, 5, 10, 30, 60];

function fmtCountdown(sec: number | null | undefined) {
  if (sec == null) return "—";
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export default function DeveloperPage() {
  const [tab, setTab] = useState<Tab>("Simulation");
  const [status, setStatus] = useState<DevSimStatus | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [logs, setLogs] = useState<DevLogEntry[]>([]);
  const [market, setMarket] = useState<Record<string, unknown> | null>(null);
  const [aiState, setAiState] = useState<Record<string, unknown> | null>(null);
  const [ipos, setIpos] = useState<unknown[]>([]);
  const [dissolutions, setDissolutions] = useState<unknown[]>([]);
  const [traders, setTraders] = useState<Array<{ id: number; name: string }>>([]);
  const [selectedTrader, setSelectedTrader] = useState<number | null>(null);
  const [portfolio, setPortfolio] = useState<unknown>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [scenarioDone, setScenarioDone] = useState<Record<number, boolean>>({});
  const [resetConfirm, setResetConfirm] = useState(false);

  const refreshStatus = useCallback(async () => {
    try {
      const data = await fetchDevStatus();
      setStatus(data);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed to load status");
    }
  }, []);

  const refreshNews = useCallback(async () => {
    try {
      const data = await devGet<Array<{ id: number; title: string; description?: string }>>("/news");
      setNews(
        data.map((n) => ({
          id: n.id,
          title: n.title,
          description: n.description ?? "",
          released_at: null,
          effective_impact: null,
        })),
      );
    } catch {
      /* non-fatal */
    }
  }, []);

  const refreshLogs = useCallback(async () => {
    try {
      setLogs(await fetchDevLogs(150));
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    if (!isDeveloperMode()) {
      setMsg("Developer mode is not enabled. Run npm run dev or developer-launch.bat.");
      return;
    }
    refreshStatus();
    refreshNews();
    refreshLogs();
    fetchDevTraders()
      .then((t) => {
        setTraders(t);
        if (t.length > 0) setSelectedTrader(t[0].id);
      })
      .catch(() => undefined);
  }, [refreshStatus, refreshNews, refreshLogs]);

  useMarketWebSocket({
    onMessage: (m) => {
      if (m.event === "SIMULATION_CLOCK" || m.event === "SIMULATION_STATUS") {
        setStatus((prev) => ({ ...(prev ?? ({} as DevSimStatus)), ...(m.payload as DevSimStatus) }));
      }
      if (m.event === "NEWS_RELEASED") refreshNews();
    },
  });

  useEffect(() => {
    const id = setInterval(() => refreshStatus(), 5000);
    return () => clearInterval(id);
  }, [refreshStatus]);

  async function act(action: "start" | "stop" | "resume" | "reset" | "restart") {
    if (action === "reset" && !resetConfirm) {
      setResetConfirm(true);
      setMsg("Click RESET again to confirm developer simulation reset.");
      return;
    }
    setResetConfirm(false);
    setBusy(true);
    setMsg("");
    try {
      await devSimAction(action);
      setMsg(`${action.toUpperCase()} OK`);
      await refreshStatus();
      if (action === "reset") {
        setNews([]);
        await refreshNews();
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : `${action} failed`);
    } finally {
      setBusy(false);
    }
  }

  async function jump(cp: DevCheckpoint) {
    if (
      cp.sim_offset_sec != null &&
      status &&
      cp.sim_offset_sec < status.elapsed_sec &&
      !window.confirm(`Jump backward to ${cp.timestamp}? This resets simulation state.`)
    ) {
      return;
    }
    setBusy(true);
    try {
      await devJumpCheckpoint(cp.checkpoint_id, true);
      setMsg(`Jumped to checkpoint ${cp.checkpoint_id}`);
      await refreshStatus();
      await refreshLogs();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Jump failed");
    } finally {
      setBusy(false);
    }
  }

  async function loadTabData() {
    if (tab === "Market") {
      setMarket((await fetchDevMarketState()) as Record<string, unknown>);
    }
    if (tab === "AI") {
      setAiState((await fetchDevAiState()) as Record<string, unknown>);
    }
    if (tab === "IPO") {
      setIpos(await fetchDevIpos());
    }
    if (tab === "Dissolution") {
      setDissolutions(await fetchDevDissolution());
    }
    if (tab === "Logs") {
      await refreshLogs();
    }
    if (tab === "Portfolio" && selectedTrader) {
      setPortfolio(await fetchDevPortfolio(selectedTrader));
    }
  }

  useEffect(() => {
    if (!isDeveloperMode()) return;
    loadTabData().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, selectedTrader]);

  if (!isDeveloperMode()) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-black p-8 font-mono text-white">
        <p className="max-w-md text-center text-yellow-300">{msg || "Developer mode unavailable."}</p>
      </main>
    );
  }

  const checkpoints = status?.checkpoints ?? [];

  return (
    <main className="min-h-screen bg-black font-mono text-white">
      <header className="sticky top-0 z-30 border-b border-neutral-800 bg-black/95 px-4 py-3 backdrop-blur">
        <h1 className="text-lg font-bold tracking-widest">TRADEVERSE DEVELOPER</h1>
        <p className="text-xs text-neutral-500">Internal testing only — not included in participant builds</p>
        {status && (
          <p className="mt-2 text-sm text-neutral-300">
            {status.elapsed} / {status.duration} · {status.current_phase} · {status.status} ·{" "}
            {status.sim_speed_multiplier}x
          </p>
        )}
        {msg && <p className="mt-1 text-sm text-yellow-300">{msg}</p>}
      </header>

      <nav className="flex gap-1 overflow-x-auto border-b border-neutral-800 px-2 py-2 text-xs">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`shrink-0 rounded px-3 py-2 ${tab === t ? "bg-neutral-700" : "bg-neutral-900 hover:bg-neutral-800"}`}
          >
            {t}
          </button>
        ))}
      </nav>

      <div className="mx-auto max-w-5xl p-4">
        {tab === "Simulation" && (
          <section className="space-y-4">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
              {(["start", "stop", "resume", "reset", "restart"] as const).map((a) => (
                <button
                  key={a}
                  disabled={busy}
                  onClick={() => act(a)}
                  className="bg-neutral-800 px-3 py-3 text-sm uppercase hover:bg-neutral-700 disabled:opacity-50"
                >
                  {a}
                </button>
              ))}
            </div>
            {status && (
              <div className="space-y-2 border border-neutral-700 p-4 text-sm">
                <p>Current: {status.current_event?.headline ?? "—"}</p>
                <p>Next: {status.next_event?.headline ?? "—"} (in {fmtCountdown(status.seconds_to_next_event)})</p>
                <p>
                  Checkpoints: {status.completed_checkpoint_count}/{status.total_checkpoint_count}
                </p>
              </div>
            )}
          </section>
        )}

        {tab === "Speed" && (
          <section className="space-y-4">
            <p className="text-sm text-neutral-400">
              Accelerated testing only. Event timeline schedule is unchanged.
            </p>
            <div className="flex flex-wrap gap-2">
              {SPEED_PRESETS.map((s) => (
                <button
                  key={s}
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await devSetSpeed(s);
                      setMsg(`Speed set to ${s}x`);
                      await refreshStatus();
                    } catch (e) {
                      setMsg(e instanceof Error ? e.message : "Speed change failed");
                    } finally {
                      setBusy(false);
                    }
                  }}
                  className={`px-4 py-2 ${status?.sim_speed_multiplier === s ? "bg-green-800" : "bg-neutral-800"}`}
                >
                  {s}x
                </button>
              ))}
            </div>
          </section>
        )}

        {tab === "Timeline" && (
          <section className="max-h-[70vh] overflow-y-auto border border-neutral-700">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-neutral-900">
                <tr>
                  <th className="p-2">Time</th>
                  <th className="p-2">Type</th>
                  <th className="p-2">Headline</th>
                  <th className="p-2">Status</th>
                  <th className="p-2" />
                </tr>
              </thead>
              <tbody>
                {checkpoints.map((c) => (
                  <tr key={c.checkpoint_id} className="border-t border-neutral-800">
                    <td className="p-2">{c.timestamp}</td>
                    <td className="p-2">{c.type}</td>
                    <td className="p-2">{c.headline}</td>
                    <td className="p-2">{c.status}</td>
                    <td className="p-2">
                      <button
                        disabled={busy}
                        onClick={() => jump(c)}
                        className="text-green-400 hover:underline disabled:opacity-50"
                      >
                        Jump
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {tab === "News" && (
          <section className="space-y-4">
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await devReleaseNextNews();
                  setMsg("Released next news checkpoint");
                  await refreshStatus();
                  await refreshNews();
                  await refreshLogs();
                } catch (e) {
                  setMsg(e instanceof Error ? e.message : "Release failed");
                } finally {
                  setBusy(false);
                }
              }}
              className="bg-blue-800 px-4 py-2 text-sm"
            >
              Release next news
            </button>
            <NewsPanel news={news} selectedNews={null} onSelectNews={() => undefined} />
          </section>
        )}

        {tab === "AI" && (
          <section className="space-y-4">
            <div className="flex gap-2">
              <button disabled={busy} onClick={() => devAiSeed().then(() => setMsg("AI seeded"))} className="bg-neutral-800 px-4 py-2">
                Seed agents
              </button>
              <button
                disabled={busy}
                onClick={async () => {
                  const r = await devAiTick();
                  setMsg(`AI tick: ${JSON.stringify(r)}`);
                  setAiState((await fetchDevAiState()) as Record<string, unknown>);
                }}
                className="bg-neutral-800 px-4 py-2"
              >
                Manual tick
              </button>
            </div>
            <pre className="overflow-auto rounded border border-neutral-700 p-3 text-xs">
              {JSON.stringify(aiState, null, 2)}
            </pre>
          </section>
        )}

        {tab === "IPO" && (
          <pre className="overflow-auto rounded border border-neutral-700 p-3 text-xs">
            {JSON.stringify(ipos, null, 2)}
          </pre>
        )}

        {tab === "Dissolution" && (
          <section className="space-y-2">
            {dissolutions.map((d, i) => (
              <div key={i} className="border border-neutral-700 p-3 text-sm">
                <pre>{JSON.stringify(d, null, 2)}</pre>
                <button
                  disabled={busy}
                  onClick={async () => {
                    const item = d as { checkpoint_id?: number };
                    if (item.checkpoint_id) await jump({ checkpoint_id: item.checkpoint_id, type: "COMPANY_DISSOLUTION", headline: "", status: "pending", timestamp: "" });
                  }}
                  className="mt-2 text-green-400"
                >
                  Jump to dissolution
                </button>
              </div>
            ))}
          </section>
        )}

        {tab === "Market" && (
          <pre className="max-h-[70vh] overflow-auto rounded border border-neutral-700 p-3 text-xs">
            {JSON.stringify(market, null, 2)}
          </pre>
        )}

        {tab === "Portfolio" && (
          <section className="space-y-4">
            <select
              value={selectedTrader ?? ""}
              onChange={(e) => setSelectedTrader(Number(e.target.value))}
              className="rounded border border-neutral-700 bg-neutral-900 px-3 py-2"
            >
              {traders.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} (#{t.id})
                </option>
              ))}
            </select>
            <pre className="overflow-auto rounded border border-neutral-700 p-3 text-xs">
              {JSON.stringify(portfolio, null, 2)}
            </pre>
          </section>
        )}

        {tab === "Logs" && (
          <div className="max-h-[70vh] space-y-1 overflow-y-auto text-xs">
            {logs.map((l) => (
              <div key={l.id} className="border-b border-neutral-800 py-1">
                <span className="text-neutral-500">{l.sim_elapsed_sec.toFixed(0)}s</span>{" "}
                <span className="text-blue-300">{l.event_type}</span>{" "}
                {JSON.stringify(l.detail)}
              </div>
            ))}
          </div>
        )}

        {tab === "Recovery" && (
          <section className="space-y-4 text-sm">
            <p>1. Run a simulation segment, then close the browser tab and reopen /terminal.</p>
            <p>2. Restart the backend process, then verify bootstrap state matches.</p>
            <button
              disabled={busy}
              onClick={async () => {
                const r = await devVerifyIdempotency();
                setMsg(JSON.stringify(r));
              }}
              className="bg-neutral-800 px-4 py-2"
            >
              Verify idempotency
            </button>
            <button
              disabled={busy}
              onClick={() => window.location.reload()}
              className="ml-2 bg-neutral-800 px-4 py-2"
            >
              Reload dashboard
            </button>
          </section>
        )}

        {tab === "Scenarios" && (
          <section className="space-y-2">
            {SCENARIO_STEPS.map((step, i) => (
              <label key={step} className="flex items-center gap-3 border border-neutral-800 p-3 text-sm">
                <input
                  type="checkbox"
                  checked={!!scenarioDone[i]}
                  onChange={(e) => setScenarioDone((prev) => ({ ...prev, [i]: e.target.checked }))}
                />
                {i + 1}. {step}
              </label>
            ))}
            <p className="text-xs text-neutral-500">
              Complete all steps in developer mode at elevated speed before building the participant package.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}

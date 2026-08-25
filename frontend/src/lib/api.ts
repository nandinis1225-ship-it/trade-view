import type { SectorGroup } from "@/components/StockSidebar";
import type { LeaderboardRow } from "@/components/Leaderboard";
import { getRuntimeConfig, isAuthError } from "@/lib/runtimeConfig";

const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";
const REQUEST_TIMEOUT_MS = 30_000;

function isNgrokHost(hostname: string): boolean {
  return (
    hostname.endsWith(".ngrok-free.dev") ||
    hostname.endsWith(".ngrok-free.app") ||
    hostname.endsWith(".ngrok.app") ||
    hostname.endsWith(".ngrok.io")
  );
}

function defaultHeaders(): HeadersInit {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined" && isNgrokHost(window.location.hostname)) {
    headers["ngrok-skip-browser-warning"] = "1";
  }
  return headers;
}

function isProductionBuild(): boolean {
  return process.env.NODE_ENV === "production";
}

/** Resolve API base URL: runtime config, env, then offline default port 8765. */
export function getApiBaseUrl(): string {
  const rt = getRuntimeConfig()?.apiUrl?.replace(/\/$/, "");
  if (rt) return rt;
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (envUrl) return envUrl;
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8765`;
  }
  return "http://127.0.0.1:8765";
}

export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${API_PREFIX}${normalized}`;
}

export function wsUrl(): string {
  const rtWs = getRuntimeConfig()?.wsUrl?.replace(/\/$/, "");
  const explicit = rtWs ?? process.env.NEXT_PUBLIC_WS_URL?.replace(/\/$/, "");
  // Map https→wss and http→ws explicitly (avoid fragile string replace).
  const base =
    explicit ??
    getApiBaseUrl().replace(/^https:/i, "wss:").replace(/^http:/i, "ws:");
  const path = `${base}${API_PREFIX}/ws`;
  if (typeof window === "undefined") return path;
  const token = window.localStorage.getItem("mse_access_token");
  if (!token) return path;
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}token=${encodeURIComponent(token)}`;
}

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("mse_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchWithTimeout(
  input: string,
  init?: RequestInit,
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, {
      ...init,
      headers: { ...defaultHeaders(), ...authHeaders(), ...(init?.headers ?? {}) },
      signal: controller.signal,
    });
  } catch (e) {
    if (e instanceof Error && e.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
    }
    if (e instanceof TypeError || (e instanceof Error && /Failed to fetch/i.test(e.message))) {
      throw new Error(
        `Backend unreachable at ${getApiBaseUrl()} — restart TRADEVERSE (Failed to fetch)`,
      );
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

async function parseError(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const json = JSON.parse(text);
    if (json.detail) return `${res.status} ${String(json.detail)}`;
  } catch {
    /* use raw text */
  }
  return text || `${res.status} error`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), { method: "DELETE" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "";
  const key = "mse_session_id";
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(key, id);
  }
  return id;
}

export function isLocalInstance(): boolean {
  const rt = getRuntimeConfig()?.localInstance;
  if (rt === true) return true;
  return process.env.NEXT_PUBLIC_LOCAL_INSTANCE === "true";
}

export function isParticipantEventMode(): boolean {
  const rt = getRuntimeConfig()?.participantEventMode;
  if (rt === true) return true;
  return process.env.NEXT_PUBLIC_PARTICIPANT_EVENT_MODE === "true";
}

export function isPinRequired(): boolean {
  const rt = getRuntimeConfig()?.pinRequired;
  if (rt === true) return true;
  return isParticipantEventMode();
}

export function getLeaderboardCollectorUrl(): string | null {
  const url = process.env.NEXT_PUBLIC_LEADERBOARD_URL?.replace(/\/$/, "");
  return url || null;
}

export function getSupabaseLeaderboardConfig(): {
  url: string;
  key: string;
  table: string;
} | null {
  const rt = getRuntimeConfig();
  const url = (rt?.supabaseUrl ?? process.env.NEXT_PUBLIC_SUPABASE_URL)?.replace(/\/$/, "");
  const key = (rt?.supabaseAnonKey ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)?.trim();
  if (!url || !key) return null;
  return {
    url,
    key,
    table:
      rt?.supabaseLeaderboardTable ??
      process.env.NEXT_PUBLIC_SUPABASE_LEADERBOARD_TABLE ??
      "participant_snapshots",
  };
}

export function hasRemoteLeaderboard(): boolean {
  if (isParticipantEventMode()) return false;
  return getSupabaseLeaderboardConfig() !== null || getLeaderboardCollectorUrl() !== null;
}

export async function fetchCollectorLeaderboard(): Promise<LeaderboardRow[]> {
  const result = await fetchLeaderboardWithDiagnostics();
  return result.rows;
}

export type LeaderboardDiagnostics = {
  rows: LeaderboardRow[];
  source: "supabase" | "collector" | "none";
  endpoint: string;
  ok: boolean;
  status?: number;
  error?: string;
  rowCount: number;
};

export async function fetchLeaderboardWithDiagnostics(): Promise<LeaderboardDiagnostics> {
  const supa = getSupabaseLeaderboardConfig();
  if (supa) {
    const endpoint = `${supa.url}/rest/v1/${supa.table}?select=*&order=return_pct.desc`;
    try {
      const res = await fetch(endpoint, {
        cache: "no-store",
        headers: {
          apikey: supa.key,
          Authorization: `Bearer ${supa.key}`,
        },
      });
      if (!res.ok) {
        const text = await res.text();
        return {
          rows: [],
          source: "supabase",
          endpoint,
          ok: false,
          status: res.status,
          error: text.slice(0, 300),
          rowCount: 0,
        };
      }
      const raw = (await res.json()) as Array<Record<string, unknown>>;
      const bySession = new Map<string, Record<string, unknown>>();
      for (const r of raw) {
        const sid = String(r.session_id ?? r.display_name ?? "");
        if (!sid || bySession.has(sid)) continue;
        bySession.set(sid, r);
      }
      const deduped = Array.from(bySession.values());
      // #region agent log
      fetch("http://127.0.0.1:7751/ingest/a915aa99-33fd-43fa-bac6-36d58d56dd08", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Debug-Session-Id": "ac2555" },
        body: JSON.stringify({
          sessionId: "ac2555",
          location: "api.ts:fetchLeaderboardWithDiagnostics",
          message: "leaderboard dedupe",
          data: { rawCount: raw.length, dedupedCount: deduped.length },
          timestamp: Date.now(),
          hypothesisId: "A",
        }),
      }).catch(() => {});
      // #endregion
      const mapped = deduped.map((r, i) => {
        const tradeCount = Number(r.trade_count ?? 0);
        const returnPct = Number(r.return_pct ?? 0);
        const score = returnPct + tradeCount * 0.01;
        return {
          rank: i + 1,
          trader_id: 0,
          name: String(r.display_name ?? "—"),
          portfolio_value: String(r.portfolio_value ?? "0"),
          return_pct: String(r.return_pct ?? "0"),
          trade_count: tradeCount,
          session_id: String(r.session_id ?? ""),
          score,
        };
      });
      mapped.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
      const rows = mapped.map((r, i) => ({
        rank: i + 1,
        trader_id: r.trader_id,
        name: r.name,
        portfolio_value: r.portfolio_value,
        return_pct: r.return_pct,
        trade_count: r.trade_count,
        session_id: r.session_id,
      }));
      return {
        rows,
        source: "supabase",
        endpoint,
        ok: true,
        status: res.status,
        rowCount: rows.length,
      };
    } catch (e) {
      return {
        rows: [],
        source: "supabase",
        endpoint,
        ok: false,
        error: e instanceof Error ? e.message : String(e),
        rowCount: 0,
      };
    }
  }

  const base = getLeaderboardCollectorUrl();
  if (!base) {
    return {
      rows: [],
      source: "none",
      endpoint: "",
      ok: false,
      error: "No Supabase or collector URL configured",
      rowCount: 0,
    };
  }
  const endpoint = `${base}/api/v1/leaderboard`;
  try {
    const res = await fetch(endpoint, { cache: "no-store" });
    if (!res.ok) {
      return {
        rows: [],
        source: "collector",
        endpoint,
        ok: false,
        status: res.status,
        error: await res.text(),
        rowCount: 0,
      };
    }
    const raw = (await res.json()) as Array<Record<string, unknown>>;
    const rows = raw.map((r, i) => ({
      rank: Number(r.rank ?? i + 1),
      trader_id: Number(r.trader_id ?? 0),
      name: String(r.name ?? r.display_name ?? "—"),
      portfolio_value: String(r.portfolio_value ?? "0"),
      return_pct: String(r.return_pct ?? "0"),
      trade_count: Number(r.trade_count ?? 0),
    }));
    return {
      rows,
      source: "collector",
      endpoint,
      ok: true,
      status: res.status,
      rowCount: rows.length,
    };
  } catch (e) {
    return {
      rows: [],
      source: "collector",
      endpoint,
      ok: false,
      error: e instanceof Error ? e.message : String(e),
      rowCount: 0,
    };
  }
}

export async function probeMarketApi(path: string): Promise<{ ok: boolean; url: string; error?: string }> {
  const url = apiUrl(path);
  try {
    const res = await fetch(url, { cache: "no-store", headers: defaultHeaders() });
    if (!res.ok) {
      return { ok: false, url, error: `${res.status} ${await res.text()}` };
    }
    return { ok: true, url };
  } catch (e) {
    return { ok: false, url, error: e instanceof Error ? e.message : String(e) };
  }
}

/** Ask backend to push this trader's score to Supabase / LAN collector. */
export async function pushLeaderboardSnapshot(): Promise<boolean> {
  if (isParticipantEventMode()) return false;
  try {
    const res = await apiPost<{ ok?: boolean }>("/session/push-leaderboard");
    if (res.ok) return true;
  } catch {
    /* backend may be busy — try direct Supabase */
  }
  return pushLeaderboardSnapshotDirect();
}

/** Browser → Supabase fallback when backend push fails. */
export async function pushLeaderboardSnapshotDirect(): Promise<boolean> {
  const supa = getSupabaseLeaderboardConfig();
  if (!supa) return false;
  try {
    const data = await fetchSessionBootstrap();
    const sessionId =
      typeof window !== "undefined"
        ? window.localStorage.getItem("mse_session_id") ?? String(data.trader_id)
        : String(data.trader_id);
    const holdings = (data.portfolio?.holdings ?? []).map((h) => ({
      ticker: h.ticker,
      quantity: h.quantity,
      avg_cost: h.avg_cost ?? "0",
    }));
    const row = {
      session_id: sessionId,
      display_name:
        typeof window !== "undefined"
          ? window.localStorage.getItem("mse_trader_name") ?? "Trader"
          : "Trader",
      cash: Number(data.wallet?.available_cash ?? 0),
      holdings_json: holdings,
      realized_pnl: Number(data.portfolio?.realized_pnl ?? 0),
      unrealized_pnl: 0,
      portfolio_value: Number(data.wallet?.portfolio_value ?? 0),
      return_pct: Number(data.wallet?.return_pct ?? 0),
      trade_count: 0,
      updated_at: new Date().toISOString(),
    };
    const endpoint = `${supa.url}/rest/v1/${supa.table}?on_conflict=session_id`;
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        apikey: supa.key,
        Authorization: `Bearer ${supa.key}`,
        "Content-Type": "application/json",
        Prefer: "resolution=merge-duplicates",
      },
      body: JSON.stringify(row),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchLeaderboardForDisplay(): Promise<LeaderboardRow[]> {
  if (hasRemoteLeaderboard()) {
    try {
      return await fetchCollectorLeaderboard();
    } catch {
      /* fall through to local API */
    }
  }
  return apiGet<LeaderboardRow[]>("/leaderboard");
}

export async function joinSession(displayName: string): Promise<{
  trader_id: number;
  display_name: string;
  access_token: string;
  session_id?: string;
}> {
  const sessionId = getOrCreateSessionId();
  const res = await apiPost<{
    trader_id: number;
    display_name: string;
    access_token: string;
    session_id?: string;
  }>("/auth/join", { display_name: displayName, session_id: sessionId });
  if (typeof window !== "undefined") {
    window.localStorage.setItem("mse_access_token", res.access_token);
    window.localStorage.setItem("mse_trader_id", String(res.trader_id));
    window.localStorage.setItem("mse_trader_name", res.display_name);
    if (res.session_id) {
      window.localStorage.setItem("mse_session_id", res.session_id);
    }
  }
  return res;
}

export async function validateEventPin(pin: string): Promise<void> {
  await apiPost("/auth/validate-pin", { pin });
}

async function bootstrapSimulation(): Promise<void> {
  try {
    await apiPost("/simulation/bootstrap");
  } catch (e) {
    const msg = e instanceof Error ? e.message : "";
    if (/timeline|TIMELINE_DECRYPT/i.test(msg)) throw e;
    /* universe may already exist */
  }
}

export async function startEventSimulation(eventPin: string): Promise<Record<string, unknown>> {
  await bootstrapSimulation();
  return apiPost<Record<string, unknown>>("/simulation/event-start", { event_pin: eventPin });
}

export async function startLocalSimulation(eventPin?: string): Promise<Record<string, unknown>> {
  if (isParticipantEventMode()) {
    if (!eventPin) throw new Error("Event PIN required");
    return startEventSimulation(eventPin);
  }
  await bootstrapSimulation();
  return apiPost<Record<string, unknown>>("/simulation/start");
}

export async function resetLocalSimulation(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>("/simulation/reset");
}

export type OrganizerResetResult = {
  ok?: boolean;
  action?: string;
  status?: string;
  global_reset_signaled?: boolean;
  leaderboard_cleared?: boolean;
  clients_should_rejoin?: boolean;
};

export type BuildParticipantZipResult = {
  ok?: boolean;
  action?: string;
  zip_path?: string;
  zip_name?: string;
  zip_size_bytes?: number;
  zip_size_mb?: string;
};

export async function organizerResetMarket(passkey: string): Promise<OrganizerResetResult> {
  return apiPost<OrganizerResetResult>("/simulation/organizer/reset-all", { passkey });
}

export async function organizerBuildParticipantZip(
  passkey: string,
): Promise<BuildParticipantZipResult> {
  return apiPost<BuildParticipantZipResult>("/simulation/organizer/build-participant-zip", {
    passkey,
  });
}

export type OrganizerMarketDashboard = {
  elapsed: string;
  current_phase: string;
  status: string;
  market_change_pct: string;
  latest_news: {
    id: number;
    title: string;
    description: string;
    released_at: string | null;
    sector_impacts: Record<string, number>;
  } | null;
  news: Array<{
    id: number;
    title: string;
    description: string;
    released_at: string | null;
    sector_impacts: Record<string, number>;
  }>;
};

export async function organizerMarketDashboard(
  passkey: string,
): Promise<OrganizerMarketDashboard> {
  return apiPost<OrganizerMarketDashboard>("/simulation/organizer/market-dashboard", { passkey });
}

export async function organizerStopMarket(passkey: string): Promise<OrganizerResetResult> {
  return apiPost<OrganizerResetResult>("/simulation/organizer/stop", { passkey });
}

export async function organizerFreshWipe(passkey: string): Promise<OrganizerResetResult> {
  return apiPost<OrganizerResetResult>("/simulation/organizer/fresh-wipe", {
    passkey,
  });
}

export async function fetchGlobalResetAt(): Promise<string | null> {
  const supa = getSupabaseLeaderboardConfig();
  if (!supa) return null;
  const table =
    process.env.NEXT_PUBLIC_SUPABASE_EVENT_CONTROL_TABLE ??
    getRuntimeConfig()?.supabaseEventControlTable ??
    "event_control";
  const endpoint = `${supa.url}/rest/v1/${table}?select=reset_at&id=eq.1`;
  try {
    const res = await fetch(endpoint, {
      cache: "no-store",
      headers: {
        apikey: supa.key,
        Authorization: `Bearer ${supa.key}`,
      },
    });
    if (!res.ok) return null;
    const rows = (await res.json()) as Array<{ reset_at?: string }>;
    return rows[0]?.reset_at ?? null;
  } catch {
    return null;
  }
}

export async function exportSnapshot(): Promise<Record<string, unknown>> {
  return apiPost<Record<string, unknown>>("/simulation/export-snapshot");
}

export type SessionBootstrap = {
  trader_id: number;
  trader_name?: string;
  trade_count?: number;
  wallet: Wallet;
  portfolio: Portfolio;
  stocks: SidebarStock[];
  sectors: SectorGroup[];
  simulation: Record<string, unknown>;
  released_news_count?: number;
  released_news?: Array<{
    id: number;
    title: string;
    description?: string;
    released_at?: string;
    brief_points?: string[];
  }>;
  leaderboard?: LeaderboardRow[];
  open_ipos?: IPO[];
  ipo_applications?: Array<{ id: number; ipo_id: number; status: string }>;
};

export type HealthResponse = {
  participant_event_mode?: boolean;
  pin_required?: boolean;
  local_instance_mode?: boolean;
  developer_mode?: boolean;
};

export async function fetchHealthConfig(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}

type Wallet = {
  available_cash: string;
  portfolio_value: string;
  total_pnl: string;
  return_pct: string;
  starting_capital?: string;
};

type Portfolio = {
  holdings: Array<{
    ticker: string | null;
    quantity: number;
    avg_cost?: string;
    market_price?: string;
    market_value?: string;
    unrealized_pnl?: string;
  }>;
  starting_capital?: string;
  realized_pnl?: string;
  cash_blocked_ipo?: string;
};

type SidebarStock = {
  id: number;
  ticker: string;
  company_name?: string;
  last_traded_price?: string;
  ltp?: string;
  percent_change?: string | null;
  is_open?: boolean;
};

type IPO = {
  id: number;
  company_name: string;
  ticker: string;
  issue_price: string;
  lot_size: number;
  maximum_lots_per_user: number;
};

export async function fetchSessionBootstrap(): Promise<SessionBootstrap> {
  return apiGet<SessionBootstrap>("/session/bootstrap");
}

export async function adminLogin(secret: string): Promise<{ access_token: string }> {
  const res = await apiPost<{ access_token: string }>("/auth/admin/login", { secret });
  if (typeof window !== "undefined") {
    window.localStorage.setItem("mse_admin_token", res.access_token);
  }
  return res;
}

export function getAdminAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("mse_admin_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function adminPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithTimeout(apiUrl(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAdminAuthHeaders(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function adminGet<T>(
  path: string,
  params?: Record<string, string | boolean | number>,
): Promise<T> {
  let url = apiUrl(path);
  if (params && Object.keys(params).length > 0) {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      qs.set(key, String(value));
    }
    url = `${url}?${qs.toString()}`;
  }
  const res = await fetchWithTimeout(url, {
    cache: "no-store",
    headers: getAdminAuthHeaders(),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

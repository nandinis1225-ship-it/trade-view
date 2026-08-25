/**
 * Participant-only API client — no Supabase, organizer, admin, or leaderboard code.
 * Used by the trading terminal so participant static exports stay lean.
 */
import type { SectorGroup } from "@/components/StockSidebar";
import { getRuntimeConfig } from "@/lib/runtimeConfig";

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

export type SessionBootstrap = {
  trader_id: number;
  trader_name?: string;
  trade_count?: number;
  wallet: {
    available_cash: string;
    portfolio_value: string;
    total_pnl: string;
    return_pct: string;
    starting_capital?: string;
  };
  portfolio: {
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
  stocks: Array<{
    id: number;
    ticker: string;
    company_name?: string;
    last_traded_price?: string;
    ltp?: string;
    percent_change?: string | null;
    is_open?: boolean;
  }>;
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
  open_ipos?: Array<{
    id: number;
    company_name: string;
    ticker: string;
    issue_price: string;
    lot_size: number;
    maximum_lots_per_user: number;
  }>;
  ipo_applications?: Array<{ id: number; ipo_id: number; status: string }>;
};

export type HealthResponse = {
  participant_event_mode?: boolean;
  pin_required?: boolean;
  local_instance_mode?: boolean;
};

export async function fetchHealthConfig(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/health");
}

export async function fetchSessionBootstrap(): Promise<SessionBootstrap> {
  return apiGet<SessionBootstrap>("/session/bootstrap");
}

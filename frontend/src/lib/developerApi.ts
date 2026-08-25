import { apiGet, apiPatch, apiPost } from "@/lib/api";

export type DevSimStatus = {
  status: string;
  elapsed: string;
  duration: string;
  elapsed_sec: number;
  current_phase: string;
  sim_speed_multiplier: number;
  current_event?: { headline: string; checkpoint_id?: number } | null;
  next_event?: { headline: string; checkpoint_id?: number } | null;
  seconds_to_next_event?: number | null;
  completed_checkpoint_count: number;
  total_checkpoint_count: number;
  checkpoints?: DevCheckpoint[];
};

export type DevCheckpoint = {
  checkpoint_id: number;
  timestamp: string;
  sim_offset_sec?: number;
  phase?: string;
  type: string;
  headline: string;
  status: string;
  payload?: Record<string, unknown>;
  sector_impacts?: Record<string, number>;
};

export type DevLogEntry = {
  id: number;
  sim_elapsed_sec: number;
  event_type: string;
  detail: Record<string, unknown>;
  created_at?: string;
};

export function isDeveloperMode(): boolean {
  if (process.env.NEXT_PUBLIC_DEVELOPER_MODE === "true") return true;
  if (typeof window !== "undefined") {
    const cfg = (window as unknown as { __TRADEVERSE_CONFIG__?: { developerMode?: boolean } })
      .__TRADEVERSE_CONFIG__;
    if (cfg?.developerMode === true) return true;
  }
  return false;
}

export async function devGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  let url = path.startsWith("/") ? path : `/${path}`;
  if (params && Object.keys(params).length > 0) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) qs.set(k, String(v));
    url = `${url}?${qs.toString()}`;
  }
  return apiGet<T>(`/developer${url}`);
}

export async function devPost<T>(path: string, body?: unknown): Promise<T> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return apiPost<T>(`/developer${normalized}`, body);
}

export async function devPatch<T>(path: string, body: unknown): Promise<T> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return apiPatch<T>(`/developer${normalized}`, body);
}

export async function fetchDevStatus(): Promise<DevSimStatus> {
  return devGet<DevSimStatus>("/simulation/status");
}

export async function devSimAction(
  action: "start" | "stop" | "resume" | "reset" | "restart",
): Promise<DevSimStatus> {
  return devPost<DevSimStatus>(`/simulation/${action}`);
}

export async function devSetSpeed(multiplier: number): Promise<unknown> {
  return devPatch("/simulation/speed", { sim_speed_multiplier: multiplier });
}

export async function devJumpCheckpoint(
  checkpointId: number,
  allowBackward = true,
): Promise<unknown> {
  return devPost("/timeline/jump", { checkpoint_id: checkpointId, allow_backward: allowBackward });
}

export async function devReleaseNextNews(): Promise<unknown> {
  return devPost("/news/release-next");
}

export async function fetchDevLogs(limit = 100): Promise<DevLogEntry[]> {
  return devGet<DevLogEntry[]>("/logs", { limit });
}

export async function fetchDevMarketState(): Promise<unknown> {
  return devGet("/market-state");
}

export async function fetchDevPortfolio(traderId: number): Promise<unknown> {
  return devGet(`/portfolio/${traderId}`);
}

export async function fetchDevAiState(): Promise<unknown> {
  return devGet("/ai/state");
}

export async function devAiTick(): Promise<unknown> {
  return devPost("/ai/tick");
}

export async function devAiSeed(): Promise<unknown> {
  return devPost("/ai/seed");
}

export async function fetchDevTraders(): Promise<Array<{ id: number; name: string }>> {
  return devGet("/traders");
}

export async function fetchDevIpos(): Promise<unknown[]> {
  return devGet("/ipos");
}

export async function fetchDevDissolution(): Promise<unknown[]> {
  return devGet("/dissolution/upcoming");
}

export async function devVerifyIdempotency(): Promise<unknown> {
  return devPost("/test/verify-idempotency");
}

export const SCENARIO_STEPS = [
  "Fresh simulation reset",
  "PIN unlock (participant rehearsal)",
  "Timeline startup",
  "News release",
  "Sector impact",
  "Stock movement",
  "AI tick",
  "BUY order",
  "SELL order",
  "P&L update",
  "IPO application",
  "IPO allocation",
  "IPO listing",
  "Company dissolution",
  "Recovery after close",
  "Final event completion",
] as const;

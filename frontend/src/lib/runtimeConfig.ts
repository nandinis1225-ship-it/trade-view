export type TradeverseRuntimeConfig = {
  apiUrl?: string;
  wsUrl?: string;
  apiPrefix?: string;
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  supabaseLeaderboardTable?: string;
  supabaseEventControlTable?: string;
  localInstance?: boolean;
  participantEventMode?: boolean;
  pinRequired?: boolean;
};

declare global {
  interface Window {
    __TRADEVERSE_CONFIG__?: TradeverseRuntimeConfig;
  }
}

export function getRuntimeConfig(): TradeverseRuntimeConfig | undefined {
  if (typeof window === "undefined") return undefined;
  return window.__TRADEVERSE_CONFIG__;
}

export function isAuthError(message: string): boolean {
  const m = message.toLowerCase();
  return m.includes("401") || m.includes("unauthor") || m.includes("invalid token");
}

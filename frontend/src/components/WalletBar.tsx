"use client";

import { fmtMoney, fmtPct, signClass } from "@/lib/marketFormat";

type Props = {
  cash?: string | null;
  portfolio?: string | null;
  pnl?: string | null;
  ret?: string | null;
  onWallet: () => void;
  showWallet: boolean;
  tradingEnabled?: boolean;
  elapsed?: string | null;
};

export function WalletBar({
  cash,
  portfolio,
  pnl,
  ret,
  onWallet,
  showWallet,
  tradingEnabled,
  elapsed,
}: Props) {
  return (
    <header
      className="sticky top-0 z-30 border-b border-[var(--line)] bg-[var(--panel)]/95 px-3 py-2.5 backdrop-blur sm:px-4"
      style={{
        backgroundImage:
          "linear-gradient(180deg, rgba(62, 207, 142, 0.06) 0%, transparent 100%)",
      }}
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 sm:gap-3">
        <div className="flex items-center gap-3">
          <span className="font-sans text-sm font-bold tracking-widest text-[var(--foreground)]">
            TRADEVERSE
          </span>
          {elapsed && (
            <span className="font-mono text-[10px] tabular-nums text-[var(--muted)]">{elapsed}</span>
          )}
          {typeof tradingEnabled === "boolean" && (
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                tradingEnabled
                  ? "bg-[var(--accent)]/15 text-[var(--accent)]"
                  : "bg-[var(--warn)]/15 text-[var(--warn)]"
              }`}
            >
              {tradingEnabled ? "Market open" : "Market closed"}
            </span>
          )}
        </div>
        <div className="flex flex-1 flex-wrap items-center justify-end gap-x-3 gap-y-1 text-[11px] sm:gap-x-4 sm:text-xs">
          <span className="whitespace-nowrap font-sans">
            <span className="text-[var(--muted)]">Cash </span>
            <span className="font-mono tabular-nums text-[var(--foreground)]">{fmtMoney(cash)}</span>
          </span>
          <span className="whitespace-nowrap font-sans">
            <span className="text-[var(--muted)]">Portfolio </span>
            <span className="font-mono tabular-nums text-[var(--foreground)]">
              {fmtMoney(portfolio)}
            </span>
          </span>
          <span className={`whitespace-nowrap font-sans ${signClass(pnl)}`}>
            <span className="text-[var(--muted)]">P&L </span>
            <span className="font-mono tabular-nums">{fmtMoney(pnl)}</span>
          </span>
          <span className={`whitespace-nowrap font-sans ${signClass(ret)}`}>
            <span className="text-[var(--muted)]">Return </span>
            <span className="font-mono tabular-nums">
              {ret != null ? fmtPct(ret) : "—"}
            </span>
          </span>
          <button
            type="button"
            onClick={onWallet}
            className={`rounded border px-2.5 py-1 font-sans text-[10px] uppercase tracking-wide transition-colors ${
              showWallet
                ? "border-[var(--accent)]/50 bg-[var(--accent)]/10 text-[var(--accent)]"
                : "border-[var(--line)] text-[var(--muted)] hover:bg-white/5 hover:text-[var(--foreground)]"
            }`}
          >
            {showWallet ? "Hide wallet" : "Wallet"}
          </button>
        </div>
      </div>
    </header>
  );
}

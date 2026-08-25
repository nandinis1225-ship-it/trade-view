"use client";

import { fmtMoney, signClass } from "@/lib/marketFormat";

type Props = {
  cash?: string | null;
  portfolio?: string | null;
  pnl?: string | null;
  elapsed?: string | null;
  duration?: string | null;
  onHoldings?: () => void;
  showHoldings?: boolean;
};

export function WalletBar({
  cash,
  portfolio,
  pnl,
  elapsed,
  duration,
  onHoldings,
  showHoldings,
}: Props) {
  const simTime =
    elapsed && duration ? `${elapsed} / ${duration}` : elapsed ?? null;

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-[var(--panel)]/95 px-3 py-2.5 backdrop-blur sm:px-4">
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="font-sans text-sm font-bold tracking-[0.25em] text-[var(--foreground)]">
            TRADEVERSE
          </span>
          {simTime && (
            <span className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]">
              Sim {simTime}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-xs sm:gap-x-6">
          <span className="whitespace-nowrap">
            <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Cash </span>
            <span className="font-mono tabular-nums">{fmtMoney(cash)}</span>
          </span>
          <span className="whitespace-nowrap">
            <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Portfolio </span>
            <span className="font-mono tabular-nums">{fmtMoney(portfolio)}</span>
          </span>
          <span className={`whitespace-nowrap ${signClass(pnl)}`}>
            <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">P&amp;L </span>
            <span className="font-mono tabular-nums">{fmtMoney(pnl)}</span>
          </span>
          {onHoldings && (
            <button
              type="button"
              onClick={onHoldings}
              className={`rounded border px-2.5 py-1 text-[10px] uppercase tracking-wide transition-colors ${
                showHoldings
                  ? "border-[var(--accent)]/50 bg-[var(--accent)]/10 text-[var(--accent)]"
                  : "border-[var(--line)] text-[var(--muted)] hover:text-[var(--foreground)]"
              }`}
            >
              Holdings
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

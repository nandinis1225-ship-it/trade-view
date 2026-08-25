"use client";

import { fmtMoney, fmtPct } from "@/lib/marketFormat";

export type EventResult = {
  participantName: string;
  startingCapital: string;
  finalCash: string;
  holdingsValue: string;
  finalPortfolioValue: string;
  pnl: string;
  returnPct: string;
  tradeCount: number;
};

type Props = {
  result: EventResult;
};

function downloadResult(result: EventResult) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `tradeverse-result-${result.participantName.replace(/\s+/g, "-").toLowerCase()}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function EventCompleteScreen({ result }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 p-4">
      <div className="w-full max-w-md rounded border border-[var(--line)] bg-[var(--panel)] p-6 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--accent)]">Event complete</p>
        <h2 className="mt-3 font-sans text-xl font-semibold">{result.participantName}</h2>
        <dl className="mt-6 space-y-3 text-left text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Starting capital</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.startingCapital)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Final cash</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.finalCash)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Holdings value</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.holdingsValue)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Final portfolio value</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.finalPortfolioValue)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">P&amp;L</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.pnl)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Return</dt>
            <dd className="font-mono tabular-nums">{fmtPct(result.returnPct)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Trade count</dt>
            <dd className="font-mono tabular-nums">{result.tradeCount}</dd>
          </div>
        </dl>
        <button
          type="button"
          className="mt-8 w-full rounded border border-[var(--accent)] py-2.5 text-sm text-[var(--accent)] hover:bg-[var(--accent)]/10"
          onClick={() => downloadResult(result)}
        >
          Export result
        </button>
      </div>
    </div>
  );
}

"use client";

import { fmtMoney, fmtPct, signClass } from "@/lib/marketFormat";

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

export function EventCompleteScreen({ result }: Props) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/95 p-4">
      <div className="w-full max-w-md rounded border border-[var(--line)] bg-[var(--panel)] p-8 text-center">
        <p className="text-xs uppercase tracking-[0.35em] text-[var(--accent)]">Event complete</p>
        <h2 className="mt-4 font-sans text-xl font-semibold">{result.participantName}</h2>

        <dl className="mt-8 space-y-4 text-left text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Final cash</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.finalCash)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Final portfolio</dt>
            <dd className="font-mono tabular-nums">{fmtMoney(result.finalPortfolioValue)}</dd>
          </div>
          <div className="flex justify-between gap-4 border-t border-[var(--line)] pt-4">
            <dt className="font-medium text-[var(--foreground)]">Final P&amp;L</dt>
            <dd className={`font-mono text-lg tabular-nums ${signClass(result.pnl)}`}>
              {fmtMoney(result.pnl)}
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-[var(--muted)]">Return</dt>
            <dd className={`font-mono tabular-nums ${signClass(result.returnPct)}`}>
              {fmtPct(result.returnPct)}
            </dd>
          </div>
        </dl>

        <p className="mt-8 text-xs text-[var(--muted)]">
          Trading is closed. Your result has been saved on this device.
        </p>
      </div>
    </div>
  );
}

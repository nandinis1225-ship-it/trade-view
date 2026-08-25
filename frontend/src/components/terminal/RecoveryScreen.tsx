"use client";

import { fmtMoney, fmtPct, signClass } from "@/lib/marketFormat";

type Props = {
  participantName: string;
  elapsed: string;
  duration: string;
  pnl: string;
  returnPct: string;
  pin: string;
  error: string | null;
  loading: boolean;
  onPinChange: (value: string) => void;
  onResume: () => void;
};

export function RecoveryScreen({
  participantName,
  elapsed,
  duration,
  pnl,
  returnPct,
  pin,
  error,
  loading,
  onPinChange,
  onResume,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4">
      <div className="w-full max-w-md rounded border border-[var(--line)] bg-[var(--panel)] px-6 py-8 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">Existing simulation</p>
        <h1 className="mt-4 font-sans text-2xl font-bold tracking-[0.2em]">TRADEVERSE</h1>

        <dl className="mt-8 space-y-4 text-left text-sm">
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Participant</dt>
            <dd className="mt-1 font-sans text-lg">{participantName}</dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Progress</dt>
            <dd className="mt-1 font-mono tabular-nums">
              {elapsed} / {duration}
            </dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Current P&amp;L</dt>
            <dd className={`mt-1 font-mono text-lg tabular-nums ${signClass(pnl)}`}>
              {fmtMoney(pnl)} ({fmtPct(returnPct)})
            </dd>
          </div>
        </dl>

        <p className="mt-8 text-xs uppercase tracking-[0.25em] text-[var(--muted)]">Event PIN</p>
        <input
          className="mt-3 w-full border-b border-[var(--line)] bg-transparent py-3 text-center font-mono text-2xl tracking-[0.5em] text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
          value={pin}
          onChange={(e) => onPinChange(e.target.value)}
          placeholder="····"
          maxLength={16}
          autoComplete="off"
          inputMode="numeric"
          onKeyDown={(e) => {
            if (e.key === "Enter") onResume();
          }}
        />

        <button
          type="button"
          className="mt-8 w-full rounded border border-[var(--accent)] py-3 font-sans text-sm font-medium uppercase tracking-[0.2em] text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/10 disabled:opacity-50"
          disabled={loading || !pin.trim()}
          onClick={onResume}
        >
          {loading ? "Resuming…" : "Resume"}
        </button>
        {error && <p className="mt-4 text-sm text-[#ef4444]">{error}</p>}
      </div>
    </div>
  );
}

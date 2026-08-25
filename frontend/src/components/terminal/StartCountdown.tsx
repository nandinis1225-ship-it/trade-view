"use client";

type Props = {
  value: number;
};

export function StartCountdown({ value }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/95">
      {value > 0 ? (
        <p className="font-mono text-8xl font-bold tabular-nums text-[var(--accent)]">{value}</p>
      ) : (
        <p className="font-sans text-2xl font-semibold uppercase tracking-[0.3em] text-[var(--accent)]">
          Simulation starts
        </p>
      )}
    </div>
  );
}

"use client";

type Props = {
  value: number;
};

export function StartCountdown({ value }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90">
      <p className="font-mono text-8xl font-bold tabular-nums text-[var(--accent)]">{value}</p>
    </div>
  );
}

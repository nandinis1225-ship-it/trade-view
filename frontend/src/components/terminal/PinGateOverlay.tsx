"use client";

type Props = {
  name: string;
  pin: string;
  error: string | null;
  loading: boolean;
  onNameChange: (value: string) => void;
  onPinChange: (value: string) => void;
  onSubmit: () => void;
};

export function PinGateOverlay({
  name,
  pin,
  error,
  loading,
  onNameChange,
  onPinChange,
  onSubmit,
}: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4">
      <div className="w-full max-w-sm text-center">
        <h1 className="font-sans text-3xl font-bold tracking-[0.35em] text-[var(--foreground)]">
          TRADEVERSE
        </h1>

        <p className="mt-10 text-xs uppercase tracking-[0.25em] text-[var(--muted)]">
          Participant name
        </p>
        <input
          className="mt-3 w-full rounded border border-[var(--line)] bg-[var(--background)] px-3 py-3 text-center font-sans text-base text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="Your name"
          maxLength={64}
          autoFocus
        />

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
            if (e.key === "Enter") onSubmit();
          }}
        />

        <button
          type="button"
          className="mt-10 w-full rounded border border-[var(--accent)] py-3 font-sans text-sm font-medium uppercase tracking-[0.2em] text-[var(--accent)] transition-colors hover:bg-[var(--accent)]/10 disabled:opacity-50"
          disabled={loading || !pin.trim() || !name.trim()}
          onClick={onSubmit}
        >
          {loading ? "Checking…" : "Enter"}
        </button>
        {error && <p className="mt-4 text-sm text-[#ef4444]">{error}</p>}
      </div>
    </div>
  );
}

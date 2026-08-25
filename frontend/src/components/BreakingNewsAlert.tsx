"use client";

import type { NewsItem } from "@/components/NewsPanel";

type Props = {
  news: NewsItem | null;
  onDismiss: () => void;
};

/** Single breaking-news alert for participants — one headline at a time. */
export function BreakingNewsAlert({ news, onDismiss }: Props) {
  if (!news) return null;

  return (
    <div className="fixed inset-x-4 top-20 z-40 mx-auto max-w-lg rounded border border-[#ef4444]/40 bg-[var(--panel)] p-4 shadow-xl md:inset-x-auto md:right-6 md:top-24">
      <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-[#ef4444]">
        Breaking news
      </p>
      <p className="mt-2 font-sans text-base font-medium">{news.title}</p>
      {news.description && <p className="mt-2 text-sm text-[var(--muted)]">{news.description}</p>}
      <button
        type="button"
        className="mt-3 font-sans text-xs text-[var(--muted)] underline hover:text-[var(--foreground)]"
        onClick={onDismiss}
      >
        Dismiss
      </button>
    </div>
  );
}

"use client";

import { useState } from "react";
import type { NewsItem } from "@/components/NewsPanel";

type Props = {
  news: NewsItem[];
};

function formatTime(releasedAt?: string) {
  if (!releasedAt) return "—";
  return new Date(releasedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function NewsFeedPanel({ news }: Props) {
  const [expandedId, setExpandedId] = useState<number | null>(news[0]?.id ?? null);

  return (
    <aside className="flex h-full min-h-[240px] flex-col border border-[var(--line)] bg-[var(--panel)]/40 lg:min-h-0">
      <p className="border-b border-[var(--line)] px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
        News
      </p>
      <div className="flex-1 overflow-y-auto p-3">
        {news.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No news released yet.</p>
        ) : (
          <ul className="space-y-3">
            {news.map((item) => {
              const open = expandedId === item.id;
              return (
                <li key={item.id} className="rounded border border-[var(--line)] bg-[var(--background)]/50">
                  <button
                    type="button"
                    className="w-full px-3 py-2 text-left hover:bg-white/[0.03]"
                    onClick={() => setExpandedId(open ? null : item.id)}
                  >
                    <p className="text-[10px] text-[var(--muted)]">{formatTime(item.released_at)}</p>
                    <p className="mt-1 text-sm font-medium leading-snug">{item.title}</p>
                  </button>
                  {open && item.description && (
                    <p className="border-t border-[var(--line)] px-3 py-2 text-xs leading-relaxed text-[var(--muted)]">
                      {item.description}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { fmtMoney, fmtPct, signClass } from "@/lib/marketFormat";

export type SidebarStock = {
  id: number;
  ticker: string;
  company_name: string;
  last_traded_price: string;
  percent_change: string | null;
  sector_name?: string | null;
  is_open?: boolean;
};

export type SectorStockRow = {
  stock_id: number;
  ticker: string;
  company_name: string;
  last_traded_price: string;
  percent_change: string;
};

export type SectorGroup = {
  sector_id: number;
  slug: string;
  name: string;
  stock_count: number;
  sector_change_pct: string;
  stocks: SectorStockRow[];
};

type Props = {
  sectors: SectorGroup[];
  dissolved?: SidebarStock[];
  selectedId: number | null;
  onSelect: (id: number) => void;
};

export function StockSidebar({ sectors, dissolved = [], selectedId, onSelect }: Props) {
  const [expandedSectors, setExpandedSectors] = useState<Set<string>>(
    () => new Set(sectors.map((s) => s.slug)),
  );

  useEffect(() => {
    setExpandedSectors((prev) => {
      const next = new Set(prev);
      for (const sector of sectors) next.add(sector.slug);
      return next;
    });
  }, [sectors]);

  function toggleSector(slug: string) {
    setExpandedSectors((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }

  const dissolvedBlock = useMemo(() => {
    if (!dissolved.length) return null;
    return (
      <div className="border-t border-[var(--line)] px-3 py-2">
        <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Dissolved</p>
        <ul>
          {dissolved.map((s) => (
            <li key={s.id} className="px-1 py-1 text-[10px] text-[var(--muted)]">
              {s.ticker} · not tradable
            </li>
          ))}
        </ul>
      </div>
    );
  }, [dissolved]);

  return (
    <aside className="flex h-full flex-col border border-[var(--line)] bg-[var(--panel)]/50">
      <p className="border-b border-[var(--line)] px-3 py-2 text-[10px] font-medium uppercase tracking-wider text-[var(--muted)]">
        Stocks
      </p>
      <div className="flex-1 overflow-y-auto">
        {sectors.map((sector) => {
          const isOpen = expandedSectors.has(sector.slug);
          const avg = sector.sector_change_pct;
          return (
            <div key={sector.slug} className="border-b border-[var(--line)]/50">
              <button
                type="button"
                onClick={() => toggleSector(sector.slug)}
                className="sticky top-0 z-10 flex w-full items-center justify-between bg-[var(--panel)]/95 px-3 py-2 text-left hover:bg-white/[0.04]"
              >
                <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--foreground)]">
                  {isOpen ? "▼" : "▶"} {sector.name}
                </span>
                <span className={`text-xs font-mono tabular-nums ${signClass(avg)}`}>
                  {fmtPct(avg)}
                </span>
              </button>
              {isOpen && (
                <ul>
                  {sector.stocks.map((s) => (
                    <li key={s.stock_id}>
                      <button
                        type="button"
                        onClick={() => onSelect(s.stock_id)}
                        className={`relative flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-white/[0.04] ${
                          selectedId === s.stock_id
                            ? "bg-[var(--accent)]/10 before:absolute before:left-0 before:top-1 before:bottom-1 before:w-0.5 before:bg-[var(--accent)]"
                            : ""
                        }`}
                      >
                        <span>
                          <span className="block font-mono font-medium">{s.ticker}</span>
                        <span className="block text-[10px] text-[var(--muted)] truncate max-w-[120px]">
                          {s.company_name}
                        </span>
                        </span>
                        <span className="text-right">
                          <span className="block tabular-nums">{fmtMoney(s.last_traded_price)}</span>
                          <span className={`block text-[10px] ${signClass(s.percent_change)}`}>
                            {fmtPct(s.percent_change)}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                  {!sector.stocks.length && (
                    <li className="px-3 py-2 text-[10px] text-[var(--muted)]">No active stocks</li>
                  )}
                </ul>
              )}
            </div>
          );
        })}
        {!sectors.length && <p className="p-3 text-xs text-[var(--muted)]">Loading stocks…</p>}
        {dissolvedBlock}
      </div>
    </aside>
  );
}

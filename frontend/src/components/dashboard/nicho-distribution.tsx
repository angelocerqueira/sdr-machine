"use client";

import Link from "next/link";
import { useState } from "react";
import { NICHO_LABEL, type NichoCanonico } from "@/lib/types";

export function NichoDistribution({
  data,
}: {
  data: Record<string, number>;
}) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(data)
    .map(([k, v]) => [k, v] as [string, number])
    .sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  const visible = expanded ? entries : entries.slice(0, 10);

  return (
    <div className="rounded-xl border border-border bg-surface p-6">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider font-[family-name:var(--font-mono)] mb-5">
        Distribuição por nicho
      </h3>
      {entries.length > 0 ? (
        <>
          <ul className="distribution-list">
            {visible.map(([k, count]) => {
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              const label = (NICHO_LABEL as Record<string, string>)[k] ?? k;
              return (
                <li key={k}>
                  <Link href={`/app/kanban?nicho_canonico=${k as NichoCanonico}`} className="distribution-row">
                    <span className="label">{label}</span>
                    <div className="bar">
                      <div className="fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="count">{count} ({pct}%)</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          {entries.length > 10 && (
            <button
              type="button"
              className="expand-btn"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Recolher" : `Ver todos (${entries.length})`}
            </button>
          )}
        </>
      ) : (
        <p className="text-text-muted text-xs">Nenhum nicho classificado ainda</p>
      )}
    </div>
  );
}

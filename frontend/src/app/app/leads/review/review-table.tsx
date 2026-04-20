"use client";

import { useEffect, useState } from "react";
import { getLeadsForReview, reclassifyLead, updateLead } from "@/lib/api";
import { NICHO_LABEL, type Lead, type NichoCanonico } from "@/lib/types";

export function ReviewTable() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const r = await getLeadsForReview({ per_page: 100 });
        if (!active) return;
        setLeads(r.items);
      } catch (err) {
        console.error("Failed to load review leads:", err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function setNicho(lead: Lead, nicho: NichoCanonico) {
    setBusyId(lead.id);
    try {
      const updated = await updateLead(lead.id, { nicho_canonico: nicho, nicho_source: "manual" });
      setLeads((ls) => ls.map((l) => (l.id === lead.id ? updated : l)));
    } catch (err) {
      console.error("Update nicho failed:", err);
    } finally {
      setBusyId(null);
    }
  }

  async function reclassify(lead: Lead) {
    setBusyId(lead.id);
    try {
      const updated = await reclassifyLead(lead.id);
      setLeads((ls) => ls.map((l) => (l.id === lead.id ? updated : l)));
    } catch (err) {
      console.error("Reclassify failed:", err);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-text-muted text-sm py-8 justify-center">
        <span className="w-4 h-4 border-2 border-text-muted border-t-accent rounded-full animate-spin" />
        Carregando...
      </div>
    );
  }

  if (!leads.length) {
    return (
      <div className="flex flex-col items-center py-16 text-center">
        <div className="w-12 h-12 rounded-full bg-surface-raised border border-border flex items-center justify-center mb-4">
          <svg className="w-5 h-5 text-text-muted" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 11l2 2 4-4" />
            <circle cx="10" cy="10" r="8" />
          </svg>
        </div>
        <p className="text-text-secondary text-sm">Nenhum lead pendente de revisão.</p>
        <p className="text-text-muted text-xs mt-1">Todos os nichos foram classificados com sucesso.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="border-b border-border">
            <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Nome</th>
            <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Nicho bruto</th>
            <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Sugestão atual</th>
            <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Confiança</th>
            <th className="text-left px-5 py-3 text-[10px] uppercase tracking-widest text-text-muted font-semibold font-[family-name:var(--font-mono)]">Ações</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((l) => {
            const busy = busyId === l.id;
            const confidence = Math.round((l.nicho_confidence ?? 0) * 100);
            return (
              <tr key={l.id} className="border-t border-border-subtle table-row-hover transition-default">
                <td className="px-5 py-3.5 text-text font-medium max-w-[200px] truncate">{l.nome}</td>
                <td className="px-5 py-3.5">
                  <code className="font-[family-name:var(--font-mono)] text-[12px] text-text-muted bg-surface-raised px-1.5 py-0.5 rounded">
                    {l.nicho || l.categoria || "—"}
                  </code>
                </td>
                <td className="px-5 py-3.5">
                  <span className="text-text">
                    {l.nicho_canonico
                      ? (NICHO_LABEL as Record<string, string>)[l.nicho_canonico] ?? l.nicho_canonico
                      : "—"}
                  </span>
                  {l.nicho_source && (
                    <span className="ml-2 font-[family-name:var(--font-mono)] text-[11px] text-text-muted bg-surface-raised px-1.5 py-0.5 rounded">
                      {l.nicho_source}
                    </span>
                  )}
                </td>
                <td className="px-5 py-3.5 font-[family-name:var(--font-mono)] text-[12px] text-text-muted">
                  {confidence}%
                </td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <select
                      value={l.nicho_canonico ?? "outros"}
                      disabled={busy}
                      onChange={(e) => setNicho(l, e.target.value as NichoCanonico)}
                      className="px-2 py-1.5 text-[12px] border border-border rounded bg-surface text-text cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-accent"
                    >
                      {Object.entries(NICHO_LABEL).map(([k, lbl]) => (
                        <option key={k} value={k}>{lbl}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => reclassify(l)}
                      className="px-3 py-1.5 text-[12px] border border-border rounded bg-surface text-text-muted hover:bg-surface-raised hover:text-text transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer whitespace-nowrap"
                    >
                      {busy ? (
                        <span className="flex items-center gap-1.5">
                          <span className="w-3 h-3 border border-text-muted border-t-accent rounded-full animate-spin" />
                          ...
                        </span>
                      ) : (
                        "Re-classificar"
                      )}
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

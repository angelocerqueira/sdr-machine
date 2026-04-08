"use client";

import { useEffect, useState, useCallback } from "react";
import { getLead, getLeadLpUrl, getLeadMessages, getLeadLandingPages, activateLandingPage, runGenerate, runOutreach, runEnrich } from "@/lib/api";
import type { Lead, OutreachMessage, LandingPage, ServiceLevels } from "@/lib/types";
import { ConfirmModal } from "./confirm-modal";
import { DiagnosticPanel } from "./diagnostic-panel";
import { ServiceLevelTabs } from "./service-level-tabs";

interface LeadSheetProps {
  leadId: number | null;
  onClose: () => void;
}

function ScoreBadge({ score }: { score: number | null }) {
  const value = score ?? 0;
  const colorClass =
    value >= 60
      ? "text-accent border-accent/20 bg-accent-subtle"
      : value >= 40
      ? "text-warning border-warning/20 bg-warning/5"
      : "text-text-muted border-border bg-surface-raised";

  return (
    <div className={`flex flex-col items-center rounded-xl border px-4 py-2.5 shrink-0 ${colorClass}`}>
      <span className={`stat-number text-2xl font-bold leading-none ${value >= 60 ? "text-accent" : value >= 40 ? "text-warning" : "text-text-muted"}`}>
        {score ?? "—"}
      </span>
      <span className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mt-0.5">
        Score
      </span>
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <p className="text-[10px] uppercase tracking-widest text-text-muted font-[family-name:var(--font-mono)] mb-1">
        {label}
      </p>
      <p className="text-[13px] text-text truncate">{value}</p>
    </div>
  );
}

function SheetSkeleton() {
  return (
    <div className="p-6 space-y-5">
      {/* Header skeleton */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="skeleton h-6 w-3/4" />
          <div className="skeleton h-4 w-1/2" />
        </div>
        <div className="skeleton h-16 w-16 rounded-xl shrink-0" />
      </div>
      {/* Info grid skeleton */}
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-surface p-3 space-y-1.5">
            <div className="skeleton h-3 w-1/2" />
            <div className="skeleton h-4 w-3/4" />
          </div>
        ))}
      </div>
      {/* Pills skeleton */}
      <div className="rounded-xl border border-border bg-surface p-4 space-y-2">
        <div className="skeleton h-3 w-1/3 mb-3" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="skeleton h-6 w-full rounded-full" />
        ))}
      </div>
    </div>
  );
}

export function LeadSheet({ leadId, onClose }: LeadSheetProps) {
  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<OutreachMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<"enrich" | "generate" | "regenerate" | "outreach" | "re-enrich" | "retry" | null>(null);
  const [landingPages, setLandingPages] = useState<LandingPage[]>([]);
  const [activatingLpId, setActivatingLpId] = useState<number | null>(null);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  // ESC key handler
  useEffect(() => {
    if (leadId === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [leadId, handleClose]);

  // Fetch lead data
  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setLead(null);
      setMessages([]);

      if (leadId === null) {
        setLoading(false);
        return;
      }

      try {
        const data = await getLead(leadId);
        if (!cancelled) {
          setLead(data);
          const [msgs, lps] = await Promise.all([
            getLeadMessages(leadId).catch(() => [] as OutreachMessage[]),
            getLeadLandingPages(leadId).catch(() => [] as LandingPage[]),
          ]);
          if (!cancelled) {
            setMessages(msgs);
            setLandingPages(lps);
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, [leadId]);

  if (leadId === null) return null;

  const score = lead?.opportunity_score ?? 0;

  return (
    <>
      {/* Backdrop */}
      <div
        className="sheet-backdrop fixed inset-0 z-40"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Sheet panel */}
      <div
        className="sheet-enter fixed top-0 right-0 z-50 h-full w-[480px] bg-surface border-l border-border flex flex-col shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Detalhes do lead"
      >
        {/* Sticky header */}
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 px-5 py-4 bg-surface border-b border-border-subtle">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <ScoreBadge score={lead?.opportunity_score ?? null} />
            <div className="min-w-0">
              {loading || !lead ? (
                <>
                  <div className="skeleton h-5 w-40 mb-1.5" />
                  <div className="skeleton h-3.5 w-28" />
                </>
              ) : (
                <>
                  <h2 className="text-[15px] font-semibold text-text truncate font-[family-name:var(--font-heading)]">
                    {lead.nome}
                  </h2>
                  <p className="text-[11px] text-text-secondary mt-0.5 truncate font-[family-name:var(--font-mono)]">
                    {lead.nicho ?? lead.categoria ?? "—"} · {lead.cidade ?? "—"}
                  </p>
                </>
              )}
            </div>
          </div>
          <button
            onClick={handleClose}
            className="shrink-0 flex items-center justify-center w-7 h-7 rounded-md text-text-muted hover:text-text hover:bg-surface-raised transition-colors"
            aria-label="Fechar"
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
              <path d="M3 3l10 10M13 3L3 13" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <SheetSkeleton />
          ) : lead ? (
            <div className="p-5 space-y-5">
              {/* Info grid (2 cols) */}
              <div className="grid grid-cols-2 gap-3">
                <InfoCell label="Telefone" value={lead.telefone ?? "—"} />
                <InfoCell
                  label="Rating"
                  value={
                    lead.rating
                      ? `${lead.rating} ★ (${lead.reviews_count} reviews)`
                      : "—"
                  }
                />
                <InfoCell label="Website" value={lead.website ?? "Sem site"} />
                <InfoCell label="Status" value={lead.status} />
              </div>

              {/* Opportunity reasons as green pills */}
              {lead.opportunity_reasons.length > 0 && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-3">
                    Gaps Detectados
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {lead.opportunity_reasons.map((reason, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-subtle border border-accent/20 text-[11px] text-accent font-[family-name:var(--font-mono)]"
                      >
                        <span className="w-1 h-1 rounded-full bg-accent shrink-0" />
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Service Level Tabs or legacy DiagnosticPanel */}
              {(lead.site_analysis as Record<string, unknown>)?.service_levels ? (
                <ServiceLevelTabs
                  serviceLevels={(lead.site_analysis as Record<string, unknown>).service_levels as ServiceLevels}
                />
              ) : (
                <DiagnosticPanel siteAnalysis={lead.site_analysis as Record<string, unknown>} />
              )}

              {/* Action buttons */}
              {(lead.status === "scraped" || lead.status === "enriched" || lead.status === "lp_generated" || lead.status === "outreach_ready" || lead.status === "disqualified" || lead.status.endsWith("_failed")) && (
                <div className="flex gap-2">
                  {lead.status === "scraped" && (
                    <button
                      onClick={() => setPendingAction("enrich")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-dim disabled:opacity-50 text-bg text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-bg/30 border-t-bg rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M8 1v14M1 8h14" />
                          <circle cx="8" cy="8" r="6" />
                        </svg>
                      )}
                      Enriquecer
                    </button>
                  )}
                  {lead.status === "enriched" && (
                    <button
                      onClick={() => setPendingAction("generate")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-dim disabled:opacity-50 text-bg text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-bg/30 border-t-bg rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M2 12l4-8 4 6 3-4 1 6" />
                        </svg>
                      )}
                      Gerar LP
                    </button>
                  )}
                  {lead.status === "lp_generated" && (
                    <button
                      onClick={() => setPendingAction("outreach")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-dim disabled:opacity-50 text-bg text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-bg/30 border-t-bg rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M2 3h12M2 8h8M2 13h10" />
                        </svg>
                      )}
                      Gerar Outreach
                    </button>
                  )}
                  {(lead.status === "lp_generated" || lead.status === "outreach_ready") && (
                    <button
                      onClick={() => setPendingAction("regenerate")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-raised hover:bg-surface-overlay border border-border disabled:opacity-50 text-text text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-border border-t-text rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M1 8a7 7 0 0113.4-2.8M15 8a7 7 0 01-13.4 2.8" />
                          <path d="M14.4 1v4.2h-4.2M1.6 15v-4.2h4.2" />
                        </svg>
                      )}
                      Regenerar LP
                    </button>
                  )}
                  {lead.status.endsWith("_failed") && (
                    <button
                      onClick={() => setPendingAction("retry")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-danger/20 hover:bg-danger/30 border border-danger/30 disabled:opacity-50 text-danger text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-danger/30 border-t-danger rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M1 8a7 7 0 0113.4-2.8M15 8a7 7 0 01-13.4 2.8" />
                          <path d="M14.4 1v4.2h-4.2M1.6 15v-4.2h4.2" />
                        </svg>
                      )}
                      Reprocessar
                    </button>
                  )}
                  {lead.status === "disqualified" && (
                    <button
                      onClick={() => setPendingAction("re-enrich")}
                      disabled={actionLoading}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-warning/20 hover:bg-warning/30 border border-warning/30 disabled:opacity-50 text-warning text-[13px] font-medium rounded-lg transition-default"
                    >
                      {actionLoading ? (
                        <span className="w-3.5 h-3.5 border-2 border-warning/30 border-t-warning rounded-full animate-spin" />
                      ) : (
                        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-4 h-4">
                          <path d="M1 8a7 7 0 0113.4-2.8M15 8a7 7 0 01-13.4 2.8" />
                          <path d="M14.4 1v4.2h-4.2M1.6 15v-4.2h4.2" />
                        </svg>
                      )}
                      Re-enriquecer
                    </button>
                  )}
                </div>
              )}

              {/* LP iframe preview */}
              {lead.lp_html && (
                <div className="rounded-xl border border-border bg-surface overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-border-subtle flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-danger/60" />
                      <span className="w-2.5 h-2.5 rounded-full bg-warning/60" />
                      <span className="w-2.5 h-2.5 rounded-full bg-accent/60" />
                    </div>
                    <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider font-[family-name:var(--font-mono)] flex-1">
                      Preview da LP
                    </h3>
                    <a
                      href={`/lp/${lead.public_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-[11px] text-accent hover:text-accent/80 font-[family-name:var(--font-mono)] transition-colors"
                    >
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="w-3 h-3">
                        <path d="M14 2H9m5 0v5m0-5L7 9" />
                        <path d="M13 9v4a1 1 0 01-1 1H3a1 1 0 01-1-1V4a1 1 0 011-1h4" />
                      </svg>
                      Tela cheia
                    </a>
                  </div>
                  <iframe
                    src={getLeadLpUrl(lead.id)}
                    className="w-full h-[400px] bg-white"
                    title={`LP Preview — ${lead.nome}`}
                  />
                </div>
              )}

              {/* LP version history */}
              {landingPages.length > 1 && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-3">
                    Versões da LP ({landingPages.length})
                  </h3>
                  <div className="space-y-2">
                    {landingPages.map((lp) => (
                      <div
                        key={lp.id}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg border transition-colors ${
                          lp.is_active
                            ? "border-accent/30 bg-accent-subtle"
                            : "border-border-subtle bg-surface-raised"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={`text-[12px] font-medium font-[family-name:var(--font-mono)] ${
                            lp.is_active ? "text-accent" : "text-text-muted"
                          }`}>
                            v{lp.version}
                          </span>
                          <span className="text-[11px] text-text-secondary">
                            {new Date(lp.created_at).toLocaleString("pt-BR", {
                              day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"
                            })}
                          </span>
                          {lp.is_active && (
                            <span className="text-[10px] text-accent font-[family-name:var(--font-mono)] uppercase">
                              ativa
                            </span>
                          )}
                        </div>
                        {!lp.is_active && (
                          <button
                            onClick={async () => {
                              setActivatingLpId(lp.id);
                              try {
                                await activateLandingPage(lead.id, lp.id);
                                const [updated, lps] = await Promise.all([
                                  getLead(lead.id),
                                  getLeadLandingPages(lead.id),
                                ]);
                                setLead(updated);
                                setLandingPages(lps);
                              } finally {
                                setActivatingLpId(null);
                              }
                            }}
                            disabled={activatingLpId === lp.id}
                            className="text-[11px] text-accent hover:text-accent/80 font-[family-name:var(--font-mono)] transition-colors disabled:opacity-50"
                          >
                            {activatingLpId === lp.id ? "..." : "Ativar"}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* WhatsApp messages list */}
              {messages.length > 0 && (
                <div className="rounded-xl border border-border bg-surface p-4">
                  <h3 className="text-[10px] uppercase tracking-widest font-[family-name:var(--font-mono)] text-text-muted mb-3">
                    Mensagens de Outreach
                  </h3>
                  <div className="space-y-3">
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className="rounded-lg border border-border-subtle bg-surface-raised p-3"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="status-pill bg-surface-overlay text-text-muted">
                            {msg.type.replace(/_/g, " ")}
                          </span>
                          {msg.sent_at && (
                            <span className="inline-flex items-center gap-1.5 text-[11px] text-accent font-[family-name:var(--font-mono)]">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                              Enviada
                            </span>
                          )}
                        </div>
                        <pre className="text-[13px] text-text-secondary whitespace-pre-wrap font-[family-name:var(--font-body)] leading-relaxed">
                          {msg.message_text}
                        </pre>
                        {msg.whatsapp_link && (
                          <a
                            href={msg.whatsapp_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 mt-2 text-[11px] text-accent hover:text-accent/80 font-[family-name:var(--font-mono)] transition-colors"
                          >
                            <svg viewBox="0 0 24 24" fill="currentColor" className="w-3 h-3">
                              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" />
                              <path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.612.616l4.573-1.449A11.944 11.944 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.37 0-4.567-.702-6.414-1.905l-.244-.157-3.176 1.005 1.04-3.1-.17-.254A9.953 9.953 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z" />
                            </svg>
                            Abrir WhatsApp
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Action confirmation modal */}
        <ConfirmModal
          open={pendingAction !== null}
          title={
            pendingAction === "enrich"
              ? "Enriquecer Lead?"
              : pendingAction === "generate"
              ? "Gerar Landing Page?"
              : pendingAction === "regenerate"
              ? "Regenerar Landing Page?"
              : pendingAction === "re-enrich"
              ? "Re-enriquecer Lead?"
              : pendingAction === "retry"
              ? "Reprocessar Lead?"
              : "Gerar Outreach?"
          }
          confirmLabel="Executar"
          onConfirm={async () => {
            if (!lead || !pendingAction) return;
            const action = pendingAction;
            setPendingAction(null);
            setActionLoading(true);
            try {
              if (action === "enrich" || action === "re-enrich") {
                await runEnrich({ lead_ids: [lead.id] });
              } else if (action === "generate" || action === "regenerate") {
                await runGenerate({ lead_ids: [lead.id] });
              } else if (action === "retry") {
                // Detect which stage failed and re-run it
                if (lead.status === "enrich_failed") {
                  await runEnrich({ lead_ids: [lead.id] });
                } else if (lead.status === "generate_failed") {
                  await runGenerate({ lead_ids: [lead.id] });
                } else if (lead.status === "outreach_failed") {
                  await runOutreach({ lead_ids: [lead.id] });
                }
              } else {
                await runOutreach({ lead_ids: [lead.id] });
              }
              // Refetch lead to get updated status
              const [updated, lps] = await Promise.all([
                getLead(lead.id),
                getLeadLandingPages(lead.id).catch(() => [] as LandingPage[]),
              ]);
              setLead(updated);
              setLandingPages(lps);
              if (action === "outreach") {
                const msgs = await getLeadMessages(lead.id).catch(() => [] as OutreachMessage[]);
                setMessages(msgs);
              }
            } catch {
              // Error handled silently — job may still be processing in background
            } finally {
              setActionLoading(false);
            }
          }}
          onCancel={() => setPendingAction(null)}
        >
          <p>
            {pendingAction === "enrich"
              ? `Enriquecer "${lead?.nome}" — análise de site, score de oportunidade e diagnóstico.`
              : pendingAction === "generate"
              ? `Gerar uma landing page personalizada para "${lead?.nome}". Usa a Claude API (~$0.01).`
              : pendingAction === "regenerate"
              ? `Gerar uma nova versão da landing page para "${lead?.nome}". A versão anterior será mantida no histórico. Usa a Claude API (~$0.01).`
              : pendingAction === "re-enrich"
              ? `Re-enriquecer "${lead?.nome}" com novo diagnóstico. O lead voltará para a fila de enriquecimento.`
              : pendingAction === "retry"
              ? `Reprocessar "${lead?.nome}" — tentar novamente o estágio que falhou (${lead?.status?.replace("_failed", "")}).`
              : `Gerar 3 mensagens de WhatsApp para "${lead?.nome}".`}
          </p>
        </ConfirmModal>

        {/* Footer: score color bar */}
        <div
          className={`h-0.5 w-full shrink-0 ${
            score >= 60
              ? "bg-accent"
              : score >= 40
              ? "bg-warning"
              : "bg-border"
          }`}
        />
      </div>
    </>
  );
}

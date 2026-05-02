"use client";

import { useMemo } from "react";
import { Icon } from "@/components/ui";

interface Props {
  counts: Record<string, number>;
  conversionRate: number;
  onExport: () => void;
  onToggleAdvancedFilters: () => void;
  advancedOpen: boolean;
  onEnrichScraped: () => void;
}

const STAGE_HINTS: Array<{ status: string; label: string; nextAction: string }> = [
  { status: "scraped", label: "scrapeados, esperando análise", nextAction: "enriquecer" },
  { status: "enriched", label: "enriquecidos, prontos pra LP", nextAction: "gerar LPs" },
  { status: "lp_generated", label: "com LP gerada", nextAction: "preparar mensagens" },
  { status: "outreach_ready", label: "prontos pra envio", nextAction: "disparar outreach" },
  { status: "outreach_sent", label: "com mensagem enviada", nextAction: "aguardar resposta" },
];

export function PipelinePageHeader({
  counts,
  conversionRate,
  onExport,
  onToggleAdvancedFilters,
  advancedOpen,
  onEnrichScraped,
}: Props) {
  const scrapedCount = counts.scraped ?? 0;

  const subtitle = useMemo(() => {
    const stage = STAGE_HINTS.find((s) => (counts[s.status] ?? 0) > 0);
    const conv = conversionRate.toFixed(2).replace(".", ",");
    if (!stage) {
      return (
        <>
          Pipeline vazio. Importe um CSV ou rode um scrape pra começar. Conversão atual:{" "}
          <span className="pl-header-em">{conv}%</span>.
        </>
      );
    }
    const count = counts[stage.status] ?? 0;
    return (
      <>
        <span className="pl-header-em">{count}</span> leads {stage.label}. Conversão atual:{" "}
        <span className="pl-header-em">{conv}%</span> · próximo passo: {stage.nextAction}.
      </>
    );
  }, [counts, conversionRate]);

  return (
    <header className="pl-header">
      <div className="pl-header-l">
        <div className="pl-header-eyebrow">SDR · Pipeline</div>
        <h1 className="pl-header-title">Pipeline</h1>
        <p className="pl-header-sub">{subtitle}</p>
      </div>

      <div className="pl-header-actions">
        <button
          type="button"
          onClick={onExport}
          className="rounded-md border border-border-strong bg-surface px-3 py-1.5 text-[13px] text-text-strong hover:border-text-muted hover:bg-surface-raised disabled:opacity-50 transition-default cursor-pointer inline-flex items-center gap-1.5"
        >
          <Icon name="doc" size={13} />
          Exportar
        </button>

        <button
          type="button"
          onClick={onToggleAdvancedFilters}
          aria-pressed={advancedOpen}
          className={`rounded-md border px-3 py-1.5 text-[13px] transition-default cursor-pointer inline-flex items-center gap-1.5 ${
            advancedOpen
              ? "border-text-strong bg-surface-raised text-text-strong"
              : "border-border-strong bg-surface text-text-strong hover:border-text-muted hover:bg-surface-raised"
          }`}
        >
          <Icon name="filter" size={13} />
          Filtros avançados
        </button>

        {scrapedCount > 0 && (
          <button
            type="button"
            onClick={onEnrichScraped}
            className="rounded-md bg-accent px-3 py-1.5 text-[13px] font-medium text-white hover:bg-accent-hover transition-default cursor-pointer inline-flex items-center gap-1.5"
          >
            <Icon name="sparkle" size={13} />
            Enriquecer{" "}
            <span className="font-mono tabular-nums">{scrapedCount}</span>
          </button>
        )}
      </div>
    </header>
  );
}

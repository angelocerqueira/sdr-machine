"use client";

import { useMemo } from "react";
import { Icon } from "@/components/ui";

interface Props {
  counts: Record<string, number>;
  conversionRate: number;
  onExport: () => void;
  onToggleAdvancedFilters: () => void;
  advancedOpen: boolean;
  onScrape: () => void;
  onCsvImport: () => void;
  onEnrichScraped: () => void;
  onGenerateLPs: () => void;
  onOutreachReady: () => void;
  onClassify: () => void;
}

const STAGE_HINTS: Array<{ status: string; label: string; nextAction: string; nextKey: NextActionKey }> = [
  { status: "scraped", label: "scrapeados, esperando análise", nextAction: "enriquecer", nextKey: "enrich" },
  { status: "enriched", label: "enriquecidos, prontos pra LP", nextAction: "gerar LPs", nextKey: "generate" },
  { status: "lp_generated", label: "com LP gerada", nextAction: "preparar mensagens", nextKey: "outreach" },
  { status: "outreach_ready", label: "prontos pra envio", nextAction: "disparar outreach", nextKey: "outreach" },
  { status: "outreach_sent", label: "com mensagem enviada", nextAction: "aguardar resposta", nextKey: null },
];

type NextActionKey = "enrich" | "generate" | "outreach" | null;

export function PipelinePageHeader({
  counts,
  conversionRate,
  onExport,
  onToggleAdvancedFilters,
  advancedOpen,
  onScrape,
  onCsvImport,
  onEnrichScraped,
  onGenerateLPs,
  onOutreachReady,
  onClassify,
}: Props) {
  const scrapedCount = counts.scraped ?? 0;
  const enrichedCount = counts.enriched ?? 0;
  const lpGeneratedCount = counts.lp_generated ?? 0;
  const totalLeads = Object.values(counts).reduce((a, b) => a + b, 0);

  const { subtitle, nextKey } = useMemo(() => {
    const stage = STAGE_HINTS.find((s) => (counts[s.status] ?? 0) > 0);
    const conv = conversionRate.toFixed(2).replace(".", ",");
    if (!stage) {
      return {
        nextKey: null as NextActionKey,
        subtitle: (
          <>
            Pipeline vazio. Importe um CSV ou rode um scrape pra começar. Conversão atual:{" "}
            <span className="pl-header-em">{conv}%</span>.
          </>
        ),
      };
    }
    const count = counts[stage.status] ?? 0;
    return {
      nextKey: stage.nextKey,
      subtitle: (
        <>
          <span className="pl-header-em">{count}</span> leads {stage.label}. Conversão atual:{" "}
          <span className="pl-header-em">{conv}%</span> · próximo passo: {stage.nextAction}.
        </>
      ),
    };
  }, [counts, conversionRate]);

  const stageBtnClass = (key: NextActionKey, isNext: boolean) => {
    if (isNext) {
      return "rounded-md bg-accent px-3 py-1.5 text-[13px] font-medium text-white hover:bg-accent-hover transition-default cursor-pointer inline-flex items-center gap-1.5";
    }
    return "rounded-md border border-border bg-surface px-3 py-1.5 text-[13px] text-text-muted hover:text-text hover:border-text-muted hover:bg-surface-raised transition-default cursor-pointer inline-flex items-center gap-1.5";
  };

  const ghostBtnClass =
    "rounded-md px-3 py-1.5 text-[13px] text-text-muted hover:text-text hover:bg-surface-raised transition-default cursor-pointer inline-flex items-center gap-1.5";

  const viewBtnClass =
    "rounded-md border border-border-strong bg-surface px-3 py-1.5 text-[13px] text-text-strong hover:border-text-muted hover:bg-surface-raised disabled:opacity-50 transition-default cursor-pointer inline-flex items-center gap-1.5";

  // Stage badges only render when there's count > 0 for the relevant status
  const showEnrich = scrapedCount > 0;
  const showGenerate = enrichedCount > 0;
  const showOutreach = lpGeneratedCount > 0;
  const showClassify = totalLeads > 0;

  return (
    <header className="pl-header">
      <div className="pl-header-l">
        <div className="pl-header-eyebrow">SDR · Pipeline</div>
        <h1 className="pl-header-title">Pipeline</h1>
        <p className="pl-header-sub">{subtitle}</p>
      </div>

      <div className="pl-header-actions">
        {/* Entrada de dados — sempre disponível */}
        <button type="button" onClick={onScrape} className={ghostBtnClass}>
          <Icon name="plus" size={13} />
          Scrape
        </button>
        <button type="button" onClick={onCsvImport} className={ghostBtnClass}>
          <Icon name="arrow-d" size={13} />
          CSV
        </button>

        {/* Stage actions contextuais */}
        {(showEnrich || showGenerate || showOutreach || showClassify) && (
          <span className="pl-header-divider" aria-hidden />
        )}

        {showEnrich && (
          <button
            type="button"
            onClick={onEnrichScraped}
            className={stageBtnClass("enrich", nextKey === "enrich")}
          >
            <Icon name="sparkle" size={13} />
            Enriquecer{" "}
            <span className="font-mono tabular-nums">{scrapedCount}</span>
          </button>
        )}

        {showGenerate && (
          <button
            type="button"
            onClick={onGenerateLPs}
            className={stageBtnClass("generate", nextKey === "generate")}
          >
            <Icon name="doc" size={13} />
            Gerar LPs{" "}
            <span className="font-mono tabular-nums">{enrichedCount}</span>
          </button>
        )}

        {showOutreach && (
          <button
            type="button"
            onClick={onOutreachReady}
            className={stageBtnClass("outreach", nextKey === "outreach")}
          >
            <Icon name="message" size={13} />
            Outreach{" "}
            <span className="font-mono tabular-nums">{lpGeneratedCount}</span>
          </button>
        )}

        {showClassify && (
          <button
            type="button"
            onClick={onClassify}
            className={stageBtnClass(null, false)}
          >
            <Icon name="target" size={13} />
            Classificar
          </button>
        )}

        {/* Ações de view — sempre presentes à direita */}
        <span className="pl-header-divider" aria-hidden />

        <button type="button" onClick={onExport} className={viewBtnClass}>
          <Icon name="doc" size={13} />
          Exportar
        </button>

        <button
          type="button"
          onClick={onToggleAdvancedFilters}
          aria-pressed={advancedOpen}
          className={
            advancedOpen
              ? viewBtnClass.replace("border-border-strong bg-surface", "border-text-strong bg-surface-raised")
              : viewBtnClass
          }
        >
          <Icon name="filter" size={13} />
          Filtros
        </button>
      </div>
    </header>
  );
}

"use client";

import { useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

interface Props {
  counts: Record<string, number>;
}

type StageTone = "muted" | "accent" | "warn" | "ok";

const FUNNEL_STEPS: Array<{
  id: string;
  label: string;
  hint: string;
  tone: StageTone;
}> = [
  { id: "scraped", label: "Scrapeado", hint: "rode enriquecer", tone: "muted" },
  { id: "enriched", label: "Analisado", hint: "leads em análise", tone: "accent" },
  { id: "lp_generated", label: "LP Gerada", hint: "LPs prontas", tone: "accent" },
  { id: "outreach_sent", label: "Msg Enviada", hint: "aguardando resposta", tone: "warn" },
  { id: "responded", label: "Respondeu", hint: "fechando negócio", tone: "ok" },
];

const PROGRESS_STATUSES = [
  "scraped",
  "enriched",
  "lp_generated",
  "outreach_ready",
  "outreach_sent",
  "responded",
  "in_call",
  "closed",
  "delivered",
];

function formatRate(rate: number): string {
  if (!Number.isFinite(rate)) return "—";
  if (rate >= 100) return "100%";
  if (rate >= 10) return `${rate.toFixed(0)}%`;
  return `${rate.toFixed(1).replace(".", ",")}%`;
}

export function PipelineFunnel({ counts }: Props) {
  const router = useRouter();
  const sp = useSearchParams();
  const activeStatus = sp.get("status") ?? "";

  const everEnteredPipeline = useMemo(
    () => PROGRESS_STATUSES.reduce((sum, s) => sum + (counts[s] ?? 0), 0),
    [counts],
  );

  const respondedRate = useMemo(() => {
    const responded = counts.responded ?? 0;
    return everEnteredPipeline > 0 ? (responded / everEnteredPipeline) * 100 : 0;
  }, [counts.responded, everEnteredPipeline]);

  const handleClick = (status: string) => {
    const next = new URLSearchParams(sp.toString());
    if (next.get("status") === status) {
      next.delete("status");
    } else {
      next.set("status", status);
    }
    router.replace(`?${next.toString()}`, { scroll: false });
  };

  return (
    <section className="pl-funnel">
      <div className="pl-funnel-head">
        <div className="pl-funnel-head-l">
          <span className="pl-funnel-head-label">Funil</span>
          <span className="pl-funnel-head-sep">·</span>
          <span className="pl-funnel-head-meta">5 estágios · clique pra filtrar</span>
        </div>
        <div className="pl-funnel-head-r">
          <span className="pl-funnel-conv-label">Conversão fim-a-fim</span>
          <span className="pl-funnel-conv-value">
            {formatRate(respondedRate)}
          </span>
        </div>
      </div>

      <div className="pl-funnel-row">
        {FUNNEL_STEPS.map((step, idx) => {
          const count = counts[step.id] ?? 0;
          const isActive = activeStatus === step.id;
          const isEmpty = count === 0;
          const pctOfTotal =
            everEnteredPipeline > 0 ? (count / everEnteredPipeline) * 100 : 0;
          const num = String(idx + 1).padStart(2, "0");

          const stepNode = (
            <button
              key={step.id}
              type="button"
              onClick={() => handleClick(step.id)}
              aria-pressed={isActive}
              aria-label={`Filtrar por ${step.label}: ${count} leads`}
              data-tone={step.tone}
              className={`pl-funnel-step${isActive ? " active" : ""}${
                isEmpty ? " empty" : ""
              }`}
            >
              <div className="pl-funnel-step-top">
                <span className="pl-funnel-step-num">{num}</span>
                <span className="pl-funnel-step-label">{step.label}</span>
              </div>
              <div className="pl-funnel-step-value">{count}</div>
              <div className="pl-funnel-step-bar" aria-hidden="true">
                <span style={{ width: `${pctOfTotal}%` }} />
              </div>
              <div className="pl-funnel-step-hint">{step.hint}</div>
            </button>
          );

          if (idx === FUNNEL_STEPS.length - 1) {
            return stepNode;
          }

          const nextCount = counts[FUNNEL_STEPS[idx + 1].id] ?? 0;
          const transitionRate =
            count > 0 ? (nextCount / count) * 100 : 0;

          return [
            stepNode,
            <div
              key={`${step.id}-arrow`}
              className="pl-funnel-arrow"
              aria-hidden="true"
            >
              <span className="pl-funnel-arrow-rate">
                {formatRate(transitionRate)}
              </span>
              <span>→</span>
            </div>,
          ];
        }).flat()}
      </div>
    </section>
  );
}

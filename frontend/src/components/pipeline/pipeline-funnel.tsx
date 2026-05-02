"use client";

import { useRouter, useSearchParams } from "next/navigation";

interface Props {
  counts: Record<string, number>;
}

const FUNNEL_STEPS = [
  { id: "scraped", label: "Scrapeado" },
  { id: "enriched", label: "Analisado" },
  { id: "lp_generated", label: "LP Gerada" },
  { id: "outreach_sent", label: "Msg Enviada" },
  { id: "responded", label: "Respondeu" },
] as const;

export function PipelineFunnel({ counts }: Props) {
  const router = useRouter();
  const sp = useSearchParams();
  const activeStatus = sp.get("status") ?? "";

  // Pipeline conversion: of leads that ever entered the pipeline (scraped is
  // the entry point), how many reached "respondeu". Counts are status
  // snapshots — leads that progressed past `scraped` aren't in the scraped
  // bucket anymore — so we approximate "ever entered" via the sum of every
  // status downstream of (and including) `scraped`. Excludes `disqualified`
  // and `failed` since those leads never had a real chance to convert.
  const PROGRESS_STATUSES = [
    "scraped", "enriched", "lp_generated", "outreach_ready",
    "outreach_sent", "responded", "in_call", "closed", "delivered",
  ];
  const everEnteredPipeline = PROGRESS_STATUSES.reduce(
    (sum, s) => sum + (counts[s] ?? 0),
    0,
  );
  const responded = counts.responded ?? 0;
  const respondedRate =
    everEnteredPipeline > 0 ? (responded / everEnteredPipeline) * 100 : 0;

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
    <div className="rounded-lg border border-border-subtle bg-surface px-4 py-3">
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="t-eyebrow">Funil</span>
        <span className="font-mono tabular-nums text-[12px] text-text-muted">
          conversão {respondedRate.toFixed(2)}%
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {FUNNEL_STEPS.map((step, idx) => {
          const count = counts[step.id] ?? 0;
          const isActive = activeStatus === step.id;
          return (
            <div key={step.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => handleClick(step.id)}
                aria-pressed={isActive}
                className={`flex flex-col items-start rounded-md px-3 py-1.5 transition-default cursor-pointer ${
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "bg-surface-raised text-text-secondary hover:text-text"
                }`}
              >
                <span className="font-mono tabular-nums text-[14px] font-medium">{count}</span>
                <span className="t-eyebrow">{step.label}</span>
              </button>
              {idx < FUNNEL_STEPS.length - 1 && (
                <span className="text-text-muted text-[10px] font-mono">→</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

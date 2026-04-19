import { Icon } from "./icon";

const STAGES = [
  { key: "scraped", label: "Capturado" },
  { key: "enriched", label: "Enriquecido" },
  { key: "lp_generated", label: "Diagnosticado" },
  { key: "outreach_ready", label: "Ativado" },
  { key: "outreach_sent", label: "Em outreach" },
] as const;

type StageKey = (typeof STAGES)[number]["key"];

interface PipeMiniProps {
  current: string;
  className?: string;
}

export function PipeMini({ current, className = "" }: PipeMiniProps) {
  const currentIdx = STAGES.findIndex(s => s.key === current);

  return (
    <div className={`flex items-center gap-0 ${className}`}>
      {STAGES.map((stage, i) => {
        const isPast = i < currentIdx;
        const isCurrent = i === currentIdx;
        const isFuture = i > currentIdx;

        return (
          <div key={stage.key} className="flex items-center">
            {i > 0 && (
              <div
                className="w-4 h-px mx-0.5"
                style={{ background: isPast || isCurrent ? "var(--accent)" : "var(--line-1)" }}
              />
            )}
            <div className="relative group">
              {isPast && (
                <div className="w-4 h-4 rounded-full bg-accent flex items-center justify-center">
                  <Icon name="check" size={10} className="text-white" />
                </div>
              )}
              {isCurrent && (
                <div className="w-4 h-4 rounded-full border-[3px] border-accent bg-bg" />
              )}
              {isFuture && (
                <div className="w-4 h-4 rounded-full border border-line-1 bg-bg" />
              )}
              <span className="absolute top-5 left-1/2 -translate-x-1/2 text-[9px] text-text-subtle whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                {stage.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

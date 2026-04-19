const STAGES = [
  { key: "scraped", label: "Capturado" },
  { key: "enriched", label: "Enriquecido" },
  { key: "lp_generated", label: "Diagnosticado" },
  { key: "outreach_ready", label: "Ativado" },
  { key: "outreach_sent", label: "Em outreach" },
] as const;

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

        return (
          <div key={stage.key} className="flex items-center">
            {i > 0 && (
              <div
                className="w-4 h-px mx-0.5"
                style={{ background: "var(--line-1)" }}
              />
            )}
            <div className="relative group">
              {isPast && (
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center"
                  style={{ background: "var(--text-strong)", color: "var(--bg)" }}
                >
                  <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                    <path d="M1.5 4l1.8 1.8L6.5 2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
              {isCurrent && (
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center"
                  style={{ border: "1.5px solid var(--text-strong)" }}
                >
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: "var(--text-strong)" }}
                  />
                </div>
              )}
              {!isPast && !isCurrent && (
                <div
                  className="w-4 h-4 rounded-full"
                  style={{ border: "1px solid var(--line-1)", background: "var(--bg)" }}
                />
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

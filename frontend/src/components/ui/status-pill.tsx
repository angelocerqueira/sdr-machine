interface StatusPillProps {
  status: string;
  className?: string;
}

const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  scraped:        { label: "Scrapeado",     classes: "text-ink-3 bg-surface-raised border-border" },
  enriched:       { label: "Analisado",     classes: "text-[oklch(0.56_0.11_230)] bg-[oklch(0.96_0.03_230)] border-transparent" },
  lp_generated:   { label: "LP Gerada",     classes: "text-accent-ink bg-accent-soft border-transparent" },
  outreach_ready: { label: "Outreach",      classes: "text-[oklch(0.52_0.13_300)] bg-[oklch(0.96_0.03_300)] border-transparent" },
  outreach_sent:  { label: "Msg Enviada",   classes: "text-warn bg-warn-soft border-transparent" },
  responded:      { label: "Respondeu",     classes: "text-ok bg-ok-soft border-transparent" },
  in_call:        { label: "Em conversa",   classes: "text-[oklch(0.54_0.14_200)] bg-[oklch(0.96_0.03_200)] border-transparent" },
  closed:         { label: "Fechado",       classes: "text-text-strong bg-surface-raised border-transparent" },
  delivered:      { label: "Entregue",      classes: "text-ink-0 bg-paper-3 border-transparent" },
  disqualified:   { label: "Descartado",    classes: "text-ink-4 bg-surface-raised border-border" },
  failed:         { label: "Falhou",        classes: "text-danger bg-danger-soft border-transparent" },
};

export function StatusPill({ status, className = "" }: StatusPillProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, classes: "text-ink-3 bg-surface-raised" };

  return (
    <span
      className={`inline-flex items-center gap-1.5 h-[22px] pl-1.5 pr-2.5 text-[11px] font-medium tracking-[0.01em] rounded-full font-mono border ${config.classes} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
      {config.label}
    </span>
  );
}

type LeadStatus =
  | "scraped" | "enriched" | "lp_generated"
  | "outreach_ready" | "outreach_sent" | "responded"
  | "in_call" | "closed" | "delivered"
  | "disqualified" | "failed";

interface StatusPillProps {
  status: string;
  className?: string;
}

const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  scraped:        { label: "Capturado",     classes: "text-ink-3 bg-surface-raised" },
  enriched:       { label: "Enriquecido",   classes: "text-[oklch(0.56_0.11_230)] bg-[oklch(0.96_0.03_230)]" },
  lp_generated:   { label: "LP Gerada",     classes: "text-accent-ink bg-accent-soft" },
  outreach_ready: { label: "Outreach",      classes: "text-[oklch(0.52_0.13_300)] bg-[oklch(0.96_0.03_300)]" },
  outreach_sent:  { label: "Enviado",       classes: "text-warn bg-warn-soft" },
  responded:      { label: "Respondeu",     classes: "text-ok bg-ok-soft" },
  in_call:        { label: "Em conversa",   classes: "text-[oklch(0.54_0.14_200)] bg-[oklch(0.96_0.03_200)]" },
  closed:         { label: "Fechado",       classes: "text-ok bg-ok-soft" },
  delivered:      { label: "Entregue",      classes: "text-ink-0 bg-paper-3" },
  disqualified:   { label: "Descartado",    classes: "text-ink-4 bg-surface-raised line-through" },
  failed:         { label: "Erro",          classes: "text-danger bg-danger-soft" },
};

export function StatusPill({ status, className = "" }: StatusPillProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, classes: "text-ink-3 bg-surface-raised" };

  return (
    <span
      className={`inline-flex items-center gap-1 h-[22px] pl-1.5 pr-2.5 text-[11px] font-medium tracking-[0.01em] rounded-full ${config.classes} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current shrink-0" />
      {config.label}
    </span>
  );
}

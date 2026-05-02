export type SignalTone = "danger" | "warn" | "ok" | "muted";

export interface Signal {
  key: string;
  label: string;
  tone: SignalTone;
}

const DIMENSION_PREFIX_RE = /^\[(ACESSIBILIDADE|LP_SITE|AUTOMACAO|MAPA_REPUTACAO)\]\s*/;

const TONE_RANK: Record<SignalTone, number> = { danger: 0, warn: 1, ok: 2, muted: 3 };

interface ToneRule {
  match: RegExp;
  label: string;
  tone: SignalTone;
}

const RULES: ToneRule[] = [
  { match: /sem website|sem site/i, label: "Sem site", tone: "danger" },
  { match: /site com problemas|connection_error|timeout|ssl_error|fora do ar/i, label: "Site offline", tone: "danger" },
  { match: /sem https|sem ssl/i, label: "Sem HTTPS", tone: "danger" },
  { match: /sem presença no google maps/i, label: "Fora do Maps", tone: "danger" },
  { match: /reviews mencionam problemas/i, label: "Reviews ruins", tone: "danger" },
  { match: /sem telefone válido/i, label: "Sem telefone", tone: "danger" },

  { match: /não é responsivo|não responsivo/i, label: "Não responsivo", tone: "warn" },
  { match: /sem link de whatsapp|sem whatsapp/i, label: "Sem WhatsApp", tone: "warn" },
  { match: /sem cta/i, label: "Sem CTA", tone: "warn" },
  { match: /pagespeed baixo/i, label: "Site lento", tone: "warn" },
  { match: /avaliação baixa/i, label: "Rating baixo", tone: "warn" },
  { match: /avaliação abaixo/i, label: "Rating abaixo", tone: "warn" },
  { match: /pouquíssimas avaliações|poucas avaliações/i, label: "Poucos reviews", tone: "warn" },
  { match: /tech stack defasado/i, label: "Stack defasada", tone: "warn" },
  { match: /email genérico|email não profissional/i, label: "Email genérico", tone: "warn" },
  { match: /telefone fixo válido/i, label: "Só fixo", tone: "warn" },
  { match: /presença digital fraca/i, label: "Digital fraca", tone: "warn" },

  { match: /sem chatbot/i, label: "Sem chatbot", tone: "muted" },
  { match: /sem analytics|sem google analytics/i, label: "Sem analytics", tone: "muted" },
  { match: /sem agendamento/i, label: "Sem agendamento", tone: "muted" },
  { match: /sem.*pagamento/i, label: "Sem pagamento", tone: "muted" },
  { match: /sem crm/i, label: "Sem CRM", tone: "muted" },
  { match: /conteúdo muito escasso/i, label: "Pouco conteúdo", tone: "muted" },
  { match: /template genérico/i, label: "Template", tone: "muted" },
  { match: /quase sem imagens/i, label: "Sem imagens", tone: "muted" },
  { match: /sem links para redes sociais/i, label: "Sem social", tone: "muted" },
  { match: /sem dados estruturados/i, label: "Sem schema", tone: "muted" },
  { match: /canais de contato fragmentados/i, label: "Canais fragmentados", tone: "muted" },
];

function stripPrefix(reason: string): string {
  return reason.replace(DIMENSION_PREFIX_RE, "").trim();
}

function classify(reason: string): { label: string; tone: SignalTone } | null {
  const cleaned = stripPrefix(reason);
  if (!cleaned) return null;
  for (const rule of RULES) {
    if (rule.match.test(cleaned)) {
      return { label: rule.label, tone: rule.tone };
    }
  }
  return null;
}

export function deriveSignals(reasons: string[] | null | undefined): Signal[] {
  if (!reasons?.length) return [];

  const seen = new Map<string, Signal>();
  for (const reason of reasons) {
    const hit = classify(reason);
    if (!hit) continue;
    const existing = seen.get(hit.label);
    if (!existing || TONE_RANK[hit.tone] < TONE_RANK[existing.tone]) {
      seen.set(hit.label, { key: hit.label, label: hit.label, tone: hit.tone });
    }
  }

  return Array.from(seen.values()).sort(
    (a, b) => TONE_RANK[a.tone] - TONE_RANK[b.tone],
  );
}

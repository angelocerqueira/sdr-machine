import type { TabConfig, TabAction } from "./lead-app-types";

// ──────────────── Score helpers ────────────────
export function scoreClass(s: number): "high" | "mid" | "low" {
  return s >= 60 ? "high" : s >= 40 ? "mid" : "low";
}

// ──────────────── Status labels ────────────────
export const STATUS_LABELS: Record<string, string> = {
  scraped: "Scrapeado",
  enriched: "Analisado",
  disqualified: "Desqualificado",
  failed: "Falhou",
  lp_generated: "LP Gerada",
  outreach_ready: "Msg Pronta",
  outreach_sent: "Msg Enviada",
  responded: "Respondeu",
  closed: "Fechado",
};

// ──────────────── Tabs (dynamic counts) ────────────────
export function buildTabs(counts: { reasons: number; lpVersions: number; messages: number }): TabConfig[] {
  return [
    { key: "diag", label: "Diagnóstico", count: counts.reasons || undefined },
    { key: "lp", label: "Landing Page", count: counts.lpVersions || undefined, suffix: "v" },
    { key: "msgs", label: "Mensagens", count: counts.messages || undefined },
    { key: "info", label: "Informações" },
  ];
}

export const TAB_ACTIONS: Record<string, TabAction> = {
  diag: { primary: "Re-enriquecer", secondary: "Exportar diagnóstico" },
  lp: { primary: "Regenerar LP", secondary: "Copiar link público" },
  msgs: { primary: "Gerar variação", secondary: "Exportar conversa" },
  info: { primary: null, secondary: "Editar" },
};

// ──────────────── Dimension labels ────────────────
export const DIM_LABEL: Record<string, string> = {
  lp: "Landing",
  automacao: "Automação",
  acessibilidade: "Acessib.",
  mapa: "Mapa",
};

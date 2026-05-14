export interface FunnelActionDM {
  acao: string;
  resultado_esperado: string;
  kpi: string;
}

export interface FunnelStageDM {
  diagnostico: string;
  acoes_top2: FunnelActionDM[];
}

export interface IAPotencialDM {
  score: number;
  oportunidades: string[];
  justificativa: string;
}

export interface DiagnosticoMarketing {
  resumo_executivo: string;
  momento_funil: "descoberta" | "atracao" | "consideracao" | "acao" | "apologia";
  potencial_ia_automacao: IAPotencialDM;
  prioridades_top3: string[];
  funil: Record<string, FunnelStageDM>;
}

export interface LeadAppItem {
  id: number;
  name: string;
  niche: string;
  city: string;
  score: number;
  status: string;
  phone: string;
}

import type { LeadProfile, NichoCanonico, NichoSource, PacoteSugerido, Prioridade } from "@/lib/types";

export interface LeadAppDetail {
  id: number;
  public_id: string;
  nome: string;
  telefone: string;
  website: string;
  endereco: string;
  cidade: string;
  nicho: string;
  categoria: string;
  rating: number;
  reviews_count: number;
  top_reviews: string[];
  status: string;
  opportunity_score: number;
  scores: { acessibilidade: number; lp: number; automacao: number; mapa: number };
  cnpj: string;
  razao_social: string;
  porte: string;
  cnae: string;
  email: string;
  socios: Array<{ nome: string }>;
  tech_stack: Array<{ name: string; category: string }>;
  opportunity_reasons: string[];
  sources: Array<{ provider: string; status: string; time: string; note: string }>;
  messages: Array<{
    id: number;
    type: string;
    sent_at: string | null;
    text: string;
    created_at?: string;
    needs_review?: boolean;
    copy_count?: number;
    click_count?: number;
    manual_rating?: number | null;
    variant_label?: string | null;
  }>;
  recommendation: {
    level: string;
    label: string;
  };
  service_levels: {
    lp?: { score: number; sinais: string[]; oportunidades: string[]; justificativa: string };
    automacao_basica?: { score: number; sinais: string[]; oportunidades: string[]; justificativa: string };
    mapa_automacoes?: { score: number; sinais: string[]; oportunidades: string[]; justificativa: string };
    vertical_os?: { score: number; sinais: string[]; oportunidades: string[]; justificativa: string };
    nivel_recomendado?: string;
    qualificado?: boolean;
    resumo_executivo?: string;
  } | null;
  diagnostico_marketing?: DiagnosticoMarketing;
  lp_versions: Array<{
    id: number;
    v: number;
    created: string;
    active?: boolean;
  }>;
  created_at: string;
  // Classification fields
  perfil_lead: LeadProfile | null;
  nicho_canonico: NichoCanonico | null;
  nicho_source: NichoSource | null;
  nicho_confidence: number | null;
  pacote_sugerido: PacoteSugerido | null;
  prioridade: Prioridade | null;
}

export interface LeadGroup {
  key: string;
  title: string;
  statuses: string[];
  items: LeadAppItem[];
}

export interface TabConfig {
  key: string;
  label: string;
  count?: number;
  suffix?: string;
}

export interface TabAction {
  primary: string | null;
  secondary: string | null;
}

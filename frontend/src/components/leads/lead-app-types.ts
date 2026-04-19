export interface LeadAppItem {
  id: number;
  name: string;
  niche: string;
  city: string;
  score: number;
  status: string;
  phone: string;
}

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
  gaps: Array<{ dim: string; text: string; weight: string }>;
  sources: Array<{ provider: string; status: string; time: string; note: string }>;
  messages: Array<{ id: number; type: string; sent_at: string | null; text: string }>;
  recommendation: {
    level: string;
    label: string;
    summary: string;
    price_low: number;
    price_high: number;
    delivery_weeks: number;
  };
  score_previous: number | null;
  checklist: Array<{
    id: string;
    dim: string;
    dim_label: string;
    title: string;
    weight: string;
    evidence: string;
    impact: string;
    impact_detail: string;
  }>;
  checklist_groups: Array<{
    key: string;
    title: string;
    hint: string;
    ids: string[];
  }>;
  lp_metrics: {
    visits: number;
    clicks_wa: number;
    ctr: number;
    period: string;
    delta_ctr: number;
    active_version: number;
    first_visit: string;
  };
  lp_versions: Array<{
    v: number;
    created: string;
    note: string;
    active?: boolean;
  }>;
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

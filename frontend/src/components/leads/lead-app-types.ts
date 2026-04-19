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
  messages: Array<{ id: number; type: string; sent_at: string | null; text: string; created_at?: string }>;
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
  lp_versions: Array<{
    id: number;
    v: number;
    created: string;
    active?: boolean;
  }>;
  created_at: string;
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

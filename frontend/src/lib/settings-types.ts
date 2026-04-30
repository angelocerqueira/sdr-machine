export type ProviderId =
  | "resend" | "telegram" | "apify" | "llm"
  | "hunter" | "apollo" | "langsmith";

export interface TestResult {
  ok: boolean;
  latency_ms: number;
  error: string | null;
}

export interface IntegrationSummary {
  provider: ProviderId;
  enabled: boolean;
  last_tested_at: string | null;
  last_test_result: TestResult | null;
  config: IntegrationConfigMasked;
}

export type IntegrationConfigMasked = Record<string, unknown> & {
  // Per provider, has_<field> + <field>_last4 for secrets
};

export interface WorkspaceProfile {
  business_name: string | null;
  your_name: string | null;
  your_email: string | null;
  your_whatsapp: string | null;
  your_website: string | null;
  legal_basis: string | null;
}

export interface WorkspaceTargeting {
  target_niches: string[];
  target_cities: string[];
  min_rating: number | null;
  max_results_per_search: number | null;
  opportunity_score_threshold: number | null;
  diagnostic_model?: string | null;
  skip_ai_diagnostic?: boolean | null;
  skip_social_scraping?: boolean | null;
  ai_potential_threshold?: number | null;
  disqualify_threshold?: number | null;
  skip_service_level_analysis?: boolean | null;
}

export const PROVIDER_META: Record<ProviderId, { label: string; description: string; docs?: string }> = {
  resend:    { label: "Resend",    description: "Email transacional para cadência de outreach",    docs: "https://resend.com/docs" },
  telegram:  { label: "Telegram",  description: "Alertas de cadência (respostas, falhas)",         docs: "https://core.telegram.org/bots/api" },
  apify:     { label: "Apify",     description: "Scraping de Google Maps",                          docs: "https://docs.apify.com" },
  llm:       { label: "LLM",       description: "Geração de landing pages, copy e diagnósticos",   docs: "" },
  hunter:    { label: "Hunter",    description: "Descoberta de email por domínio",                  docs: "https://hunter.io/api-documentation" },
  apollo:    { label: "Apollo",    description: "Enriquecimento de contato",                        docs: "https://apolloio.github.io/apollo-api-docs/" },
  langsmith: { label: "LangSmith", description: "Tracing de chains LLM",                            docs: "https://docs.smith.langchain.com" },
};

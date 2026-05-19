from datetime import date, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# === Leads ===

class LeadBase(BaseModel):
    nome: str
    telefone: str | None = None
    email: str | None = None
    website: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    nicho: str | None = None
    categoria: str | None = None
    rating: float | None = None
    reviews_count: int = 0
    google_maps_url: str | None = None
    top_reviews: list[str] = []
    cnpj: str | None = None
    razao_social: str | None = None
    porte: str | None = None
    cnae: str | None = None
    data_fundacao: date | None = None
    socios: list = []
    tratamento_formal: str | None = None


class LeadOut(LeadBase):
    id: int
    public_id: str
    status: str
    opportunity_score: int | None = None
    opportunity_reasons: list[str] = []
    score_acessibilidade: int = 0
    score_lp: int = 0
    score_automacao: int = 0
    score_mapa: int = 0
    nivel_recomendado: str | None = None
    site_analysis: dict = {}
    social_profiles: dict = {}
    tech_stack: list = []
    enrichment_sources: list = []
    lp_html: str | None = None
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime
    perfil_lead: str | None = None
    nicho_canonico: str | None = None
    nicho_source: str | None = None
    nicho_confidence: float | None = None
    pacote_sugerido: str | None = None
    prioridade: str | None = None
    has_instagram: bool | None = None
    classified_at: datetime | None = None

    model_config = {"from_attributes": True}


class LeadSummaryOut(LeadBase):
    """Lead without lp_html — used in list endpoints to avoid huge payloads."""
    id: int
    public_id: str
    status: str
    opportunity_score: int | None = None
    opportunity_reasons: list[str] = []
    score_acessibilidade: int = 0
    score_lp: int = 0
    score_automacao: int = 0
    score_mapa: int = 0
    nivel_recomendado: str | None = None
    tech_stack: list = []
    enrichment_sources: list = []
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime
    perfil_lead: str | None = None
    nicho_canonico: str | None = None
    pacote_sugerido: str | None = None
    prioridade: str | None = None
    has_instagram: bool | None = None

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    status: str | None = None
    nome: str | None = None
    telefone: str | None = None
    email: str | None = None
    website: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    nicho: str | None = None
    nicho_canonico: Literal[
        "dentista", "estetica", "salao_barbearia", "restaurante",
        "petshop_vet", "academia", "contabilidade", "imobiliaria",
        "loja_roupas", "auto_escola", "advocacia", "industria",
        "clinica_medica", "escola_curso", "outros",
    ] | None = None
    pacote_sugerido: Literal["essencial", "profissional", "premium", "skip"] | None = None
    prioridade: Literal["maxima", "alta", "media", "baixa", "pular"] | None = None


class ReclassifyRequest(BaseModel):
    force: bool = False  # default: preserve manual nicho (safest UX)


class ClassifyRequest(BaseModel):
    scope: Literal["unclassified", "all", "by_job", "by_status"] = "unclassified"
    scope_filter: dict | None = None
    force: bool = False


class LeadListOut(BaseModel):
    items: list[LeadSummaryOut]
    total: int
    page: int
    per_page: int


# === Jobs ===

class JobOut(BaseModel):
    id: int
    type: str
    status: str
    params: dict = {}
    result_summary: dict = {}
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListOut(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    per_page: int


# === Pipeline ===

class PipelineStatusOut(BaseModel):
    eligible_counts: dict[str, int]
    running_jobs: list[str]


class ScrapeRequest(BaseModel):
    nichos: list[str] = []
    cidades: list[str] = []
    max_results: int = 50
    fontes: list[str] = ["google_maps", "cnpj"]


class EnrichRequest(BaseModel):
    lead_ids: list[int] = []
    skip_providers: list[str] = []
    force_providers: list[str] = []


class GenerateRequest(BaseModel):
    lead_ids: list[int] = []
    max_count: int = 50


class OutreachRequest(BaseModel):
    lead_ids: list[int] = []


# === Dashboard ===

class DashboardStats(BaseModel):
    total_leads: int
    leads_by_status: dict[str, int]
    avg_score: float | None
    total_jobs: int
    conversion_rate: float | None
    profile_distribution: dict[str, int] = {}
    nicho_distribution: dict[str, int] = {}


# === Landing Pages ===

class LandingPageOut(BaseModel):
    id: int
    public_id: str
    lead_id: int
    version: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# === Outreach Messages ===

class OutreachMessageOut(BaseModel):
    id: int
    lead_id: int
    type: str
    message_text: str
    whatsapp_link: str | None = None
    sent_at: datetime | None = None
    response_received_at: datetime | None = None
    status: str
    validation_errors: list[str] | None = None
    cta_usado: str | None = None
    angulo_usado: str | None = None
    needs_review: bool = False
    created_at: datetime
    copy_count: int = 0
    click_count: int = 0
    manual_rating: int | None = None
    variant_label: str | None = None

    model_config = {"from_attributes": True}


# === Bulk Operations ===

class BulkLeadUpdate(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)
    data: LeadUpdate


class BulkLeadDelete(BaseModel):
    lead_ids: list[int] = Field(min_length=1, max_length=5000)


class BulkUpdateError(BaseModel):
    lead_id: int
    error: str


class BulkUpdateResult(BaseModel):
    updated: int
    errors: list[BulkUpdateError] = Field(default_factory=list)


class BulkDeleteResult(BaseModel):
    deleted: int
    errors: list[BulkUpdateError] = Field(default_factory=list)


# === Pipeline Preview ===

PipelineAction = Literal["enrich", "generate", "outreach", "classify"]
SkippedReason = Literal["disqualified"]


class PipelinePreviewRequest(BaseModel):
    action: PipelineAction
    lead_ids: list[int] = Field(min_length=1, max_length=5000)
    options: dict[str, Any] = Field(default_factory=dict)


class PipelinePreviewResponse(BaseModel):
    action: PipelineAction
    total_leads: int
    eligible: int
    skipped: int
    skipped_reasons: dict[SkippedReason, int] = Field(default_factory=dict)
    cost_estimate: dict | None = None
    quota_status: list[dict] | None = None
    warnings: list[str] = Field(default_factory=list)


# === Lead IDs ===

class LeadIdsResponse(BaseModel):
    ids: list[int] = Field(default_factory=list)
    total: int
    truncated: bool = False


# === Conversations / Inbox ===

class MessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    conversation_id: int
    direction: str  # "in" | "out"
    provider_message_id: str | None
    body: str | None
    media_url: str | None
    status: str
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    received_at: datetime | None
    error: str | None
    created_at: datetime


class ConversationListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    lead_id: int
    lead_nome: str | None
    lead_telefone: str | None
    lead_status: str | None
    provider: str
    phone: str
    last_message_at: datetime | None
    last_message_preview: str | None
    unread_count: int
    status: str


class ConversationOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    workspace_id: int
    lead_id: int
    # Denormalised from Lead for display (None when lead deleted)
    lead_nome: str | None = None
    lead_status: str | None = None
    provider: str
    provider_chat_id: str
    phone: str
    last_message_at: datetime | None
    unread_count: int
    status: str
    created_at: datetime
    messages: list[MessageOut]


class SendMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

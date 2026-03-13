from datetime import datetime
from pydantic import BaseModel


# === Leads ===

class LeadBase(BaseModel):
    nome: str
    telefone: str | None = None
    website: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    nicho: str | None = None
    categoria: str | None = None
    rating: float | None = None
    reviews_count: int = 0
    google_maps_url: str | None = None
    top_reviews: list[str] = []


class LeadOut(LeadBase):
    id: int
    status: str
    opportunity_score: int | None = None
    opportunity_reasons: list[str] = []
    site_analysis: dict = {}
    lp_html: str | None = None
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadSummaryOut(LeadBase):
    """Lead without lp_html — used in list endpoints to avoid huge payloads."""
    id: int
    status: str
    opportunity_score: int | None = None
    opportunity_reasons: list[str] = []
    job_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    status: str | None = None


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

class ScrapeRequest(BaseModel):
    nichos: list[str] = []
    cidades: list[str] = []
    max_results: int = 50


class EnrichRequest(BaseModel):
    lead_ids: list[int] = []


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


# === Outreach Messages ===

class OutreachMessageOut(BaseModel):
    id: int
    lead_id: int
    type: str
    message_text: str
    whatsapp_link: str | None = None
    sent_at: datetime | None = None
    response_received_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

"""Pydantic schemas leves pras tools MCP retornarem."""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class LeadSummary(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    nicho: Optional[str]
    cidade: Optional[str]
    status: str
    opportunity_score: Optional[int]
    has_email: bool
    has_website: bool

    @classmethod
    def from_lead(cls, lead) -> "LeadSummary":
        return cls(
            id=lead.id, nome=lead.nome or "(sem nome)",
            telefone=lead.telefone, nicho=lead.nicho, cidade=lead.cidade,
            status=lead.status, opportunity_score=lead.opportunity_score,
            has_email=bool(lead.email), has_website=bool(lead.website),
        )


class LeadListResult(BaseModel):
    items: List[LeadSummary]
    total: int
    page: int
    per_page: int


class LeadFull(BaseModel):
    id: int
    nome: str
    telefone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    endereco: Optional[str]
    nicho: Optional[str]
    cidade: Optional[str]
    categoria: Optional[str]
    rating: Optional[float]
    reviews_count: Optional[int]
    status: str
    opportunity_score: Optional[int]
    opportunity_reasons: Optional[List[str]]
    cnpj: Optional[str]
    razao_social: Optional[str]
    porte: Optional[str]
    tech_stack: Optional[List[Any]]
    enrichment_sources: Optional[List[Any]]
    perfil_lead: Optional[str]
    nicho_canonico: Optional[str]
    created_at: datetime
    updated_at: datetime
    responded_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: int
    lead_id: int
    lead_nome: Optional[str]
    phone: str
    provider: str
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    unread_count: int
    status: str


class MessageSummary(BaseModel):
    id: int
    direction: str
    body: Optional[str]
    sent_at: Optional[datetime]
    received_at: Optional[datetime]
    status: str


class ConversationFull(BaseModel):
    id: int
    lead_id: int
    phone: str
    provider: str
    unread_count: int
    status: str
    created_at: datetime
    messages: List[MessageSummary]


class JobSummary(BaseModel):
    id: int
    type: str
    status: str
    progress: Optional[float]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]


class JobFull(JobSummary):
    params: Optional[dict]
    result_summary: Optional[dict]


class DashboardStats(BaseModel):
    total_leads: int
    by_status: dict[str, int]
    avg_score: Optional[float]
    conversion_rate: Optional[float]
    leads_by_day: List[dict]


class LandingPageSummary(BaseModel):
    id: int
    lead_id: int
    version: int
    is_active: bool
    created_at: datetime


class WorkspaceProfileOut(BaseModel):
    business_name: Optional[str]
    your_name: Optional[str]
    your_email: Optional[str]
    your_whatsapp: Optional[str]
    your_website: Optional[str]
    legal_basis: Optional[str]


class WorkspaceTargetingOut(BaseModel):
    target_niches: List[str]
    target_cities: List[str]
    min_rating: Optional[float]
    max_results_per_search: Optional[int]
    opportunity_score_threshold: Optional[int]


class PendingActionOut(BaseModel):
    id: str
    action_type: str
    preview: dict
    created_at: datetime
    expires_at: datetime
    committed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

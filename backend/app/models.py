import secrets
import string
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Integer, String, Text, Numeric, Float,
    DateTime, Date, ForeignKey, Index, JSON, UniqueConstraint, func
)
from sqlalchemy.orm import relationship

_NANOID_ALPHABET = string.ascii_letters + string.digits + "-_"


def generate_nanoid(size: int = 16) -> str:
    return "".join(secrets.choice(_NANOID_ALPHABET) for _ in range(size))

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")
    params = Column(JSON, default=dict)
    result_summary = Column(JSON, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    leads = relationship("Lead", back_populates="job")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(16), unique=True, nullable=False, default=generate_nanoid)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(50))
    website = Column(String(500))
    endereco = Column(String(500))
    cidade = Column(String(100))
    nicho = Column(String(100))
    categoria = Column(String(100))
    rating = Column(Numeric(2, 1))
    reviews_count = Column(Integer, default=0)
    google_maps_url = Column(String(500))
    top_reviews = Column(JSON, default=list)
    status = Column(String(50), default="scraped")
    opportunity_score = Column(Integer)
    opportunity_reasons = Column(JSON, default=list)
    site_analysis = Column(JSON, default=dict)
    social_profiles = Column(JSON, default=dict)
    email = Column(String(255))
    cnpj = Column(String(18))
    razao_social = Column(String(255))
    porte = Column(String(50))
    cnae = Column(String(100))
    data_fundacao = Column(Date)
    socios = Column(JSON, default=list)
    tech_stack = Column(JSON, default=list)
    enrichment_sources = Column(JSON, default=list)
    score_acessibilidade = Column(Integer, default=0, server_default="0")
    score_lp = Column(Integer, default=0, server_default="0")
    score_automacao = Column(Integer, default=0, server_default="0")
    score_mapa = Column(Integer, default=0, server_default="0")
    nivel_recomendado = Column(String(20), nullable=True)
    # Classification fields (see classifier.py / classifier_enums.py)
    perfil_lead = Column(String(30), nullable=True)
    nicho_canonico = Column(String(30), nullable=True)
    nicho_source = Column(String(30), nullable=True)
    nicho_confidence = Column(Float, nullable=True)
    pacote_sugerido = Column(String(30), nullable=True)
    prioridade = Column(String(20), nullable=True)
    classification_hash = Column(String(32), nullable=True)
    classified_at = Column(DateTime, nullable=True)
    has_instagram = Column(Boolean, nullable=True)
    parent_lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    nome_limpo = Column(String(255), nullable=True)
    place_id = Column(String(100), nullable=True)
    lp_html = Column(Text)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="leads")
    outreach_messages = relationship("OutreachMessage", back_populates="lead", cascade="all, delete-orphan")
    landing_pages = relationship("LandingPage", back_populates="lead", cascade="all, delete-orphan", order_by="LandingPage.version.desc()")

    __table_args__ = (
        Index("idx_leads_status", "status"),
        Index("idx_leads_nicho", "nicho"),
        Index("idx_leads_cidade", "cidade"),
        Index("idx_leads_score", "opportunity_score"),
        Index("idx_leads_email", "email"),
        Index("idx_leads_cnpj", "cnpj"),
        Index("idx_leads_perfil_lead", "perfil_lead"),
        Index("idx_leads_nicho_canonico", "nicho_canonico"),
        Index("idx_leads_pacote_sugerido", "pacote_sugerido"),
        Index("idx_leads_prioridade", "prioridade"),
        Index("idx_leads_parent_lead_id", "parent_lead_id"),
        Index("idx_leads_place_id", "place_id"),
    )


class LandingPage(Base):
    __tablename__ = "landing_pages"

    id = Column(Integer, primary_key=True)
    public_id = Column(String(16), unique=True, nullable=False, default=generate_nanoid)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    html = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())

    lead = relationship("Lead", back_populates="landing_pages")

    __table_args__ = (
        Index("idx_landing_pages_lead_id", "lead_id"),
        UniqueConstraint("lead_id", "version", name="uq_landing_pages_lead_version"),
    )


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    whatsapp_link = Column(Text)
    sent_at = Column(DateTime)
    response_received_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    lead = relationship("Lead", back_populates="outreach_messages")

    __table_args__ = (
        Index("idx_outreach_messages_lead_id", "lead_id"),
    )


class IntegrationSettings(Base):
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False, default=1, server_default="1")
    provider = Column(String(32), nullable=False)
    config = Column(JSON, nullable=False, default=dict, server_default="{}")
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    last_tested_at = Column(DateTime, nullable=True)
    last_test_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_integration_workspace_provider"),
        Index("idx_integration_settings_workspace", "workspace_id"),
    )


class WorkspaceProfile(Base):
    __tablename__ = "workspace_profile"

    workspace_id = Column(Integer, primary_key=True, default=1, server_default="1")
    business_name = Column(String(255), nullable=True)
    your_name = Column(String(255), nullable=True)
    your_email = Column(String(255), nullable=True)
    your_whatsapp = Column(String(50), nullable=True)
    your_website = Column(String(500), nullable=True)
    legal_basis = Column(String(64), nullable=True, default="legitimo_interesse_b2b",
                         server_default="legitimo_interesse_b2b")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkspaceTargeting(Base):
    __tablename__ = "workspace_targeting"

    workspace_id = Column(Integer, primary_key=True, default=1, server_default="1")
    target_niches = Column(JSON, nullable=True, default=list, server_default="[]")
    target_cities = Column(JSON, nullable=True, default=list, server_default="[]")
    min_rating = Column(Float, nullable=True)
    max_results_per_search = Column(Integer, nullable=True)
    opportunity_score_threshold = Column(Integer, nullable=True)
    diagnostic_model = Column(String(64), nullable=True)
    skip_ai_diagnostic = Column(Boolean, nullable=True)
    skip_social_scraping = Column(Boolean, nullable=True)
    ai_potential_threshold = Column(Integer, nullable=True)
    disqualify_threshold = Column(Integer, nullable=True)
    skip_service_level_analysis = Column(Boolean, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

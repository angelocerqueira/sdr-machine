from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Numeric,
    DateTime, ForeignKey, Index, JSON, func
)
from sqlalchemy.orm import relationship

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
    lp_html = Column(Text)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="leads")
    outreach_messages = relationship("OutreachMessage", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_leads_status", "status"),
        Index("idx_leads_nicho", "nicho"),
        Index("idx_leads_cidade", "cidade"),
        Index("idx_leads_score", "opportunity_score"),
    )


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)
    message_text = Column(Text, nullable=False)
    whatsapp_link = Column(String(500))
    sent_at = Column(DateTime)
    response_received_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())

    lead = relationship("Lead", back_populates="outreach_messages")

    __table_args__ = (
        Index("idx_outreach_messages_lead_id", "lead_id"),
    )

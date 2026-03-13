from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead
from app.schemas import LeadListOut, LeadOut, LeadSummaryOut, LeadUpdate, OutreachMessageOut

router = APIRouter(prefix="/api/leads", tags=["leads"])

VALID_STATUSES = {
    "scraped",
    "enriched",
    "lp_generated",
    "outreach_ready",
    "outreach_sent",
    "responded",
    "in_call",
    "closed",
    "delivered",
    "scrape_failed",
    "enrichment_failed",
    "generation_failed",
    "outreach_failed",
}


@router.get("", response_model=LeadListOut)
def list_leads(
    status: str | None = None,
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)
    if nicho:
        query = query.filter(Lead.nicho == nicho)
    if cidade:
        query = query.filter(Lead.cidade == cidade)
    if score_min is not None:
        query = query.filter(Lead.opportunity_score >= score_min)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return LeadListOut(
        items=[LeadSummaryOut.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/{lead_id}/lp")
def get_lead_lp(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.lp_html:
        raise HTTPException(status_code=404, detail="Landing page not generated yet")
    return Response(content=lead.lp_html, media_type="text/html")


@router.get("/{lead_id}/messages", response_model=list[OutreachMessageOut])
def get_lead_messages(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.outreach_messages


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if payload.status is not None:
        if payload.status not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{payload.status}'. Must be one of: {sorted(VALID_STATUSES)}",
            )
        lead.status = payload.status

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()

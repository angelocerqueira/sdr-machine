from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, LandingPage, Lead
from app.schemas import (
    BulkDeleteResult,
    BulkLeadDelete,
    BulkLeadUpdate,
    BulkUpdateError,
    BulkUpdateResult,
    JobOut,
    LandingPageOut,
    LeadIdsResponse,
    LeadListOut,
    LeadOut,
    LeadSummaryOut,
    LeadUpdate,
    OutreachMessageOut,
    ReclassifyRequest,
)

router = APIRouter(prefix="/api/leads", tags=["leads"])

ORDER_MAP = {
    "score_desc": Lead.opportunity_score.desc().nulls_last(),
    "score_asc": Lead.opportunity_score.asc().nulls_last(),
    "name_asc": Lead.nome.asc(),
    "created_desc": Lead.created_at.desc(),
    "updated_desc": Lead.updated_at.desc(),
}

VALID_STATUSES = {
    "scraped",
    "enriched",
    "disqualified",
    "lp_generated",
    "outreach_ready",
    "outreach_sent",
    "responded",
    "in_call",
    "closed",
    "delivered",
    "scrape_failed",
    "enrich_failed",
    "generate_failed",
    "outreach_failed",
}


def _apply_lead_filters(
    query,
    *,
    status: str | None = None,
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    has_telefone: bool | None = None,
    has_email: bool | None = None,
    search: str | None = None,
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
):
    """Apply common filters to a Lead query. Returns the filtered query."""
    if status:
        if status == "failed":
            query = query.filter(Lead.status.like("%_failed"))
        else:
            query = query.filter(Lead.status == status)
    if nicho:
        query = query.filter(Lead.nicho == nicho)
    if cidade:
        query = query.filter(Lead.cidade == cidade)
    if score_min is not None:
        query = query.filter(Lead.opportunity_score >= score_min)
    if score_max is not None:
        query = query.filter(Lead.opportunity_score <= score_max)
    if has_telefone is True:
        query = query.filter(Lead.telefone.isnot(None))
    elif has_telefone is False:
        query = query.filter(Lead.telefone.is_(None))
    if has_email is True:
        query = query.filter(Lead.email.isnot(None))
    elif has_email is False:
        query = query.filter(Lead.email.is_(None))
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Lead.nome.ilike(term),
            Lead.telefone.ilike(term),
            Lead.nicho.ilike(term),
            Lead.cidade.ilike(term),
            Lead.email.ilike(term),
            Lead.razao_social.ilike(term),
        ))
    if perfil_lead:
        query = query.filter(Lead.perfil_lead == perfil_lead)
    if nicho_canonico:
        query = query.filter(Lead.nicho_canonico == nicho_canonico)
    return query


@router.get("/filters")
def lead_filters(db: Session = Depends(get_db)):
    """Return distinct nichos and cidades for dynamic filter dropdowns."""
    nichos = [r[0] for r in db.query(Lead.nicho).filter(Lead.nicho.isnot(None)).distinct().order_by(Lead.nicho).all()]
    cidades = [r[0] for r in db.query(Lead.cidade).filter(Lead.cidade.isnot(None)).distinct().order_by(Lead.cidade).all()]
    return {"nichos": nichos, "cidades": cidades}


@router.get("/counts")
def lead_counts(
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    has_telefone: bool | None = None,
    has_email: bool | None = None,
    search: str | None = None,
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
    db: Session = Depends(get_db),
):
    """Return lead counts grouped by status. Used by Kanban column headers."""
    query = db.query(Lead.status, func.count(Lead.id))
    query = _apply_lead_filters(
        query,
        nicho=nicho,
        cidade=cidade,
        score_min=score_min,
        score_max=score_max,
        has_telefone=has_telefone,
        has_email=has_email,
        search=search,
        perfil_lead=perfil_lead,
        nicho_canonico=nicho_canonico,
    )

    rows = query.group_by(Lead.status).all()
    result: dict[str, int] = {}
    for status, count in rows:
        if status and status.endswith("_failed"):
            result["failed"] = result.get("failed", 0) + count
        else:
            result[status] = count
    return result


@router.get("/review", response_model=LeadListOut)
def list_leads_for_review(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return leads that need manual review: nicho=outros, nicho_source=failed, or low confidence."""
    from sqlalchemy import case as sa_case
    query = db.query(Lead).filter(
        or_(
            Lead.nicho_canonico == "outros",
            Lead.nicho_source == "failed",
            Lead.nicho_confidence < 0.5,
        )
    )
    total = query.count()
    items = query.order_by(Lead.id).offset((page - 1) * per_page).limit(per_page).all()
    return LeadListOut(
        items=[LeadSummaryOut.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/ids", response_model=LeadIdsResponse)
def list_lead_ids(
    status: str | None = None,
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    has_telefone: bool | None = None,
    has_email: bool | None = None,
    search: str | None = None,
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
    db: Session = Depends(get_db),
):
    """Return up to 5000 lead IDs matching the filters. Used by frontend
    bulk-selection in 'select all matching filter' mode to materialize the ID set."""
    query = _apply_lead_filters(
        db.query(Lead.id),
        status=status,
        nicho=nicho,
        cidade=cidade,
        score_min=score_min,
        score_max=score_max,
        has_telefone=has_telefone,
        has_email=has_email,
        search=search,
        perfil_lead=perfil_lead,
        nicho_canonico=nicho_canonico,
    )
    total = query.count()
    rows = query.limit(5001).all()
    truncated = len(rows) > 5000
    ids = [r[0] for r in rows[:5000]]
    return LeadIdsResponse(ids=ids, total=total, truncated=truncated)


@router.get("", response_model=LeadListOut)
def list_leads(
    status: str | None = None,
    nicho: str | None = None,
    cidade: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    has_telefone: bool | None = None,
    has_email: bool | None = None,
    search: str | None = None,
    perfil_lead: str | None = None,
    nicho_canonico: str | None = None,
    order_by: str = Query("score_desc", pattern="^(score_desc|score_asc|name_asc|created_desc|updated_desc|prioridade)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = _apply_lead_filters(
        db.query(Lead),
        status=status,
        nicho=nicho,
        cidade=cidade,
        score_min=score_min,
        score_max=score_max,
        has_telefone=has_telefone,
        has_email=has_email,
        search=search,
        perfil_lead=perfil_lead,
        nicho_canonico=nicho_canonico,
    )

    if order_by == "prioridade":
        from sqlalchemy import case as sa_case
        prio_order = sa_case(
            (Lead.prioridade == "maxima", 1),
            (Lead.prioridade == "alta", 2),
            (Lead.prioridade == "media", 3),
            (Lead.prioridade == "baixa", 4),
            (Lead.prioridade == "pular", 5),
            else_=6,
        )
        query = query.order_by(prio_order, Lead.opportunity_score.desc())
    else:
        query = query.order_by(ORDER_MAP[order_by])

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


@router.get("/p/{public_id}/lp")
def get_lead_lp_by_public_id(public_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.public_id == public_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.lp_html:
        raise HTTPException(status_code=404, detail="Landing page not generated yet")
    return Response(content=lead.lp_html, media_type="text/html")


@router.get("/p/{public_id}", response_model=LeadOut)
def get_lead_by_public_id(public_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.public_id == public_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/{lead_id}/landing-pages", response_model=list[LandingPageOut])
def get_lead_landing_pages(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.landing_pages


@router.post("/{lead_id}/landing-pages/{lp_id}/activate", response_model=LandingPageOut)
def activate_landing_page(lead_id: int, lp_id: int, db: Session = Depends(get_db)):
    lp = db.query(LandingPage).filter(
        LandingPage.id == lp_id, LandingPage.lead_id == lead_id
    ).first()
    if not lp:
        raise HTTPException(status_code=404, detail="Landing page not found")
    # Deactivate all others
    db.query(LandingPage).filter(
        LandingPage.lead_id == lead_id, LandingPage.id != lp_id
    ).update({"is_active": False})
    lp.is_active = True
    # Sync lp_html on lead for backwards compatibility
    lead = db.get(Lead, lead_id)
    lead.lp_html = lp.html
    db.commit()
    db.refresh(lp)
    return lp


@router.get("/{lead_id}/messages", response_model=list[OutreachMessageOut])
def get_lead_messages(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.outreach_messages


@router.get("/{lead_id}/jobs", response_model=list[JobOut])
def get_lead_jobs(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    result = []
    for job in jobs:
        lead_ids = job.params.get("lead_ids", []) if job.params else []
        if lead_id in lead_ids or job.id == lead.job_id:
            result.append(job)
    return result


@router.post("/{lead_id}/reclassify", response_model=LeadOut)
def reclassify_lead(
    lead_id: int,
    body: ReclassifyRequest | None = None,
    db: Session = Depends(get_db),
):
    from app.pipeline.enrichment.classifier import classify
    from app.pipeline.enrichment.providers.classification_provider import (
        consolidate_lead_for_classification,
    )

    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Best-effort lock; SQLite (tests) ignores
    try:
        db.query(Lead).filter(Lead.id == lead_id).with_for_update(nowait=False).first()
    except Exception:
        pass

    force = body.force if body is not None else False  # default: preserve manual nicho

    from app.pipeline.enrichment.classifier import build_classifier_llm_client
    lead_data = consolidate_lead_for_classification(lead)
    result = classify(lead_data, llm_client=build_classifier_llm_client())

    # Preserve manual nicho when not forced
    result_dict = result.to_dict()
    if lead.nicho_source == "manual" and not force:
        result_dict["nicho_canonico"] = lead.nicho_canonico
        result_dict["nicho_source"] = lead.nicho_source
        result_dict["nicho_confidence"] = lead.nicho_confidence

    # Don't persist hash for failed runs — lets future runs retry after aliases/LLM improve
    if result_dict.get("nicho_source") == "failed":
        result_dict.pop("classification_hash", None)

    for k, v in result_dict.items():
        if hasattr(lead, k) and v is not None:
            setattr(lead, k, v)
    lead.classified_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/bulk", response_model=BulkUpdateResult)
def bulk_update_leads(payload: BulkLeadUpdate, db: Session = Depends(get_db)):
    update_data = payload.data.model_dump(exclude_unset=True)
    if not update_data:
        return BulkUpdateResult(updated=0)

    if "status" in update_data and update_data["status"] not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status: {update_data['status']}",
        )

    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    found_ids = {l.id for l in leads}
    errors = [
        BulkUpdateError(lead_id=lid, error="Lead not found")
        for lid in payload.lead_ids
        if lid not in found_ids
    ]

    sets_nicho = "nicho_canonico" in update_data
    for lead in leads:
        for k, v in update_data.items():
            setattr(lead, k, v)
        if sets_nicho:
            lead.nicho_source = "manual"
            lead.nicho_confidence = 1.0

    try:
        db.commit()
        updated = len(leads)
    except Exception as exc:  # noqa: BLE001 — surface commit failure as global error
        db.rollback()
        updated = 0
        errors.append(BulkUpdateError(lead_id=0, error=f"Commit failed: {str(exc)[:200]}"))

    return BulkUpdateResult(updated=updated, errors=errors)


@router.delete("/bulk", response_model=BulkDeleteResult)
def bulk_delete_leads(payload: BulkLeadDelete, db: Session = Depends(get_db)):
    leads = db.query(Lead).filter(Lead.id.in_(payload.lead_ids)).all()
    found_ids = {l.id for l in leads}
    errors = [
        BulkUpdateError(lead_id=lid, error="Lead not found")
        for lid in payload.lead_ids
        if lid not in found_ids
    ]

    for lead in leads:
        db.delete(lead)

    try:
        db.commit()
        deleted = len(leads)
    except Exception as exc:  # noqa: BLE001 — surface commit failure as global error
        db.rollback()
        deleted = 0
        errors.append(BulkUpdateError(lead_id=0, error=f"Commit failed: {str(exc)[:200]}"))

    return BulkDeleteResult(deleted=deleted, errors=errors)


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

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    if "nicho_canonico" in update_data:
        lead.nicho_source = "manual"
        lead.nicho_confidence = 1.0

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

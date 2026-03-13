import asyncio
import json
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.database import get_db, SessionLocal
from app.models import Lead, Job, OutreachMessage
from app.schemas import (
    ScrapeRequest, EnrichRequest, GenerateRequest, OutreachRequest,
    JobOut, JobListOut,
)
from app.config import settings

router = APIRouter(prefix="/api", tags=["pipeline"])

# ---------------------------------------------------------------------------
# In-memory SSE events
# ---------------------------------------------------------------------------

_job_events: dict[int, list[dict]] = {}


def _emit(job_id: int, event: dict):
    if job_id not in _job_events:
        _job_events[job_id] = []
    _job_events[job_id].append(event)
    if event.get("type") in ("done", "error"):
        threading.Timer(60, lambda: _job_events.pop(job_id, None)).start()


# ---------------------------------------------------------------------------
# Background task runners
# ---------------------------------------------------------------------------


def _run_scrape(job_id: int, params: dict):
    from app.pipeline.scraper import scrape_all

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        nichos = params.get("nichos") or settings.target_niches
        cidades = params.get("cidades") or settings.target_cities
        max_results = params.get("max_results") or settings.max_results_per_search

        raw_leads = scrape_all(nichos=nichos, cidades=cidades, max_results=max_results)

        created = 0
        errors: list[str] = []
        for idx, ld in enumerate(raw_leads):
            try:
                lead = Lead(
                    nome=ld["nome"],
                    telefone=ld.get("telefone"),
                    website=ld.get("website"),
                    endereco=ld.get("endereco"),
                    cidade=ld.get("cidade"),
                    nicho=ld.get("nicho"),
                    categoria=ld.get("categoria"),
                    rating=ld.get("rating"),
                    reviews_count=ld.get("reviews_count", 0),
                    google_maps_url=ld.get("google_maps_url"),
                    top_reviews=ld.get("top_reviews", []),
                    status="scraped",
                    job_id=job_id,
                )
                db.add(lead)
                db.commit()
                created += 1
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(raw_leads)})
            except Exception as exc:
                db.rollback()
                errors.append(f"Lead {ld.get('nome', '?')}: {str(exc)[:120]}")

        job.status = "done"
        job.result_summary = {"created": created, "total_scraped": len(raw_leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()


def _run_enrich(job_id: int, params: dict):
    from app.pipeline.enricher import enrich_lead_data

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        lead_ids = params.get("lead_ids", [])
        if lead_ids:
            leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "scraped").all()

        enriched = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:
                result = enrich_lead_data(lead.website or "")
                lead.opportunity_score = result["opportunity_score"]
                lead.opportunity_reasons = result["opportunity_reasons"]
                lead.site_analysis = result["site_analysis"]
                lead.status = "enriched"
                db.commit()
                enriched += 1
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()
                lead.status = "enrich_failed"
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done"
        job.result_summary = {"enriched": enriched, "total": len(leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()


def _run_generate(job_id: int, params: dict):
    from app.pipeline.generator import generate_landing_page

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        lead_ids = params.get("lead_ids", [])
        max_count = params.get("max_count", 50)
        if lead_ids:
            leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "enriched").limit(max_count).all()

        generated = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:
                lead_data = {
                    "nome": lead.nome,
                    "telefone": lead.telefone,
                    "website": lead.website,
                    "endereco": lead.endereco,
                    "cidade": lead.cidade,
                    "nicho": lead.nicho,
                    "categoria": lead.categoria,
                    "rating": float(lead.rating) if lead.rating else None,
                    "reviews_count": lead.reviews_count,
                    "top_reviews": lead.top_reviews or [],
                    "opportunity_reasons": lead.opportunity_reasons or [],
                    "site_analysis": lead.site_analysis or {},
                }
                html = generate_landing_page(lead_data)
                if html:
                    lead.lp_html = html
                    lead.status = "generated"
                    db.commit()
                    generated += 1
                else:
                    lead.status = "generate_failed"
                    db.commit()
                    errors.append(f"Lead {lead.id} ({lead.nome}): empty HTML returned")
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()
                lead.status = "generate_failed"
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done"
        job.result_summary = {"generated": generated, "total": len(leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()


def _run_outreach(job_id: int, params: dict):
    from app.pipeline.outreach import generate_messages

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        lead_ids = params.get("lead_ids", [])
        if lead_ids:
            leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "generated").all()

        messaged = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:
                lead_data = {
                    "nome": lead.nome,
                    "telefone": lead.telefone,
                    "website": lead.website,
                    "rating": float(lead.rating) if lead.rating else None,
                    "reviews_count": lead.reviews_count,
                    "opportunity_reasons": lead.opportunity_reasons or [],
                    "site_analysis": lead.site_analysis or {},
                }
                messages = generate_messages(lead.id, lead_data)
                for msg in messages:
                    om = OutreachMessage(
                        lead_id=lead.id,
                        type=msg["type"],
                        message_text=msg["message_text"],
                        whatsapp_link=msg.get("whatsapp_link", ""),
                    )
                    db.add(om)
                lead.status = "outreach_ready"
                db.commit()
                messaged += 1
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()
                lead.status = "outreach_failed"
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done"
        job.result_summary = {"messaged": messaged, "total": len(leads), "errors": errors}
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": job.result_summary})

    except Exception as exc:
        db.rollback()
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:500]})
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Runner dispatch
# ---------------------------------------------------------------------------

_RUNNERS = {
    "scrape": _run_scrape,
    "enrich": _run_enrich,
    "generate": _run_generate,
    "outreach": _run_outreach,
}


def _start_job(job_type: str, params: dict, bg: BackgroundTasks, db: Session) -> Job:
    job = Job(type=job_type, params=params)
    db.add(job)
    db.commit()
    db.refresh(job)
    bg.add_task(_RUNNERS[job_type], job.id, params)
    return job


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/pipeline/scrape", response_model=JobOut)
def run_scrape(req: ScrapeRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    params = req.model_dump()
    job = _start_job("scrape", params, bg, db)
    return job


@router.post("/pipeline/enrich", response_model=JobOut)
def run_enrich(req: EnrichRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    params = req.model_dump()
    job = _start_job("enrich", params, bg, db)
    return job


@router.post("/pipeline/generate", response_model=JobOut)
def run_generate(req: GenerateRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    params = req.model_dump()
    job = _start_job("generate", params, bg, db)
    return job


@router.post("/pipeline/outreach", response_model=JobOut)
def run_outreach(req: OutreachRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    params = req.model_dump()
    job = _start_job("outreach", params, bg, db)
    return job


@router.get("/jobs", response_model=JobListOut)
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(Job).count()
    items = (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return JobListOut(items=items, total=total, page=page, per_page=per_page)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        sent = 0
        while True:
            events = _job_events.get(job_id, [])
            while sent < len(events):
                yield {"data": json.dumps(events[sent])}
                if events[sent].get("type") in ("done", "error"):
                    return
                sent += 1
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())

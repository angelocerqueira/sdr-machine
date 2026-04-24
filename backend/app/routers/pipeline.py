import asyncio
import json
import logging
import threading
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.database import get_db, SessionLocal
from app.models import LandingPage, Lead, Job, OutreachMessage
from app.pipeline.enrichment.classifier_enums import NichoSource
from app.schemas import (
    ScrapeRequest, EnrichRequest, GenerateRequest, OutreachRequest,
    JobOut, JobListOut, PipelineStatusOut,
    ClassifyRequest,
)
from app.config import settings

logger = logging.getLogger(__name__)

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
        fontes = params.get("fontes") or ["google_maps", "cnpj"]

        raw_leads, errors = scrape_all(nichos=nichos, cidades=cidades, max_results=max_results, fontes=fontes)

        created = 0
        skipped_existing = 0
        for idx, ld in enumerate(raw_leads):
            try:
                place_id = ld.get("place_id")
                if place_id:
                    existing = db.query(Lead).filter(Lead.place_id == place_id).first()
                    if existing:
                        skipped_existing += 1
                        _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(raw_leads)})
                        continue

                lead = Lead(
                    nome=ld["nome"],
                    telefone=ld.get("telefone"),
                    website=ld.get("website"),
                    email=ld.get("email"),
                    cnpj=ld.get("cnpj"),
                    razao_social=ld.get("razao_social"),
                    porte=ld.get("porte"),
                    cnae=ld.get("cnae"),
                    endereco=ld.get("endereco"),
                    cidade=ld.get("cidade"),
                    nicho=ld.get("nicho"),
                    categoria=ld.get("categoria"),
                    rating=ld.get("rating"),
                    reviews_count=ld.get("reviews_count", 0),
                    google_maps_url=ld.get("google_maps_url"),
                    place_id=place_id,
                    top_reviews=ld.get("top_reviews", []),
                    has_instagram=ld.get("has_instagram"),
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

        job.status = "done_with_errors" if errors else "done"
        job.result_summary = {
            "created": created,
            "skipped_existing": skipped_existing,
            "total_scraped": len(raw_leads),
            "errors": errors,
        }
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
    from app.pipeline.enricher import enrich_lead_via_orchestrator
    from app.pipeline.enrichment.apply import apply_enrichment_result

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        _emit(job_id, {"type": "started", "job_id": job_id})

        lead_ids = params.get("lead_ids", [])
        skip_providers = params.get("skip_providers", []) or []
        force_providers = params.get("force_providers", []) or []

        if lead_ids:
            leads = db.query(Lead).filter(Lead.id.in_(lead_ids)).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "scraped").all()

        enriched = 0
        errors: list[str] = []
        for idx, lead in enumerate(leads):
            try:
                result = enrich_lead_via_orchestrator(
                    lead,
                    skip_providers=skip_providers,
                    force_providers=force_providers,
                )
                apply_enrichment_result(lead, result)
                lead.status = "enriched"
                enriched += 1
                db.commit()
                _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(leads)})
            except Exception as exc:
                db.rollback()
                lead.status = "enrich_failed"
                db.commit()
                errors.append(f"Lead {lead.id} ({lead.nome}): {str(exc)[:120]}")

        job.status = "done_with_errors" if errors else "done"
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
            leads = db.query(Lead).filter(
                Lead.id.in_(lead_ids),
                Lead.status != "disqualified",
            ).all()
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
                    # Deactivate previous LPs
                    db.query(LandingPage).filter(
                        LandingPage.lead_id == lead.id, LandingPage.is_active.is_(True)
                    ).update({"is_active": False})
                    # Get next version number
                    max_version = db.query(func.max(LandingPage.version)).filter(
                        LandingPage.lead_id == lead.id
                    ).scalar() or 0
                    # Create new LP record
                    lp = LandingPage(
                        lead_id=lead.id,
                        html=html,
                        version=max_version + 1,
                        is_active=True,
                    )
                    db.add(lp)
                    lead.lp_html = html
                    lead.status = "lp_generated"
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

        job.status = "done_with_errors" if errors else "done"
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
            leads = db.query(Lead).filter(
                Lead.id.in_(lead_ids),
                Lead.status != "disqualified",
            ).all()
        else:
            leads = db.query(Lead).filter(Lead.status == "lp_generated").all()

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

        job.status = "done_with_errors" if errors else "done"
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


def _run_csv_import(job_id: int, params: dict):
    from app.pipeline.csv_importer import parse_csv

    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "started", "job_id": job_id})

        file_content = params["file_content"]
        nicho = params.get("nicho", "")
        cidade = params.get("cidade", "")

        raw_leads, parse_errors = parse_csv(file_content)
        errors = list(parse_errors)
        created = 0
        skipped = 0

        for idx, ld in enumerate(raw_leads):
            try:
                # Dedup: check nome + telefone
                existing = db.query(Lead).filter(
                    Lead.nome == ld["nome"],
                    Lead.telefone == ld.get("telefone"),
                ).first()
                if existing:
                    skipped += 1
                    _emit(job_id, {"type": "progress", "current": idx + 1, "total": len(raw_leads)})
                    continue

                lead = Lead(
                    nome=ld["nome"],
                    telefone=ld.get("telefone"),
                    website=ld.get("website"),
                    endereco=ld.get("endereco"),
                    cidade=ld.get("cidade") or cidade,
                    nicho=ld.get("nicho") or nicho,
                    categoria=ld.get("categoria"),
                    rating=ld.get("rating"),
                    email=ld.get("email"),
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

        job.status = "done_with_errors" if errors else "done"
        job.result_summary = {
            "created": created,
            "skipped": skipped,
            "total": len(raw_leads),
            "errors": errors,
        }
        job.finished_at = datetime.utcnow()
        db.commit()

        # Chain: trigger classification over the imported batch
        try:
            # Respect concurrency guard — skip if another classification is already running
            existing_classify = db.query(Job).filter(
                Job.type == "classification",
                Job.status.in_(["pending", "running"]),
            ).first()
            if existing_classify:
                logger.info(
                    "skipping auto-chain: classification job %s still %s",
                    existing_classify.id, existing_classify.status,
                )
            else:
                classify_job = Job(
                    type="classification", status="pending",
                    params={
                        "scope": "by_job",
                        "scope_filter": {"job_id": job_id},
                        "force": False,
                    },
                )
                db.add(classify_job)
                db.commit()
                threading.Thread(
                    target=_run_classify,
                    args=(classify_job.id, classify_job.params),
                    daemon=True,
                ).start()
        except Exception as exc:
            logger.warning("failed to chain classification: %s", exc)

        _emit(job_id, {"type": "done", "summary": job.result_summary})
    except Exception as exc:
        job = db.get(Job, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.utcnow()
            db.commit()
        _emit(job_id, {"type": "error", "message": str(exc)[:200]})
    finally:
        db.close()


def _run_classify(job_id: int, params: dict):
    """Background runner for batch classification.

    Isolates failures per-lead. Circuit breaker at 50% exception rate after 20 leads.
    Soft nicho failures (nicho_source=failed) do NOT count toward circuit breaker.
    """
    from app.pipeline.enrichment.classifier import classify, build_classifier_llm_client
    from app.pipeline.enrichment.providers.classification_provider import (
        consolidate_lead_for_classification,
    )

    db = SessionLocal()
    llm_client = build_classifier_llm_client()
    try:
        job = db.get(Job, job_id)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "started", "job_id": job_id})

        scope = params.get("scope", "unclassified")
        scope_filter = params.get("scope_filter") or {}
        force = params.get("force", False)

        query = db.query(Lead)
        if scope == "unclassified":
            query = query.filter(Lead.perfil_lead.is_(None))
        elif scope == "by_job":
            jid = scope_filter.get("job_id")
            if jid is None:
                raise ValueError("scope=by_job requires scope_filter.job_id")
            query = query.filter(Lead.job_id == jid)
        elif scope == "by_status":
            st = scope_filter.get("status")
            if not st:
                raise ValueError("scope=by_status requires scope_filter.status")
            query = query.filter(Lead.status == st)
        elif scope != "all":
            raise ValueError(f"unknown classification scope: {scope!r}")
        # "all" → no filter

        leads = query.all()
        total = len(leads)
        _emit(job_id, {"type": "progress", "current": 0, "total": total})

        results = {"ok": 0, "failed": 0, "skipped": 0, "errors": {}}
        exceptions = 0  # separate counter — only hard exceptions count toward circuit breaker

        for idx, lead in enumerate(leads):
            try:
                lead_data = consolidate_lead_for_classification(lead)
                result = classify(lead_data, llm_client=llm_client)

                # Idempotency: skip if hash unchanged (and not forced)
                if (lead.classification_hash == result.classification_hash
                        and not force):
                    results["skipped"] += 1
                else:
                    # Preserve manual nicho unless forced
                    if lead.nicho_source == "manual" and not force:
                        result.nicho_canonico = lead.nicho_canonico
                        result.nicho_source = lead.nicho_source
                        result.nicho_confidence = lead.nicho_confidence

                    result_dict = result.to_dict()
                    # Don't persist hash for failed runs — lets future runs retry
                    if result.nicho_source == NichoSource.FAILED or (
                        hasattr(result.nicho_source, "value")
                        and result.nicho_source.value == "failed"
                    ) or result.nicho_source == "failed":
                        result_dict.pop("classification_hash", None)

                    for k, v in result_dict.items():
                        if hasattr(lead, k) and v is not None:
                            setattr(lead, k, v)
                    lead.classified_at = datetime.utcnow()
                    db.commit()

                    if result.nicho_source == NichoSource.FAILED or result.nicho_source == "failed":
                        results["failed"] += 1
                    else:
                        results["ok"] += 1
            except Exception as exc:
                db.rollback()
                results["failed"] += 1
                exceptions += 1  # only hard exceptions count toward breaker
                results["errors"][lead.id] = str(exc)[:200]

            # Circuit breaker: >50% hard exceptions after 20 processed
            if idx + 1 >= 20:
                exception_rate = exceptions / (idx + 1)
                if exception_rate > 0.5:
                    job.status = "stalled"
                    job.result_summary = {**results, "reason": "too_many_failures", "exceptions": exceptions}
                    job.finished_at = datetime.utcnow()
                    db.commit()
                    _emit(job_id, {"type": "error", "message": "too_many_failures"})
                    return

            # Progress every 5 leads (or on last)
            if (idx + 1) % 5 == 0 or (idx + 1) == total:
                _emit(job_id, {
                    "type": "progress",
                    "current": idx + 1, "total": total,
                    "summary": results,
                })

        job.status = "done_with_errors" if results["failed"] else "done"
        job.result_summary = results
        job.finished_at = datetime.utcnow()
        db.commit()
        _emit(job_id, {"type": "done", "summary": results})

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
    "csv_import": _run_csv_import,
    "classification": _run_classify,
}


def _start_job(job_type: str, params: dict, bg: BackgroundTasks, db: Session) -> Job:
    existing = db.query(Job).filter(Job.type == job_type, Job.status == "running").first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe um job '{job_type}' em execução (#{existing.id})"
        )
    job = Job(type=job_type, params=params)
    db.add(job)
    db.commit()
    db.refresh(job)
    bg.add_task(_RUNNERS[job_type], job.id, params)
    return job


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/pipeline/status", response_model=PipelineStatusOut)
def pipeline_status(db: Session = Depends(get_db)):
    eligible = {
        "scrape": 0,
        "enrich": db.query(Lead).filter(Lead.status == "scraped").count(),
        "generate": db.query(Lead).filter(Lead.status == "enriched").count(),
        "outreach": db.query(Lead).filter(Lead.status == "lp_generated").count(),
        "disqualified": db.query(Lead).filter(Lead.status == "disqualified").count(),
    }
    running = [
        row[0] for row in
        db.query(Job.type).filter(Job.status == "running").distinct().all()
    ]
    return PipelineStatusOut(eligible_counts=eligible, running_jobs=running)


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


@router.post("/pipeline/classify", response_model=JobOut)
def start_classify_job(
    body: ClassifyRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Guard against concurrent classification jobs
    existing = db.query(Job).filter(
        Job.type == "classification",
        Job.status.in_(["pending", "running"]),
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"classification job already in progress (id={existing.id})",
        )

    job = Job(type="classification", status="pending", params=body.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(_run_classify, job.id, body.model_dump())
    return job


@router.post("/pipeline/csv-import", response_model=JobOut)
async def run_csv_import(
    file: UploadFile = File(...),
    nicho: str = Form(""),
    cidade: str = Form(""),
    bg: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um CSV")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo excede limite de 5MB")

    try:
        file_content = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            file_content = content.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Encoding do arquivo não suportado")

    params = {"file_content": file_content, "nicho": nicho, "cidade": cidade}
    job = _start_job("csv_import", params, bg, db)
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

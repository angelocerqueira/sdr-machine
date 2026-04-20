from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Lead
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats/trends")
def get_dashboard_trends(days: int = 30, db: Session = Depends(get_db)):
    """Returns daily lead counts, job counts, score distribution, and top nichos for the last N days."""
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Leads created per day
    leads_by_day = (
        db.query(
            func.date(Lead.created_at).label("day"),
            func.count(Lead.id).label("count"),
        )
        .filter(Lead.created_at >= cutoff)
        .group_by(func.date(Lead.created_at))
        .order_by(func.date(Lead.created_at))
        .all()
    )

    # Jobs per day
    jobs_by_day = (
        db.query(
            func.date(Job.created_at).label("day"),
            func.count(Job.id).label("count"),
        )
        .filter(Job.created_at >= cutoff)
        .group_by(func.date(Job.created_at))
        .order_by(func.date(Job.created_at))
        .all()
    )

    # Score distribution buckets
    score_buckets: dict[str, int] = {}
    leads_with_score = (
        db.query(Lead.opportunity_score)
        .filter(Lead.opportunity_score.isnot(None))
        .all()
    )
    for (score,) in leads_with_score:
        bucket = f"{(score // 10) * 10}-{(score // 10) * 10 + 9}"
        score_buckets[bucket] = score_buckets.get(bucket, 0) + 1

    # Leads by nicho (top 10)
    nicho_counts = (
        db.query(Lead.nicho, func.count(Lead.id))
        .filter(Lead.nicho.isnot(None))
        .group_by(Lead.nicho)
        .order_by(func.count(Lead.id).desc())
        .limit(10)
        .all()
    )

    return {
        "leads_by_day": [{"day": str(day), "count": count} for day, count in leads_by_day],
        "jobs_by_day": [{"day": str(day), "count": count} for day, count in jobs_by_day],
        "score_distribution": score_buckets,
        "leads_by_nicho": [{"nicho": n, "count": c} for n, c in nicho_counts],
    }


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    avg_score = db.query(func.avg(Lead.opportunity_score)).scalar()
    total_jobs = db.query(func.count(Job.id)).scalar() or 0

    rows = (
        db.query(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
        .all()
    )
    leads_by_status: dict[str, int] = {}
    for status, count in rows:
        if status and status.endswith("_failed"):
            leads_by_status["failed"] = leads_by_status.get("failed", 0) + count
        else:
            leads_by_status[status] = count

    conversion_rate = None
    if total_leads > 0:
        converted = leads_by_status.get("closed", 0) + leads_by_status.get("delivered", 0)
        conversion_rate = round(converted / total_leads * 100, 2)

    profile_dist_rows = (
        db.query(Lead.perfil_lead, func.count(Lead.id))
        .filter(Lead.perfil_lead.isnot(None))
        .group_by(Lead.perfil_lead)
        .all()
    )
    profile_distribution = {row[0]: row[1] for row in profile_dist_rows}

    nicho_dist_rows = (
        db.query(Lead.nicho_canonico, func.count(Lead.id))
        .filter(Lead.nicho_canonico.isnot(None))
        .group_by(Lead.nicho_canonico)
        .all()
    )
    nicho_distribution = {row[0]: row[1] for row in nicho_dist_rows}

    return DashboardStats(
        total_leads=total_leads,
        leads_by_status=leads_by_status,
        avg_score=round(avg_score, 2) if avg_score is not None else None,
        total_jobs=total_jobs,
        conversion_rate=conversion_rate,
        profile_distribution=profile_distribution,
        nicho_distribution=nicho_distribution,
    )

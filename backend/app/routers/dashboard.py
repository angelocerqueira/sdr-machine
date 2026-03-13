from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Lead
from app.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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
    leads_by_status = {status: count for status, count in rows}

    conversion_rate = None
    if total_leads > 0:
        converted = leads_by_status.get("closed", 0) + leads_by_status.get("delivered", 0)
        conversion_rate = round(converted / total_leads * 100, 2)

    return DashboardStats(
        total_leads=total_leads,
        leads_by_status=leads_by_status,
        avg_score=round(avg_score, 2) if avg_score is not None else None,
        total_jobs=total_jobs,
        conversion_rate=conversion_rate,
    )

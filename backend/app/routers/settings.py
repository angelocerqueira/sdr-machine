from fastapi import APIRouter

from app.config import settings as app_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return {
        "target_niches": app_settings.target_niches,
        "target_cities": app_settings.target_cities,
        "min_rating": app_settings.min_rating,
        "max_results_per_search": app_settings.max_results_per_search,
        "opportunity_score_threshold": app_settings.opportunity_score_threshold,
        "business_name": app_settings.business_name,
        "your_name": app_settings.your_name,
    }

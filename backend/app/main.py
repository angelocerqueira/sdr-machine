import datetime
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings as app_settings
from app.database import SessionLocal
from app.integrations.crypto import SettingsEncKeyMissing
from app.middleware import AuthMiddleware
from app.models import Job
from app.routers import dashboard, leads, pipeline, settings, workspace_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="SDR Machine API", version="1.0.0")


@app.on_event("startup")
def _reap_orphaned_jobs() -> None:
    """Mark jobs left running/pending from a previous process as failed.

    Runner threads are daemons — Railway redeploys (and any process death)
    drop them mid-execution. Without this, the UI shows those jobs stuck
    on "running" forever and `_start_job`'s same-type guard blocks new ones.
    """
    db = SessionLocal()
    try:
        stale = db.query(Job).filter(Job.status.in_(["pending", "running"])).all()
        for job in stale:
            job.status = "failed"
            job.error_message = "interrupted by server restart"
            job.finished_at = datetime.datetime.utcnow()
        if stale:
            db.commit()
            logger.warning(
                "startup.reaped_orphaned_jobs count=%d ids=%s",
                len(stale), [j.id for j in stale],
            )
    except Exception:
        logger.exception("startup.reap_failed")
        db.rollback()
    finally:
        db.close()


@app.exception_handler(SettingsEncKeyMissing)
async def _settings_enc_key_missing_handler(request: Request, exc: SettingsEncKeyMissing):
    """503 com mensagem clara quando crypto é usado sem master key configurada.

    Container sobe sem SETTINGS_ENC_KEY (config default ""), mas qualquer
    fluxo que precise cifrar/decifrar (Settings UI: PUT credencial, GET
    integração já cadastrada) bate aqui. Operador adiciona o secret e
    reinicia — sem code change.
    """
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )

cors_origins = ["http://localhost:3000", "http://localhost:4000"]
if app_settings.frontend_url and app_settings.frontend_url not in cors_origins:
    cors_origins.append(app_settings.frontend_url)
for extra in app_settings.cors_extra_origins.split(","):
    extra = extra.strip()
    if extra and extra not in cors_origins:
        cors_origins.append(extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    AuthMiddleware,
    database_url=app_settings.database_url,
    public_paths=["/api/health", "/api/leads/p/", "/docs", "/openapi.json"],
)

app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(pipeline.router)
app.include_router(workspace_settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

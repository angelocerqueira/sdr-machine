import contextlib
import datetime
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings as app_settings
from app.database import SessionLocal
from app.integrations.crypto import SettingsEncKeyMissing
from app.mcp.server import build_mcp_server
from app.middleware import AuthMiddleware
from app.models import Job
from app.routers import conversations, dashboard, leads, mcp_tokens_router, pipeline, settings, webhooks, workspace_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="SDR Machine API", version="1.0.0")

# MCP server lives on app.state and is rebuilt each lifespan entry.
# StreamableHTTPSessionManager.run() can only be called once per instance, so
# tests (que entram no lifespan múltiplas vezes via TestClient) precisam de uma
# nova instância a cada startup. A Mount route abaixo tem seu `.app` atualizado
# dentro do lifespan pra apontar pro server vigente.
_initial_mcp_server = build_mcp_server()
_mcp_mount_app = _initial_mcp_server.streamable_http_app()
app.state.mcp_server = _initial_mcp_server


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


@contextlib.asynccontextmanager
async def _combined_lifespan(_app):
    """Combina startup hooks legados + MCP session_manager.

    SDK FastMCP 1.27 exige que `session_manager.run()` esteja ativo durante o
    ciclo de vida da app pra servir requests no streamable_http transport. Como
    estamos migrando do `@app.on_event("startup")` (deprecated), inlineamos o
    reaper aqui pra preservar o comportamento existente.

    O server MCP é reconstruído a cada entrada de lifespan porque o
    StreamableHTTPSessionManager interno só permite uma chamada a `.run()` por
    instância — tests entram/saem do lifespan múltiplas vezes via TestClient.
    """
    _reap_orphaned_jobs()
    # Reap MCP pending actions expired
    try:
        from app.mcp.reaper import reap_expired_actions
        db = SessionLocal()
        try:
            reap_expired_actions(db)
        finally:
            db.close()
    except Exception:
        logger.exception("startup.reap_mcp_failed")
    server = build_mcp_server()
    _app.state.mcp_server = server
    # Aponta a Mount route pro ASGI app do server recém-criado.
    _mcp_mount.app = server.streamable_http_app()
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(server.session_manager.run())
        yield


app.router.lifespan_context = _combined_lifespan


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
    public_paths=[
        "/api/health",
        "/api/leads/p/",
        "/api/webhooks",
        "/api/mcp",
        "/docs",
        "/openapi.json",
    ],
)

app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(pipeline.router)
app.include_router(workspace_settings.router)
app.include_router(webhooks.router)
app.include_router(conversations.router)
app.include_router(mcp_tokens_router.router)

# Mount MCP server. AuthMiddleware lets /api/mcp through; FastMCP has its own
# Bearer auth via TokenVerifier. O `.app` da Mount é trocado dentro do lifespan
# pra apontar pro server vigente daquele ciclo.
app.mount("/api/mcp", _mcp_mount_app)

# Captura a Mount route recém-criada pra que o lifespan possa swapear seu `.app`.
_mcp_mount = next(r for r in app.router.routes if getattr(r, "path", None) == "/api/mcp")


@app.get("/api/health")
def health():
    return {"status": "ok"}

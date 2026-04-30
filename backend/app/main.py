from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings as app_settings
from app.integrations.crypto import SettingsEncKeyMissing
from app.middleware import AuthMiddleware
from app.routers import dashboard, leads, pipeline, settings, workspace_settings

app = FastAPI(title="SDR Machine API", version="1.0.0")


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

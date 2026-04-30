from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings as app_settings
from app.middleware import AuthMiddleware
from app.routers import dashboard, leads, pipeline, settings, workspace_settings

app = FastAPI(title="SDR Machine API", version="1.0.0")

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

"""
Ponto de entrada da aplicação FastAPI do SAGA.

Responsabilidades:
- Instanciar a aplicação FastAPI e configurar lifespan Firebase.
- Registrar todos os routers sob /api/v1.
- Configurar CORS e health check.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.firebase import init_firebase, shutdown_firebase


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield
    shutdown_firebase()


app = FastAPI(
    title="SAGA — Sistema de Acompanhamento e Gestão Acadêmica",
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from backend.app.api.v1 import (  # noqa: E402
    activities,
    activity_types,
    advisors,
    audit_logs,
    auth,
    checklist,
    dashboard,
    extensions,
    inference,
    productions,
    reports,
    students,
    vehicles,
    work_plan,
)

PREFIX = "/api/v1"

for module in [
    activities, activity_types, advisors, audit_logs, auth,
    checklist, dashboard, extensions, inference, productions,
    reports, students, vehicles, work_plan,
]:
    if hasattr(module, "router"):
        app.include_router(module.router, prefix=PREFIX)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.api_version}

"""
Ponto de entrada da aplicação FastAPI do SAGA.

Responsabilidades:
- Instanciar a aplicação FastAPI com título, versão e descrição do projeto.
- Configurar o lifespan (startup/shutdown) para inicializar e encerrar o Firebase Admin SDK
  via backend/app/core/firebase.py.
- Registrar os routers de cada domínio (auth, students, advisors, departments, work_plan,
  activities, activity_types, productions, vehicles, extensions, checklist, inference,
  reports, dashboard, audit_logs, notifications) sob o prefixo /api/v1.
- Configurar middlewares globais: CORS, tratamento de exceções HTTP e logging de requests.
- Expor endpoint público GET /api/v1/health para health check da API e conectividade Firebase.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1 import (
    activities,
    activity_types,
    advisors,
    audit_logs,
    auth,
    checklist,
    coordination_transfers,
    dashboard,
    departments,
    extensions,
    inference,
    notifications,
    productions,
    programs,
    qualis_weights,
    registration_requests,
    reports,
    requests,
    students,
    transfers,
    users,
    vehicles,
    work_plan,
)
from backend.app.core.config import settings
from backend.app.core.firebase import init_firebase, shutdown_firebase
from backend.app.api.v1.transfer_cross import router as transfer_cross_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_firebase()
        logger.info("Firebase Admin SDK inicializado com sucesso.")
    except Exception as exc:
        logger.warning("Falha ao inicializar Firebase Admin SDK: %s", exc)
    yield
    shutdown_firebase()
    logger.info("Firebase Admin SDK encerrado.")


app = FastAPI(
    title="SAGA — Sistema de Acompanhamento e Gestão Acadêmica",
    version=settings.api_version,
    description="API para gestão de programas de pós-graduação: discentes, planos, atividades e produções.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=_PREFIX, tags=["auth"])
app.include_router(students.router, prefix=_PREFIX, tags=["students"])
app.include_router(advisors.router, prefix=_PREFIX, tags=["advisors"])
app.include_router(departments.router, prefix=_PREFIX, tags=["departments"])
app.include_router(work_plan.router, prefix=_PREFIX, tags=["work-plan"])
app.include_router(activities.router, prefix=_PREFIX, tags=["activities"])
app.include_router(activity_types.router, prefix=_PREFIX, tags=["activity-types"])
app.include_router(productions.router, prefix=_PREFIX, tags=["productions"])
app.include_router(vehicles.router, prefix=_PREFIX, tags=["vehicles"])
app.include_router(extensions.router, prefix=_PREFIX, tags=["Prorrogações"])
app.include_router(checklist.router, prefix=_PREFIX, tags=["checklist"])
app.include_router(coordination_transfers.router, prefix=_PREFIX, tags=["coordination-transfers"])
app.include_router(programs.router, prefix=_PREFIX, tags=["programs"])
app.include_router(qualis_weights.router, prefix=_PREFIX, tags=["qualis-weights"])
app.include_router(
    registration_requests.router,
    prefix=_PREFIX,
    tags=["registration-requests"],
)
app.include_router(inference.router, prefix=_PREFIX, tags=["inference"])
app.include_router(reports.router, prefix=_PREFIX, tags=["reports"])
app.include_router(dashboard.router, prefix=_PREFIX, tags=["dashboard"])
app.include_router(audit_logs.router, prefix=_PREFIX, tags=["audit-logs"])
app.include_router(notifications.router, prefix=_PREFIX, tags=["notifications"])
app.include_router(transfers.router, prefix=_PREFIX, tags=["transfers"])
app.include_router(users.router, prefix=_PREFIX, tags=["users"])
app.include_router(requests.router, prefix=_PREFIX, tags=["requests"])
app.include_router(transfer_cross_router)
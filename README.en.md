<div align="center">

# SAGA — Academic Monitoring and Management System

[🇧🇷 Português](./README.md) · **[🇺🇸 English](./README.en.md)**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%2B%20Auth%20%2B%20Storage-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Status](https://img.shields.io/badge/Status-MVP%20Complete-brightgreen)](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica)

<br/>

> Academic project for the **Problem Solving III** course — combining **Logic Programming** (custom inference engine) and **Aspect-Oriented Programming** (native Python mechanisms) in a real graduate program management system.

[Repository](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica) · [Technical Docs](./docs/) · [Wiki](./docs/Home.md) · [Project Brief](./docs/enunciado.md)

</div>

---

## Table of Contents

- [About](#about)
- [Implemented Paradigms](#implemented-paradigms)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation & Running](#installation--running)
- [Environment Variables](#environment-variables)
- [Inference Engine](#inference-engine)
- [AOP Aspects](#aop-aspects)
- [Roles & Permissions](#roles--permissions)
- [API Routes](#api-routes)
- [Documentation & Decisions](#documentation--decisions)
- [Methodology](#methodology)
- [Deadlines](#deadlines)
- [Team](#team)

---

## About

SAGA is an academic monitoring system for **graduate programs (Master's)**, managing the full student lifecycle: enrollment, work plans, creditable activities, completion checklists, deadline extensions, transfers, and management reports.

The domain is intentionally complex — rules that cross multiple modules — making it an ideal environment to exercise two paradigms in an integrated way:

- The **logic engine** decides what is true in the system (defense eligibility, academic status, credit validation).
- The **aspects** define how each operation is intercepted and enriched (authorization, auditing, history, alerts), keeping business logic clean.

> For the full domain model (entities, ubiquitous language, business rules), see [`CONTEXT.md`](./CONTEXT.md).

### Student Statuses

| Status | Description |
|--------|-------------|
| 🟢 Regular | On track, plan up to date |
| 🔄 On Extension | Additional semester granted and ongoing |
| 🔴 At Risk | Pending items or overdue deadlines |
| ✅ Qualified | Passed the qualification exam |
| 📝 Defense Phase | Eligible for defense and proceeding |
| 🎓 Completed | Finished the program and defended |
| ❌ Dismissed | Removed from the program |

---

## Implemented Paradigms

### Logic Programming — Inference Engine

Engine built **from scratch in pure Python**, with no external logic programming libraries. Implements:

- Term representation (`Atom`, `Variable`, `Compound`)
- **Unification** algorithm
- **Substitutions** as variable → value dictionaries
- **Query resolution** (conjunction of conditions, no backtracking)
- Fact base and rule base separated from the resolution mechanism

Academic decisions are expressed as **declarative rules** — changing a policy means editing the rule, not rewriting control flow.

### Aspect-Oriented Programming

Implemented exclusively with **native Python mechanisms**: decorators, metaclasses, descriptors, `__init_subclass__`, and the `inspect` module. Covers the five mandatory cross-cutting concerns from the project brief (A01–A05), with join points, advices, and weaving explicitly documented in each module's docstring.

---

## Architecture

```
SAGA/
├── src/                              # Frontend — React + Vite + Tailwind
│   ├── app/
│   │   ├── components/               # Pages and UI components (shadcn/ui + MUI)
│   │   │   ├── auth/                 # Login, first access, password recovery
│   │   │   ├── dashboard/            # Role-based dashboards (student, advisor, coordination)
│   │   │   ├── students/             # Student management
│   │   │   ├── advisors/             # Advisor management
│   │   │   ├── workplan/             # Work plan / kanban (react-dnd)
│   │   │   ├── activities/           # Creditable activities
│   │   │   ├── productions/          # Bibliographic productions
│   │   │   ├── checklist/            # Completion checklist
│   │   │   ├── requests/             # Requests (extension, enrollment lock, transfer)
│   │   │   ├── extensions/           # Deadline extensions
│   │   │   ├── registration-requests/ # Enrollment requests
│   │   │   ├── transfers/            # Advisee / coordination transfers
│   │   │   ├── departments/          # Departments (managed by adm)
│   │   │   ├── inference/            # Logic engine visualization
│   │   │   ├── reports/              # Management reports (Recharts)
│   │   │   ├── export/               # Report export
│   │   │   ├── notifications/        # Notification center
│   │   │   ├── settings/            # Program & Qualis-weight settings
│   │   │   ├── audit/               # Audit log
│   │   │   └── layout/               # Sidebar, TopBar, AppLayout
│   │   ├── context/AppContext.tsx    # Global state
│   │   └── router/PrivateRoute.tsx   # Protected routes (react-router)
│   ├── api/                          # Domain-scoped HTTP clients
│   ├── hooks/                        # useAuth, useNotifications, useDashboard, …
│   └── lib/firebase.ts               # Firebase SDK (Auth + Firestore)
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI + Firebase lifespan + CORS
│   │   ├── core/                     # Config, Firebase Admin SDK, auth, email
│   │   ├── api/v1/                   # FastAPI routers per domain (+ tests/)
│   │   ├── models/                   # Pydantic schemas
│   │   ├── services/                 # Business logic + InferenceService
│   │   ├── repositories/             # Firestore + Storage access layer
│   │   └── aspects/                  # AOP aspects (A01–A05 + ownership)
│   │       └── aspect_config.py      # Flags to enable/disable aspects
│   │
│   ├── inference_engine/             # Logic engine — isolated, no external imports
│   │   ├── terms.py                  # Atom, Variable, Compound
│   │   ├── unification.py            # unify()
│   │   ├── substitution.py           # apply()
│   │   ├── resolver.py               # solve() — no backtracking
│   │   ├── knowledge_base.py         # FactBase + RuleBase + InferenceEngine
│   │   ├── rules/                    # RL01–RL05 (declarative modules)
│   │   └── tests/                    # pytest — coverage for all 5 rules
│   │
│   └── scripts/seed_firestore.py     # Firestore initial seed
│
├── docs/
│   ├── enunciado.md                  # Full project brief
│   ├── PRD.md · SDD.md               # Product Requirements + Spec-Driven Development
│   ├── CONTEXT.md → (root)           # Domain model / ubiquitous language
│   ├── adr/                          # Architecture Decision Records (0001–0009)
│   ├── user-stories/                 # User stories by theme
│   ├── specs/                        # 10 technical specification JSONs (01–10)
│   └── Home.md                       # Wiki landing page
│
├── guidelines/                       # Guidelines + commit conventions
├── pyproject.toml · uv.lock          # Python config (uv, >=3.12)
├── package.json · vite.config.ts     # Frontend (pnpm)
└── .env.example                      # Environment variables template
```

> Full backend layer tree in [`.claude/rules/architecture.md`](./.claude/rules/architecture.md).

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React | 18 |
| Build Tool | Vite | 6 |
| Styling | Tailwind CSS + shadcn/ui + MUI | 4 / — / 7 |
| Routing | react-router | 7 |
| Charts / Kanban | Recharts · react-dnd | — |
| Backend | FastAPI | 0.100+ |
| Backend Language | Python | 3.12+ |
| Database | Firebase Firestore | — |
| Storage | Firebase Storage (documents) | — |
| Authentication | Firebase Auth (JWT + custom claims) | — |
| Package Manager (BE) | uv | — |
| Package Manager (FE) | pnpm | — |
| Testing | pytest + pytest-asyncio | — |

---

## Installation & Running

### Prerequisites

- Node.js 20+ and [pnpm](https://pnpm.io/)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Firebase project configured ([Firebase Console](https://console.firebase.google.com/)) with Firestore + Authentication + Storage enabled

### Frontend

```bash
# Install dependencies
pnpm install

# Development server (http://localhost:5173)
pnpm dev

# Production build
pnpm build
```

### Backend

Managed with **uv** (see `uv.lock`); requires **Python ≥ 3.12**.

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Run FastAPI server (http://localhost:8000)
uv run uvicorn backend.app.main:app --reload --port 8000

# Run inference engine tests
uv run pytest backend/inference_engine/tests/ -v

# Lint and format (ruff)
uv run ruff check .
uv run ruff format .

# Seed Firestore (run once)
uv run python backend/scripts/seed_firestore.py
```

> **Without uv:** `python -m venv .venv` → activate (`source .venv/bin/activate` on Linux/macOS, `.venv\Scripts\activate` on Windows) → `pip install -e ".[dev]"`.

### Health Check

```
GET http://localhost:8000/api/v1/health
```

---

## Environment Variables

Copy [`.env.example`](./.env.example) to `.env` at the project root and fill in:

```env
# Backend — Firebase Admin SDK
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=
FIREBASE_STORAGE_BUCKET=

# API
API_VERSION=1.0.0-MVP
CORS_ORIGINS=["http://localhost:5173"]   # JSON array, not comma-separated
FRONTEND_URL=http://localhost:5173       # base for the first-access link

# Email (first-access invite) — any SMTP server
EMAIL_PROVIDER=smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@saga.local
SMTP_USE_TLS=true
EXPOSE_INVITE_TOKEN=true                  # false in production

# Frontend — Firebase SDK (Vite)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_PROJECT_ID=
VITE_AUTH_DOMAIN=
VITE_FIRESTORE_DB=(default)
VITE_API_URL=http://localhost:8000        # root host, without the /api/v1 prefix
```

> Backend credentials are obtained from the Firebase Console under **Project Settings → Service Accounts → Generate new private key**.

---

## Inference Engine

The `inference_engine/` package is **fully isolated**: no imports from FastAPI, Firebase, or any ORM. The only external entry point is `InferenceEngine.query(goal: Term) -> list[dict]`. The `InferenceService` (in `services/`) is solely responsible for populating the `FactBase` with Firestore data before each query.

### Implemented Rules

| ID | File | Description |
|----|------|-------------|
| RL01 | `defense_eligibility.py` | Defense eligibility (5 AND conditions) |
| RL02 | `credit_validation.py` | Credit validation by group (min/max) |
| RL03 | `academic_status.py` | Academic status: at risk (4 OR clauses) |
| RL04 | `activity_eligibility.py` | Creditable activity eligibility |
| RL05 | `production_scoring.py` | Production score weighted by venue's Qualis weight |

### Covered Inferences

**RL01 — Defense Eligibility:** a student is eligible if they have minimum credits, language proficiency, approved qualification, at least one validated bibliographic production, and a completed work plan.

**RL02 — Credit Validation:** checks minimum for the basic group (≥12), minimum for the specific group (≥8), maximum for technological activities (≤4), and total minimum (≥24).

**RL03 — Academic Status:** distinguishes regular from at-risk (overdue deadline, insufficient credits, pending qualification, or delayed plan) and identifies qualified and defense-phase students.

**RL04 — Activity Eligibility:** an activity earns credits if its type is active, it falls within the validity period, and there is no duplicate in the same period.

**RL05 — Production Scoring:** `score = base_score × qualis_weight`, applying the weight **in effect on the publication date** — Qualis weights (`A1`–`A8`) are versioned per program.

---

## AOP Aspects

Implemented using **exclusively native Python mechanisms** — no external AOP libraries.

| ID | File | Advice Type | Python Mechanism | Join Points |
|----|------|-------------|-----------------|-------------|
| A01 | `authorization.py` | Before | Decorator `@requires_role` | Endpoints that modify sensitive data |
| A02 | `audit.py` | Around | Decorator + `inspect` | All write operations |
| A03 | `history.py` | Before + After | Metaclass `HistoryMeta` | Changes to versioned entities |
| A04 | `deadline_validation.py` | Before + After | Decorator `@check_deadlines` | Operations on tasks and plans |
| A05 | `alerts.py` | After | Decorator `@trigger_alerts` | Activity validation, progress, deadlines |

> **Ownership (`ownership.py`)** — an A01 companion: the `@check_dashboard_ownership` and `@check_work_plan_ownership` decorators ensure the right to access/edit a resource comes from the **relationship** (student owner, advisor/co-advisor of the student) rather than the role alone. E.g., the work-plan kanban is editable by the student's advisor and read-only for coordination without an advising link.

### Canonical Decorator Order on Endpoints

```python
@requires_role(...)       # A01 — checks permission before
@audit_operation          # A02 — records the operation around
@check_deadlines          # A04 — validates deadlines before/after
@trigger_alerts           # A05 — dispatches alerts after
async def endpoint_func(...):
    ...
```

Flags in `aspect_config.py` allow disabling any aspect individually without modifying business logic — useful for isolated testing.

---

## Roles & Permissions

Roles are stored as **custom claims** (`role`, `programa_id`) in the Firebase Auth JWT token. The canonical `role` values are exactly `adm`, `coordenacao`, `orientador`, and `aluno`.

| Role | Main Permissions |
|------|----------------|
| `adm` | **Global** technical/institutional superuser (`programa_id: null`): creates/edits/disables coordinators in any program; sits outside every academic program |
| `coordenacao` | Full CRUD, final validation of activities/productions, reports, program settings and Qualis weights |
| `orientador` | Read advisees, create plans/tasks, issue opinions, approve progress |
| `aluno` | Own data, register activities, productions, and progress updates |

> Advising is **orthogonal** to the administrative role: a coordination who takes on advisees gets their own advisor record while remaining `coordenacao` (see [ADR-0002](./docs/adr/0002-papel-unico-com-toggle-de-visao.md)).

---

## API Routes

Base prefix: `/api/v1`

| Domain | Prefix | Main Operations |
|--------|--------|----------------|
| Authentication | `/auth` · `/health` | Login, invite, first access (password & Google), `me`, health |
| Students | `/students` | CRUD, status, qualification, proficiency, coauthors |
| Advisors | `/advisors` | CRUD, list advisees |
| Work Plan | `/work-plan` · `/stages` · `/tasks` | Stages, tasks, status, progress updates |
| Activities | `/activities` | Registration, document, opinion, validation, rejection |
| Activity Types | `/activity-types` | Scoring and limit configuration |
| Productions | `/productions` | Registration with venue and RL05 scoring |
| Vehicles | `/vehicles` | Registration and Qualis level |
| Programs | `/programs` | List and configure credit rules |
| Qualis Weights | `/qualis-weights` | Define and history of versioned weights |
| Checklist | `/checklist` | Query requirements per student |
| Extensions | `/extensions` | Request, approval, rejection |
| Requests | `/requests` | Unified requests list |
| Registration Requests | `/registration-requests` | Approve/reject new users |
| Transfers | `/transfers` · `/transfers-cross` | Advisee (direct, cross-program) |
| Coordination Transfers | `/coordination-transfers` | Coordination hand-off |
| Users | `/users` | Create coordinators, profile |
| Notifications | `/notifications` | Mark as read |
| Inference | `/inference` | Direct query to the logic engine |
| Reports | `/reports` | At-risk, by status, by advisor, time, productions |
| Dashboard | `/dashboard` | Aggregated data per role |
| Audit Logs | `/audit-logs` | Operation history |

---

## Documentation & Decisions

| Resource | Description |
|----------|-------------|
| [`CONTEXT.md`](./CONTEXT.md) | Domain model and ubiquitous language |
| [`docs/PRD.md`](./docs/PRD.md) | Product Requirements Document |
| [`docs/SDD.md`](./docs/SDD.md) | Spec-Driven Development guide |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records (0001–0009) |
| [`docs/specs/`](./docs/specs/) | 10 technical specification JSONs per module |
| [`docs/user-stories/`](./docs/user-stories/) | User stories by theme |
| [`docs/Home.md`](./docs/Home.md) | Wiki landing page |

---

## Methodology

The project uses **Kanban** on GitHub Projects with the following weekly flow:

```
Backlog → Sprint Backlog → In Progress → Done
```

### Commit Conventions

Atomic commits following Conventional Commits. Details in [`guidelines/CommitConventions.md`](./guidelines/CommitConventions.md).

```
<type>(<scope>): <short description in imperative mood>

[optional body — motivation and context]

[footer — BREAKING CHANGE or issue reference]
```

**Types:** `feat` · `fix` · `docs` · `test` · `refactor` · `chore` · `style` · `perf` · `ci`

---

## Deadlines

| Phase | Date | Time | Consequence |
|-------|------|------|-------------|
| Repository Setup | Jun 07, 2026 | 23:59 | NOk for the entire group if neglected |
| Final Submission | Jul 13, 2026 | — | Final grade |

---

## Team

### Students

| Name | GitHub |
|------|--------|
| Pietro Mendes Prauchner | [@PPrauchner](https://github.com/PPrauchner) |
| Rafael Jaques Lopes | [@rjnlopes03](https://github.com/rjnlopes03) |
| Inaurrara Flores | [@inaurrara](https://github.com/inaurrara) |
| Lorenzo Ponsci Ficher | [@lorenzoficher](https://github.com/lorenzoficher) |
| Gabriel Dornelles | [@bielGD23](https://github.com/bielGD23) |
| Gustavo dos Anjos | [@gustavodanjos](https://github.com/gustavodanjos) |

### Professors

| Name | GitHub |
|------|--------|
| Paulo Silas Severo de Souza | [@paulosevero](https://github.com/paulosevero) |
| Silvio Quincozes | [@sequincozes](https://github.com/sequincozes) |

---

<div align="center">

Project developed for the **Problem Solving III** course — UNIPAMPA, 2026.

</div>

<div align="center">

# SAGA — Academic Monitoring and Management System

[🇧🇷 Português](./README.md) · **[🇺🇸 English](./README.en.md)**

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%2B%20Auth-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica)

<br/>

> Academic project for the **Problem Solving III** course — combining **Logic Programming** (custom inference engine) and **Aspect-Oriented Programming** (native Python mechanisms) in a real graduate program management system.

[Repository](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica) · [Technical Docs](./docs/) · [Project Brief](./docs/enunciado.md)

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
- [Methodology](#methodology)
- [Deadlines](#deadlines)
- [Team](#team)

---

## About

SAGA is an academic monitoring system for **graduate programs (Master's)**, managing the full student lifecycle: enrollment, work plans, creditable activities, completion checklists, deadline extensions, and management reports.

The domain is intentionally complex — rules that cross multiple modules — making it an ideal environment to exercise two paradigms in an integrated way:

- The **logic engine** decides what is true in the system (defense eligibility, academic status, credit validation).
- The **aspects** define how each operation is intercepted and enriched (authorization, auditing, history, alerts), keeping business logic clean.

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

Implemented exclusively with **native Python mechanisms**: decorators, metaclasses, descriptors, `__init_subclass__`, and the `inspect` module. Covers the five mandatory cross-cutting concerns from the project brief, with explicitly documented join points, advices, and weaving.

---

## Architecture

```
SAGA/
├── src/                              # Frontend — React + Vite + Tailwind
│   ├── app/
│   │   ├── components/               # Pages and UI components (shadcn/ui)
│   │   │   ├── auth/                 # Login, registration, password recovery
│   │   │   ├── dashboard/            # Role-based dashboards (student, advisor, coordination)
│   │   │   ├── students/             # Student management
│   │   │   ├── activities/           # Creditable activities
│   │   │   ├── productions/          # Bibliographic productions
│   │   │   ├── checklist/            # Completion checklist
│   │   │   ├── inference/            # Logic engine visualization
│   │   │   ├── reports/              # Management reports
│   │   │   └── layout/               # Sidebar, TopBar, AppLayout
│   │   └── context/AppContext.tsx    # Global state and routing
│   ├── api/                          # Domain-scoped HTTP clients
│   ├── hooks/                        # useAuth, useNotifications
│   └── lib/firebase.ts               # Firebase SDK (Auth + Firestore)
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI + Firebase lifespan + CORS
│   │   ├── core/                     # Config, Firebase Admin SDK, auth dependency
│   │   ├── api/v1/                   # FastAPI routers per domain
│   │   ├── models/                   # Pydantic schemas
│   │   ├── services/                 # Business logic + InferenceService
│   │   ├── repositories/             # Firestore access layer
│   │   └── aspects/                  # 5 AOP aspects (A01–A05)
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
│   ├── SDD.md                        # Spec-Driven Development guide
│   └── specs/                        # 10 technical specification JSONs (01–10)
│
├── guidelines/
│   ├── Guidelines.md
│   └── CommitConventions.md          # Atomic commit conventions
│
├── .gitmessage                       # Commit template
├── pyproject.toml                    # Python config (>=3.12)
├── package.json                      # Node/React dependencies
└── vite.config.ts                    # Vite configuration
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React | 18 |
| Build Tool | Vite | 6 |
| Styling | Tailwind CSS + shadcn/ui | 4 |
| Backend | FastAPI | 0.100+ |
| Backend Language | Python | 3.12+ |
| Database | Firebase Firestore | — |
| Authentication | Firebase Auth (JWT) | — |
| Package Manager (FE) | pnpm | — |
| Testing | pytest | — |

---

## Installation & Running

### Prerequisites

- Node.js 20+ and [pnpm](https://pnpm.io/)
- Python 3.12+
- Firebase project configured ([Firebase Console](https://console.firebase.google.com/)) with Firestore + Authentication enabled

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

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -e ".[dev]"

# Run FastAPI server (http://localhost:8000)
uvicorn backend.app.main:app --reload --port 8000

# Run inference engine tests
pytest backend/inference_engine/tests/ -v

# Seed Firestore (run once)
python backend/scripts/seed_firestore.py
```

### Health Check

```
GET http://localhost:8000/api/v1/health
```

---

## Environment Variables

Create a `.env` file at the project root:

```env
# Backend — Firebase Admin SDK
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=

# Frontend — Firebase SDK (Vite)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_PROJECT_ID=
VITE_AUTH_DOMAIN=
VITE_FIRESTORE_DB=
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
| RL05 | `production_scoring.py` | Production score weighted by venue level |

### Covered Inferences

**RL01 — Defense Eligibility:** a student is eligible if they have minimum credits, language proficiency, approved qualification, at least one validated bibliographic production, and a completed work plan.

**RL02 — Credit Validation:** checks minimum by basic group, minimum by specific group, and maximum for technological activities.

**RL03 — Academic Status:** distinguishes regular from at-risk (overdue deadline, insufficient credits, pending qualification, or delayed plan) and identifies qualified and defense-phase students.

**RL04 — Activity Eligibility:** an activity earns credits if it falls within the program period, has a supporting document, has an active type, and does not exceed the category limit.

**RL05 — Production Scoring:** weights the score by the venue's relevance level, configurable per program.

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

Roles are stored as **custom claims** (`role`, `programa_id`) in the Firebase Auth JWT token.

| Role | Main Permissions |
|------|----------------|
| `coordenacao` | Full CRUD, activity validation, reports, program settings |
| `orientador` | Read advisees, create plans/tasks, issue opinions |
| `aluno` | Own data, register activities, productions, and progress updates |

---

## API Routes

Base prefix: `/api/v1`

| Domain | Prefix | Main Operations |
|--------|--------|----------------|
| Authentication | `/auth` | Login, invite, first access, password reset |
| Students | `/students` | CRUD, status, inferred situation |
| Advisors | `/advisors` | CRUD, list advisees |
| Work Plan | `/work-plan` | Stages, tasks, progress updates |
| Activities | `/activities` | Registration, validation, rejection |
| Activity Types | `/activity-types` | Scoring and limit configuration |
| Productions | `/productions` | Registration with venue and RL05 scoring |
| Vehicles | `/vehicles` | Registration and relevance level |
| Checklist | `/checklist` | Query requirements per student |
| Extensions | `/extensions` | Request, opinion, and approval |
| Inference | `/inference` | Direct query to the logic engine |
| Reports | `/reports` | Overdue students, production, avg time |
| Dashboard | `/dashboard` | Aggregated data per role |
| Audit Logs | `/audit-logs` | Operation history (coordination only) |

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

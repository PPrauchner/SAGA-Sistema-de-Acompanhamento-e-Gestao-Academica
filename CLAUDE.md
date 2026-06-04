# CLAUDE.md — SAGA

Sistema de Acompanhamento e Gestão Acadêmica (SAGA) para programas de
pós-graduação. Gerencia discentes, planos de trabalho, atividades
creditáveis, produções bibliográficas e prorrogações. Dois paradigmas
obrigatórios: **motor de inferência lógica** (Python puro) e **AOP**
(decoradores/metaclasses nativos do Python).

---

## Arquitetura

```
raiz/
├── src/                        # Frontend React + Vite + Tailwind
│   ├── app/
│   │   ├── components/         # Páginas e componentes UI (shadcn/ui)
│   │   └── context/AppContext  # Estado global e roteamento
│   ├── api/                    # Clientes HTTP por domínio
│   ├── hooks/                  # useAuth, useNotifications
│   ├── lib/firebase.ts         # Firebase SDK (Auth + Firestore)
│   └── styles/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI + lifespan Firebase
│   │   ├── core/               # config, firebase admin, auth dependency
│   │   ├── api/v1/             # Routers FastAPI por domínio
│   │   ├── models/             # Pydantic schemas
│   │   ├── services/           # Lógica de negócio (+ inference_service)
│   │   ├── repositories/       # Acesso ao Firestore
│   │   └── aspects/            # 5 aspectos AOP
│   ├── inference_engine/       # Motor lógico isolado (sem imports externos)
│   │   ├── terms.py            # Atom, Variable, Compound
│   │   ├── unification.py      # unify()
│   │   ├── substitution.py     # apply()
│   │   ├── resolver.py         # solve() — sem backtracking
│   │   ├── knowledge_base.py   # FactBase + RuleBase + InferenceEngine
│   │   ├── rules/              # RL01–RL05 (módulos declarativos)
│   │   └── tests/              # pytest — 5 arquivos, sem __init__.py
│   └── scripts/seed_firestore.py
├── docs/specs/                 # 10 JSONs de especificação técnica
├── guidelines/
│   ├── Guidelines.md
│   └── CommitConventions.md    # Template e regras de commit
├── .gitmessage                 # Template git: git config commit.template .gitmessage
└── CLAUDE.md                   # este arquivo
```

---

## Comandos

### Frontend
```bash
# Instalar dependências
pnpm install

# Desenvolvimento
pnpm dev          # Vite dev server em http://localhost:5173

# Build
pnpm build
```

### Backend
```bash
# Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# Instalar dependências (após definir pyproject.toml)
pip install -e ".[dev]"

# Rodar o servidor FastAPI
uvicorn backend.app.main:app --reload --port 8000

# Rodar testes do motor de inferência
pytest backend/inference_engine/tests/ -v

# Seed do Firestore (executar uma vez)
python backend/scripts/seed_firestore.py
```

### Variáveis de ambiente
Criar `.env` na raiz com:
```
# Backend
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=

# Frontend (Vite)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_PROJECT_ID=
VITE_AUTH_DOMAIN=
VITE_FIRESTORE_DB=
```

---

## Motor de Inferência — Regras de Isolamento

O `inference_engine/` é **completamente isolado**:
- Sem imports de FastAPI, Firebase, pydantic ou qualquer ORM
- Único ponto de entrada externo: `InferenceEngine.query(goal: Term) -> list[dict]`
- `InferenceService` (em `services/`) é o único responsável por popular a
  `FactBase` com dados do Firestore antes de cada consulta
- Para adicionar/alterar uma regra de negócio: editar apenas o arquivo
  correspondente em `rules/` (RL01–RL05), não a lógica de controle

### Regras implementadas
| ID   | Arquivo                  | Descrição                             |
|------|--------------------------|---------------------------------------|
| RL01 | `defense_eligibility.py` | Aptidão à defesa (5 condições AND)    |
| RL02 | `credit_validation.py`   | Créditos por grupo (mín/máx)          |
| RL03 | `academic_status.py`     | Em risco (4 cláusulas OR, sem NAF)    |
| RL04 | `activity_eligibility.py`| Elegibilidade de atividade creditável |
| RL05 | `production_scoring.py`  | Pontuação ponderada por veículo       |

---

## Aspectos AOP

Implementados com mecanismos nativos do Python — sem bibliotecas externas.

| ID  | Arquivo                  | Tipo         | Mecanismo Python          |
|-----|--------------------------|--------------|---------------------------|
| A01 | `authorization.py`       | Before       | Decorador `@requires_role`|
| A02 | `audit.py`               | Around       | Decorador + `inspect`     |
| A03 | `history.py`             | Before+After | Metaclasse `HistoryMeta`  |
| A04 | `deadline_validation.py` | Before+After | Decorador `@check_deadlines`|
| A05 | `alerts.py`              | After        | Decorador `@trigger_alerts`|

Ordem canônica de decoradores nos endpoints:
```python
@requires_role(...)
@audit_operation
@check_deadlines
@trigger_alerts
async def endpoint_func(...):
```

Flags para desabilitar aspectos em teste: `aspect_config.py`.

---

## Firebase / Firestore

- **Auth**: custom claims `{ role, programa_id }` em cada token JWT
- **Escrita**: exclusivamente via Admin SDK no backend
- **Leitura direta no frontend**: apenas `notifications/` (onSnapshot)
- **Coleções principais**: `users`, `students`, `advisors`, `activity_types`,
  `vehicles`, `programs`, `audit_logs`, `notifications`, `invites`
- **Sub-coleções**: `students/{id}/work_plan`, `/activities`, `/productions`,
  `/extensions`, `/inferred_status`, `/history`

---

## Papéis e Permissões

| Papel         | Permissões principais                                       |
|---------------|-------------------------------------------------------------|
| `coordenacao` | CRUD completo, validação final, relatórios, configurações   |
| `orientador`  | Leitura de orientandos, criar plano/tasks, emitir pareceres |
| `aluno`       | Próprios dados, registrar atividades/produções/progresso    |

---

## Convenções de Código

- **Python**: docstrings em todos os módulos; tipagem explícita; sem lógica
  nos arquivos de rota (delegar para services)
- **TypeScript**: um arquivo de API por domínio em `src/api/`; hooks em
  `src/hooks/`; alias `@` aponta para `src/`
- **Commits**: atômicos, seguir template em `guidelines/CommitConventions.md`
- **Testes**: pytest para o motor de inferência; cobertura obrigatória de
  todos os cenários apto/risco/inapto das 5 regras

---

## Especificações Técnicas

Documentação detalhada de cada módulo em `docs/specs/`:

| Arquivo                         | Conteúdo                              |
|---------------------------------|---------------------------------------|
| `01_motor_inferencia.json`      | Motor lógico completo + casos de teste|
| `02_aspectos_aop.json`          | 5 aspectos com join points e advice   |
| `03_firebase_schema.json`       | Schema Firestore + mapeamento páginas |
| `04_autenticacao.json`          | Firebase Auth + fluxo de convite      |
| `05_discentes.json`             | CRUD alunos e orientadores            |
| `06_plano_trabalho.json`        | Plano, etapas, tasks e progresso      |
| `07_atividades_producoes.json`  | Fluxo de validação + RL04/RL05        |
| `08_checklist_prorrogacoes.json`| Checklist + prorrogações              |
| `09_relatorios_dashboard.json`  | Dashboards e relatórios               |
| `10_integracao_frontend.json`   | Substituição dos dados hardcoded      |

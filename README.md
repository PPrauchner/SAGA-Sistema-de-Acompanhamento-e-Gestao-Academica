<div align="center">

# SAGA — Sistema de Acompanhamento e Gestão Acadêmica

**[🇧🇷 Português](./README.md)** · [🇺🇸 English](./README.en.md)

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%2B%20Auth%20%2B%20Storage-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Status](https://img.shields.io/badge/Status-MVP%20Conclu%C3%ADdo-brightgreen)](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica)

<br/>

> Projeto acadêmico para a disciplina de **Resolução de Problemas III** — combina **Programação Lógica** (motor de inferência próprio) e **Programação Orientada a Aspectos** (mecanismos nativos do Python) em um sistema real de gerenciamento de pós-graduação.

[Repositório](https://github.com/PPrauchner/SAGA-Sistema-de-Acompanhamento-e-Gestao-Academica) · [Documentação Técnica](./docs/) · [Wiki](./docs/Home.md) · [Enunciado](./docs/enunciado.md)

</div>

---

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Paradigmas Implementados](#paradigmas-implementados)
- [Arquitetura](#arquitetura)
- [Stack de Tecnologia](#stack-de-tecnologia)
- [Instalação e Execução](#instalação-e-execução)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Motor de Inferência](#motor-de-inferência)
- [Aspectos AOP](#aspectos-aop)
- [Papéis e Permissões](#papéis-e-permissões)
- [Rotas da API](#rotas-da-api)
- [Documentação e Decisões](#documentação-e-decisões)
- [Metodologia](#metodologia)
- [Prazos](#prazos)
- [Equipe](#equipe)

---

## Sobre o Projeto

O SAGA é um sistema de acompanhamento acadêmico para programas de **mestrado**, gerenciando o ciclo completo do discente: desde o cadastro e o plano de trabalho até a validação de créditos, checklist de integralização, prorrogações, transferências e relatórios gerenciais.

O domínio é propositalmente complexo — regras que se cruzam em múltiplos módulos — o que o torna o ambiente ideal para exercitar dois paradigmas de forma integrada:

- O **motor lógico** decide o que é verdade no sistema (aptidão à defesa, situação acadêmica, elegibilidade de créditos).
- Os **aspectos** definem como cada operação é interceptada e enriquecida (autorização, auditoria, histórico, alertas), mantendo a lógica de negócio limpa.

> Para o modelo de domínio completo (entidades, linguagem ubíqua, regras de negócio), ver [`CONTEXT.md`](./CONTEXT.md).

### Estados do Discente

| Status | Descrição |
|--------|-----------|
| 🟢 Regular | Dentro do prazo, plano em dia |
| 🔄 Em Prorrogação | Semestre adicional concedido e em curso |
| 🔴 Em Risco | Pendências ou prazos estourados |
| ✅ Qualificado | Aprovado na qualificação |
| 📝 Em Fase de Defesa | Apto à defesa e com a defesa encaminhada |
| 🎓 Concluído | Integralizou o curso e defendeu |
| ❌ Desligado | Removido do programa |

---

## Paradigmas Implementados

### Programação Lógica — Motor de Inferência

Motor construído **do zero em Python puro**, sem bibliotecas externas de programação lógica. Implementa:

- Representação de termos (`Atom`, `Variable`, `Compound`)
- Algoritmo de **unificação**
- **Substituições** como dicionário variável → valor
- **Resolução de consultas** (conjunção de condições, sem backtracking)
- Base de fatos e base de regras separadas do mecanismo de resolução

As decisões acadêmicas são expressas como **regras declarativas** — mudar uma política significa alterar a regra, não reescrever fluxo de código.

### Programação Orientada a Aspectos

Implementada exclusivamente com **mecanismos nativos do Python**: decoradores, metaclasses, descritores, `__init_subclass__` e o módulo `inspect`. Cobre as cinco preocupações transversais obrigatórias do enunciado (A01–A05), com join points, advices e weaving explicitamente documentados nos docstrings de cada módulo.

---

## Arquitetura

```
SAGA/
├── src/                              # Frontend — React + Vite + Tailwind
│   ├── app/
│   │   ├── components/               # Páginas e componentes UI (shadcn/ui + MUI)
│   │   │   ├── auth/                 # Login, primeiro acesso, recuperação de senha
│   │   │   ├── dashboard/            # Dashboards por papel (aluno, orientador, coordenação)
│   │   │   ├── students/             # Gestão de discentes
│   │   │   ├── advisors/             # Gestão de orientadores
│   │   │   ├── workplan/             # Plano de trabalho / kanban (react-dnd)
│   │   │   ├── activities/           # Atividades creditáveis
│   │   │   ├── productions/          # Produções bibliográficas
│   │   │   ├── checklist/            # Checklist de integralização
│   │   │   ├── requests/             # Solicitações (prorrogação, trancamento, transferência)
│   │   │   ├── extensions/           # Prorrogações
│   │   │   ├── registration-requests/ # Pedidos de cadastro
│   │   │   ├── transfers/            # Transferências de orientando / coordenação
│   │   │   ├── departments/          # Departamentos (gestão pelo adm)
│   │   │   ├── inference/            # Visualização do motor lógico
│   │   │   ├── reports/              # Relatórios gerenciais (Recharts)
│   │   │   ├── export/               # Exportação de relatórios
│   │   │   ├── notifications/        # Central de notificações
│   │   │   ├── settings/            # Configurações de programa e pesos Qualis
│   │   │   ├── audit/               # Log de auditoria
│   │   │   └── layout/               # Sidebar, TopBar, AppLayout
│   │   ├── context/AppContext.tsx    # Estado global
│   │   └── router/PrivateRoute.tsx   # Rotas protegidas (react-router)
│   ├── api/                          # Clientes HTTP por domínio
│   ├── hooks/                        # useAuth, useNotifications, useDashboard, …
│   └── lib/firebase.ts               # Firebase SDK (Auth + Firestore)
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI + lifespan Firebase + CORS
│   │   ├── core/                     # Config, Firebase Admin SDK, auth, e-mail
│   │   ├── api/v1/                   # Routers FastAPI por domínio (+ tests/)
│   │   ├── models/                   # Schemas Pydantic
│   │   ├── services/                 # Lógica de negócio + InferenceService
│   │   ├── repositories/             # Acesso ao Firestore + Storage
│   │   └── aspects/                  # Aspectos AOP (A01–A05 + ownership)
│   │       └── aspect_config.py      # Flags para ativar/desativar aspectos
│   │
│   ├── inference_engine/             # Motor lógico — isolado, sem imports externos
│   │   ├── terms.py                  # Atom, Variable, Compound
│   │   ├── unification.py            # unify()
│   │   ├── substitution.py           # apply()
│   │   ├── resolver.py               # solve() — sem backtracking
│   │   ├── knowledge_base.py         # FactBase + RuleBase + InferenceEngine
│   │   ├── rules/                    # RL01–RL05 (módulos declarativos)
│   │   └── tests/                    # pytest — cobertura das 5 regras
│   │
│   └── scripts/seed_firestore.py     # Seed inicial do Firestore
│
├── docs/
│   ├── enunciado.md                  # Enunciado completo do projeto
│   ├── PRD.md · SDD.md               # Product Requirements + Spec-Driven Development
│   ├── CONTEXT.md → (raiz)           # Modelo de domínio / linguagem ubíqua
│   ├── adr/                          # Architecture Decision Records (0001–0009)
│   ├── user-stories/                 # Histórias de usuário por tema
│   ├── specs/                        # 10 JSONs de especificação técnica (01–10)
│   └── Home.md                       # Página inicial da Wiki
│
├── guidelines/                       # Guidelines + convenções de commit
├── pyproject.toml · uv.lock          # Configuração Python (uv, >=3.12)
├── package.json · vite.config.ts     # Frontend (pnpm)
└── .env.example                      # Modelo de variáveis de ambiente
```

> Árvore completa das camadas do backend em [`.claude/rules/architecture.md`](./.claude/rules/architecture.md).

---

## Stack de Tecnologia

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Frontend | React | 18 |
| Build Tool | Vite | 6 |
| Estilização | Tailwind CSS + shadcn/ui + MUI | 4 / — / 7 |
| Roteamento | react-router | 7 |
| Gráficos / Kanban | Recharts · react-dnd | — |
| Backend | FastAPI | 0.100+ |
| Linguagem Back | Python | 3.12+ |
| Banco de Dados | Firebase Firestore | — |
| Armazenamento | Firebase Storage (comprovantes) | — |
| Autenticação | Firebase Auth (JWT + custom claims) | — |
| Gerenciador de Pacotes (BE) | uv | — |
| Gerenciador de Pacotes (FE) | pnpm | — |
| Testes | pytest + pytest-asyncio | — |

---

## Instalação e Execução

### Pré-requisitos

- Node.js 20+ e [pnpm](https://pnpm.io/)
- Python 3.12+ e [uv](https://docs.astral.sh/uv/)
- Projeto configurado no [Firebase Console](https://console.firebase.google.com/) (Firestore + Authentication + Storage)

### Frontend

```bash
# Instalar dependências
pnpm install

# Servidor de desenvolvimento (http://localhost:5173)
pnpm dev

# Build de produção
pnpm build
```

### Backend

Gerenciado com **uv** (ver `uv.lock`); requer **Python ≥ 3.12**.

```bash
# Instalar dependências (cria .venv automaticamente)
uv sync

# Rodar o servidor FastAPI (http://localhost:8000)
uv run uvicorn backend.app.main:app --reload --port 8000

# Rodar testes do motor de inferência
uv run pytest backend/inference_engine/tests/ -v

# Lint e format (ruff)
uv run ruff check .
uv run ruff format .

# Seed inicial do Firestore (executar uma vez)
uv run python backend/scripts/seed_firestore.py
```

> **Alternativa sem uv:** `python -m venv .venv` → ativar (`source .venv/bin/activate` no Linux/macOS, `.venv\Scripts\activate` no Windows) → `pip install -e ".[dev]"`.

### Health Check

```
GET http://localhost:8000/api/v1/health
```

---

## Variáveis de Ambiente

Copiar [`.env.example`](./.env.example) para `.env` na raiz do projeto e preencher:

```env
# Backend — Firebase Admin SDK
FIREBASE_PROJECT_ID=
FIREBASE_PRIVATE_KEY=
FIREBASE_CLIENT_EMAIL=
FIREBASE_STORAGE_BUCKET=

# API
API_VERSION=1.0.0-MVP
CORS_ORIGINS=["http://localhost:5173"]   # array JSON, não vírgula-separado
FRONTEND_URL=http://localhost:5173       # base para o link de primeiro acesso

# E-mail (convite de primeiro acesso) — qualquer servidor SMTP
EMAIL_PROVIDER=smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@saga.local
SMTP_USE_TLS=true
EXPOSE_INVITE_TOKEN=true                  # false em produção

# Frontend — Firebase SDK (Vite)
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_PROJECT_ID=
VITE_AUTH_DOMAIN=
VITE_FIRESTORE_DB=(default)
VITE_API_URL=http://localhost:8000        # host raiz, sem o prefixo /api/v1
```

> As credenciais do Firebase Admin SDK (backend) são obtidas no Console do Firebase em **Configurações do Projeto → Contas de Serviço → Gerar nova chave privada**.

---

## Motor de Inferência

O `inference_engine/` é **completamente isolado**: sem imports de FastAPI, Firebase ou qualquer ORM. O único ponto de entrada externo é `InferenceEngine.query(goal: Term) -> list[dict]`. O `InferenceService` (em `services/`) é o único responsável por popular a `FactBase` com dados do Firestore antes de cada consulta.

### Regras Implementadas

| ID | Arquivo | Descrição |
|----|---------|-----------|
| RL01 | `defense_eligibility.py` | Aptidão à defesa (5 condições AND) |
| RL02 | `credit_validation.py` | Validação de créditos por grupo (mín/máx) |
| RL03 | `academic_status.py` | Situação acadêmica: em risco (4 cláusulas OR) |
| RL04 | `activity_eligibility.py` | Elegibilidade de atividade creditável |
| RL05 | `production_scoring.py` | Pontuação ponderada por peso Qualis do veículo |

### Inferências Cobertas

**RL01 — Aptidão à Defesa:** um aluno está apto se possui créditos mínimos, proficiência, qualificação aprovada, ao menos uma produção bibliográfica validada e plano concluído.

**RL02 — Validação de Créditos:** verifica mínimo por grupo básico (≥12), mínimo por grupo específico (≥8), máximo por atividade tecnológica (≤4) e mínimo total (≥24).

**RL03 — Situação Acadêmica:** distingue regular de em risco (prazo estourado, créditos insuficientes, qualificação pendente ou plano atrasado) e identifica qualificado e em fase de defesa.

**RL04 — Elegibilidade de Atividade:** uma atividade gera crédito se o tipo estiver ativo, estiver dentro do período de validade e não houver duplicata no mesmo período.

**RL05 — Pontuação de Produção:** `score = pontuação_base × peso_qualis`, aplicando o peso **vigente na data de publicação** — os pesos Qualis (`A1`–`A8`) são versionados por programa.

---

## Aspectos AOP

Implementados com mecanismos **exclusivamente nativos do Python** — sem bibliotecas externas de orientação a aspectos.

| ID | Arquivo | Tipo de Advice | Mecanismo Python | Join Points |
|----|---------|---------------|-----------------|-------------|
| A01 | `authorization.py` | Before | Decorador `@requires_role` | Endpoints que alteram dados sensíveis |
| A02 | `audit.py` | Around | Decorador + `inspect` | Todas as operações de escrita |
| A03 | `history.py` | Before + After | Metaclasse `HistoryMeta` | Alterações em entidades versionáveis |
| A04 | `deadline_validation.py` | Before + After | Decorador `@check_deadlines` | Operações sobre tasks e planos |
| A05 | `alerts.py` | After | Decorador `@trigger_alerts` | Validação de atividades, progresso, prazos |

> **Ownership (`ownership.py`)** — companheiro do A01: decoradores `@check_dashboard_ownership` e `@check_work_plan_ownership` garantem que o direito de acessar/editar um recurso venha do **vínculo** (aluno dono, orientador/coorientador do aluno) e não apenas do papel. Ex.: o kanban do plano de trabalho é editável pelo orientador do aluno e read-only para a coordenação sem vínculo de orientação.

### Ordem Canônica nos Endpoints

```python
@requires_role(...)       # A01 — verifica permissão antes
@audit_operation          # A02 — registra a operação ao redor
@check_deadlines          # A04 — valida prazos antes/depois
@trigger_alerts           # A05 — dispara alertas após
async def endpoint_func(...):
    ...
```

As flags em `aspect_config.py` permitem desabilitar qualquer aspecto individualmente sem alterar a lógica de negócio — útil para testes isolados.

---

## Papéis e Permissões

Os papéis são armazenados como **custom claims** (`role`, `programa_id`) no token JWT do Firebase Auth. Os valores canônicos de `role` são exatamente `adm`, `coordenacao`, `orientador` e `aluno`.

| Papel | Permissões Principais |
|-------|----------------------|
| `adm` | Superusuário técnico/institucional **global** (`programa_id: null`): cria/edita/desativa coordenadores em qualquer programa; fora de todo programa acadêmico |
| `coordenacao` | CRUD completo, validação final de atividades/produções, relatórios, configurações do programa e pesos Qualis |
| `orientador` | Leitura de orientandos, criação de plano/tasks, emissão de pareceres, aprovação de progresso |
| `aluno` | Próprios dados, registro de atividades, produções e atualizações de progresso |

> Orientar é **ortogonal** ao papel administrativo: uma coordenação que assume orientandos ganha um registro de orientador próprio, sem deixar de ser `coordenacao` (ver [ADR-0002](./docs/adr/0002-papel-unico-com-toggle-de-visao.md)).

---

## Rotas da API

Prefixo base: `/api/v1`

| Domínio | Prefixo | Operações Principais |
|---------|---------|---------------------|
| Autenticação | `/auth` · `/health` | Login, convite, primeiro acesso (senha e Google), `me`, health |
| Discentes | `/students` | CRUD, situação, qualificação, proficiência, coautores |
| Orientadores | `/advisors` | CRUD, listagem de orientandos |
| Plano de Trabalho | `/work-plan` · `/stages` · `/tasks` | Etapas, tasks, status, atualizações de progresso |
| Atividades | `/activities` | Registro, comprovante, parecer, validação, rejeição |
| Tipos de Atividade | `/activity-types` | Configuração de pontuação e limites |
| Produções | `/productions` | Registro com veículo e pontuação RL05 |
| Veículos | `/vehicles` | Cadastro e nível Qualis |
| Programas | `/programs` | Listagem e configuração de regras de crédito |
| Pesos Qualis | `/qualis-weights` | Definição e histórico de pesos versionados |
| Checklist | `/checklist` | Consulta de requisitos por aluno |
| Prorrogações | `/extensions` | Solicitação, aprovação, rejeição |
| Solicitações | `/requests` | Lista unificada de solicitações |
| Pedidos de Cadastro | `/registration-requests` | Aprovação/rejeição de novos usuários |
| Transferências | `/transfers` · `/transfers-cross` | Orientando (direta, cross-programa) |
| Transf. de Coordenação | `/coordination-transfers` | Hand-off de coordenação |
| Usuários | `/users` | Criação de coordenadores, perfil |
| Notificações | `/notifications` | Marcar como lida |
| Inferência | `/inference` | Consulta direta ao motor lógico |
| Relatórios | `/reports` | Em risco, por status, por orientador, tempo, produções |
| Dashboard | `/dashboard` | Dados agregados por papel |
| Auditoria | `/audit-logs` | Histórico de operações |

---

## Documentação e Decisões

| Recurso | Descrição |
|---------|-----------|
| [`CONTEXT.md`](./CONTEXT.md) | Modelo de domínio e linguagem ubíqua |
| [`docs/PRD.md`](./docs/PRD.md) | Product Requirements Document |
| [`docs/SDD.md`](./docs/SDD.md) | Guia de Spec-Driven Development |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records (0001–0009) |
| [`docs/specs/`](./docs/specs/) | 10 JSONs de especificação técnica por módulo |
| [`docs/user-stories/`](./docs/user-stories/) | Histórias de usuário por tema |
| [`docs/Home.md`](./docs/Home.md) | Página inicial da Wiki |

---

## Metodologia

O projeto utiliza **Kanban** no GitHub Projects com o seguinte fluxo semanal:

```
Backlog → Sprint Backlog → Em Progresso → Feito
```

### Convenções de Commit

Commits atômicos seguindo Conventional Commits. Detalhes em [`guidelines/CommitConventions.md`](./guidelines/CommitConventions.md).

```
<tipo>(<escopo>): <descrição curta no imperativo>

[corpo opcional — motivação e contexto]

[rodapé — BREAKING CHANGE ou referência a issue]
```

**Tipos:** `feat` · `fix` · `docs` · `test` · `refactor` · `chore` · `style` · `perf` · `ci`

---

## Prazos

| Fase | Data | Hora | Consequência |
|------|------|------|-------------|
| Setup do Repositório | 07/06/2026 | 23h59 | NOk para todo o grupo se negligenciado |
| Entrega Final | 13/07/2026 | — | Conceito final |

---

## Equipe

### Discentes

| Nome | GitHub |
|------|--------|
| Pietro Mendes Prauchner | [@PPrauchner](https://github.com/PPrauchner) |
| Rafael Jaques Lopes | [@rjnlopes03](https://github.com/rjnlopes03) |
| Inaurrara Flores | [@inaurrara](https://github.com/inaurrara) |
| Lorenzo Ponsci Ficher | [@lorenzoficher](https://github.com/lorenzoficher) |
| Gabriel Dornelles | [@bielGD23](https://github.com/bielGD23) |
| Gustavo dos Anjos | [@gustavodanjos](https://github.com/gustavodanjos) |

### Professores

| Nome | GitHub |
|------|--------|
| Paulo Silas Severo de Souza | [@paulosevero](https://github.com/paulosevero) |
| Silvio Quincozes | [@sequincozes](https://github.com/sequincozes) |

---

<div align="center">

Projeto desenvolvido para a disciplina de **Resolução de Problemas III** — UNIPAMPA, 2026.

</div>

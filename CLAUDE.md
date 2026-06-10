# CLAUDE.md — SAGA

Instruções de desenvolvimento para o SAGA — Sistema de Acompanhamento e Gestão Acadêmica.

> Para entender o **domínio do problema** (entidades, ciclo de vida do discente, regras acadêmicas, papéis), ver [`CONTEXT.md`](./CONTEXT.md).

---

## Skills e Regras de Comportamento

@.claude/rules/karpathy-principles.md

> As regras específicas de backend e frontend são carregadas automaticamente
> via .claude/rules/backend.md e .claude/rules/frontend.md quando o Claude
> abre arquivos em backend/ ou src/.

## Arquitetura

Ver [`.claude/rules/architecture.md`](./.claude/rules/architecture.md) para a árvore completa de arquivos e camadas do backend.

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

Ver descrições de domínio em [`CONTEXT.md → Regras Acadêmicas`](./CONTEXT.md#regras-acadêmicas-motor-de-inferência).

| ID   | Arquivo                    |
|------|----------------------------|
| RL01 | `defense_eligibility.py`   |
| RL02 | `credit_validation.py`     |
| RL03 | `academic_status.py`       |
| RL04 | `activity_eligibility.py`  |
| RL05 | `production_scoring.py`    |

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

Ver coleções e entidades em [`CONTEXT.md → Modelo de Dados`](./CONTEXT.md#modelo-de-dados-coleções-firestore).

Regras de acesso:
- **Auth**: custom claims `{ role, programa_id }` em cada token JWT
- **Escrita**: exclusivamente via Admin SDK no backend
- **Leitura direta no frontend**: apenas `notifications/` (onSnapshot)

---

---

## Convenções de Código

Ver [`.claude/rules/code-conventions.md`](./.claude/rules/code-conventions.md) para: docstrings Google Style, type hints Python 3.10+, restrições do enunciado (isolamento do motor, AOP, routers), convenções TypeScript e Clean Code.

Resumo das regras críticas:
- **inference_engine/**: isolado, sem imports externos, ponto de entrada único `InferenceEngine.query()`
- **Aspectos**: sem bibliotecas externas; documentar Join Point, Advice e Weaving em cada docstring
- **Routers**: apenas receber request → chamar service → retornar response; sem lógica de negócio
- **Commits**: atômicos, seguir `guidelines/CommitConventions.md`; testes **sempre** em commit separado da implementação (`feat`/`fix` primeiro, `test` depois)
- **Testes**: pytest, cobrir todos os cenários apto/risco/inapto das 5 regras
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

---

## Workflow de Issues (GitHub Projects)

### Ao iniciar trabalho em uma issue

O **primeiro comando obrigatório** ao começar qualquer issue é registrá-la:

```bash
echo "NUMERO_DA_ISSUE" > .claude/current-issue
```

Substitua `NUMERO_DA_ISSUE` pelo número real (ex: `echo "42" > .claude/current-issue`).
Esse arquivo é lido automaticamente pelo hook ao abrir o PR.

### Quando o usuário confirmar que o trabalho está pronto

1. Faça commit de tudo seguindo `guidelines/CommitConventions.md`
2. Abra o PR com:

```bash
gh pr create \
  --title "tipo: descrição curta (#NUMERO)" \
  --body "Closes #NUMERO" \
  --base main
```

O hook `.claude/hooks/post-bash.sh` detecta o `gh pr create` automaticamente
e move a issue para **In Review** no GitHub Projects (projeto #4).

### Regras Gerais

ver descrições de regras gerais em [`CONTEXT.md → Regras Gerais`]

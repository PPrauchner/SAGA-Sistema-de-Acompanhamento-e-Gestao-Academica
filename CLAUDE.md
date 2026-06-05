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

### Regras

- Nunca abra PR sem ter o `.claude/current-issue` preenchido — o hook não saberá qual issue mover.
- O arquivo `.claude/current-issue` é ignorado pelo git (listado no `.gitignore`).
- Se a issue não estiver vinculada ao projeto #4, o hook avisará mas não falhará.

---

## Comportamento Obrigatório (leia antes de qualquer tarefa)

### 1. Fluxo SDD — spec antes de código

Antes de implementar qualquer feature ou modificar lógica de negócio:
1. Identifique o(s) spec(s) correspondente(s) em `docs/specs/`
2. Leia o spec completo com `Read`
3. Se houver ambiguidade entre o spec e o código existente, pergunte antes de assumir
4. Ao terminar, compare a implementação com o spec e liste divergências

Mapeamento rápido de domínio → spec:

| Domínio                        | Spec                              |
|--------------------------------|-----------------------------------|
| Motor de inferência / regras   | `01_motor_inferencia.json`        |
| Aspectos AOP                   | `02_aspectos_aop.json`            |
| Firestore / schema             | `03_firebase_schema.json`         |
| Autenticação / convites        | `04_autenticacao.json`            |
| Discentes / orientadores       | `05_discentes.json`               |
| Plano de trabalho              | `06_plano_trabalho.json`          |
| Atividades / produções         | `07_atividades_producoes.json`    |
| Checklist / prorrogações       | `08_checklist_prorrogacoes.json`  |
| Relatórios / dashboard         | `09_relatorios_dashboard.json`    |
| Integração frontend            | `10_integracao_frontend.json`     |

### 2. Uma issue por sessão

Mantenha o foco em uma única issue por conversa. Se perceber que a tarefa
envolve múltiplos domínios não relacionados, sinalize ao usuário e sugira
quebrar em issues separadas.

### 3. Commits atômicos durante o trabalho

Não acumule mudanças em áreas diferentes sem commitar. A cada etapa lógica
concluída (ex: spec lido + modelo criado, ou endpoint implementado + teste
passando), faça um commit seguindo `guidelines/CommitConventions.md`.

**Critérios para atomicidade — um commit deve ter UMA responsabilidade lógica:**

- **Uma camada por commit**: não misture mudanças em `models/`, `services/` e
  `api/v1/` no mesmo commit, mesmo que todas sejam do mesmo domínio.
- **Dependências e config separados do código funcional**: alterações em
  `pyproject.toml`, `.env.example`, variáveis de ambiente ou arquivos de
  configuração devem ser commits independentes, não agrupados com features.
- **Scaffolding separado de implementação**: criar a estrutura de um arquivo
  (ex: `router = APIRouter()` em stubs) é um commit; implementar a lógica
  de um endpoint é outro commit.
- **Um domínio por commit**: alterações que tocam `students/` e `activities/`
  ao mesmo tempo devem ser dois commits, salvo se a mudança for exclusivamente
  transversal (ex: renomear um campo compartilhado).
- **Teste junto com o código que ele testa**: o teste de uma função vai no
  mesmo commit da função, não depois.

**Exemplos corretos para inicialização de um módulo backend:**
```
chore(backend): adiciona fastapi, pydantic-settings, firebase-admin ao pyproject.toml
feat(backend/config): implementa Settings com pydantic-settings e cria .env.example
feat(backend/firebase): stub de inicialização do Admin SDK
feat(backend/core): inicializa app FastAPI com CORS, lifespan e registro de routers
feat(backend/health): GET /api/v1/health retornando status da API e do Firebase
```

**Sinal de alerta**: se a mensagem de commit precisar de mais de uma frase no
corpo para descrever *o que* foi feito (não *por que*), o commit provavelmente
deve ser dividido.

### 4. Nunca quebre os testes do inference_engine

O motor de inferência é isolado e tem testes obrigatórios. Após qualquer
alteração em `backend/inference_engine/`, rode:
```bash
pytest backend/inference_engine/tests/ -v
```
Não prossiga se algum teste falhar.


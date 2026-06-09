# Arquitetura — SAGA

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
├── docs/
│   ├── specs/                  # 10 JSONs de especificação técnica
│   └── agents/                 # Referências para agent skills
│       ├── architecture.md     # este arquivo
│       ├── code-conventions.md # Docstrings, type hints, restrições
├── guidelines/
│   ├── Guidelines.md
│   └── CommitConventions.md    # Template e regras de commit
├── .claude/
│   ├── commands/               # Slash commands (/commit, /tdd, etc.)
│   │   └── workflow/           # Commands do workflow SAGA
│   └── skills/                 # Agent skills (carregadas autonomamente)
│       ├── engineering/        # tdd, diagnose, to-prd, to-issues, etc.
│       └── productivity/       # grill-me, handoff, teach, etc.
├── .gitmessage                 # Template git
├── CLAUDE.md                   # Instruções de desenvolvimento
└── CONTEXT.md                  # Modelo de domínio
```

## Camadas do Backend

| Camada | Pasta | Responsabilidade |
|--------|-------|-----------------|
| API | `api/v1/` | Receber request → chamar service → retornar response |
| Service | `services/` | Lógica de negócio; único consumidor do InferenceEngine |
| Repository | `repositories/` | Acesso ao Firestore; sem lógica de negócio |
| Model | `models/` | Schemas Pydantic de entrada/saída |
| Aspect | `aspects/` | Cross-cutting concerns (A01–A05) |
| Inference | `inference_engine/` | Motor lógico isolado; sem imports externos |

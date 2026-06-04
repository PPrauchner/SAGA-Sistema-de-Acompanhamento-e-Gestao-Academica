"""
Ponto de entrada da aplicação FastAPI do SAGA.

Responsabilidades:
- Instanciar a aplicação FastAPI com título, versão e descrição do projeto.
- Configurar o lifespan (startup/shutdown) para inicializar e encerrar o Firebase Admin SDK
  via backend/app/core/firebase.py.
- Registrar os routers de cada domínio (auth, students, advisors, work_plan, activities,
  activity_types, productions, vehicles, extensions, checklist, inference, reports,
  dashboard, audit_logs) sob o prefixo /api/v1.
- Configurar middlewares globais: CORS, tratamento de exceções HTTP e logging de requests.
- Expor endpoint público GET /api/v1/health para health check da API e conectividade Firebase.
"""

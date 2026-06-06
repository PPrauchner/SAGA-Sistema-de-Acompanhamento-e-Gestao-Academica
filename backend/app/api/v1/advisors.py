"""
Router FastAPI para os endpoints de gestão de orientadores.

Responsabilidades:
- GET /api/v1/advisors: lista orientadores com contagem de orientandos ativos.
  Restrito a @requires_role('coordenacao').
- POST /api/v1/advisors: cria orientador e envia convite de primeiro acesso.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/advisors/{advisor_id}: atualiza dados do orientador.
  Aplica @requires_role('coordenacao') e @audit_operation.
- DELETE /api/v1/advisors/{advisor_id}: remove orientador (verificando ausência de
  orientandos ativos). Aplica @requires_role('coordenacao') e @audit_operation.
"""

from fastapi import APIRouter

router = APIRouter()

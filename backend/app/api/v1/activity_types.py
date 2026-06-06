"""
Router FastAPI para os endpoints de tipos de atividade creditável.

Responsabilidades:
- GET /api/v1/activity-types: lista tipos de atividade do programa. Acessível por todos
  os papéis autenticados.
- POST /api/v1/activity-types: cria novo tipo de atividade com pontuação, limite,
  categoria e flags. Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/activity-types/{type_id}: atualiza tipo de atividade — aciona aspecto de
  histórico (@track_history) pois alterações em pontuação ou limite afetam fatos do motor.
  Aplica @requires_role('coordenacao'), @audit_operation e @track_history.
- PATCH /api/v1/activity-types/{type_id}/toggle: ativa ou desativa o tipo.
  Aplica @requires_role('coordenacao'), @audit_operation e @track_history, pois mudança
  em ativo afeta o fato tipo_ativo do motor lógico.
"""

from fastapi import APIRouter

router = APIRouter()

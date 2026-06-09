"""
Router FastAPI para o endpoint de inferência lógica detalhada.

Responsabilidades:
- GET /api/v1/inference/{student_id}: executa todas as inferências do motor lógico para
  o aluno (RL01 a RL05) via InferenceService e retorna resultado estruturado completo com:
  situacao_inferida, apto_defesa, creditos_validos, em_risco, checklist detalhado por item,
  atividades_elegiveis (IDs que passaram na RL04), pontuacoes_producoes (score, nivel, peso
  por produção via RL05) e fatos_usados[] para exibição na InferencePage.
  Aplica @requires_role('aluno' apenas próprio, 'orientador' apenas orientandos,
  'coordenacao') e @audit_operation.
"""

from fastapi import APIRouter

router = APIRouter()

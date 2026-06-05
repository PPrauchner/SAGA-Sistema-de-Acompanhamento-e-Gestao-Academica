"""
Router FastAPI para os endpoints de relatórios gerenciais — exclusivos da coordenação.

Responsabilidades:
- GET /api/v1/reports/students-at-risk: alunos com situação de risco inferida pelo motor.
  Aplica @requires_role('coordenacao') e @audit_operation.
- GET /api/v1/reports/students-by-status: contagem e lista de alunos por situação registrada.
- GET /api/v1/reports/students-by-advisor: alunos agrupados por orientador com distribuição
  de status.
- GET /api/v1/reports/completion-time: tempo médio de integralização dos alunos concluídos
  (média de data_conclusao - data_ingresso).
- GET /api/v1/reports/productions: produção bibliográfica por aluno e por orientador com
  pontuação total e distribuição por nível de relevância. Aplica @audit_operation.
"""

from fastapi import APIRouter

router = APIRouter()

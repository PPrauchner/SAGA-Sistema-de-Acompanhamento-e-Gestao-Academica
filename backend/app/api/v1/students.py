"""
Router FastAPI para os endpoints de gestão de discentes.

Responsabilidades:
- GET /api/v1/students: lista alunos com filtros opcionais de status, orientador_id e
  programa_id. Coordenação vê todos; orientador vê apenas próprios orientandos.
  Aplica @check_deadlines para recalcular status de prazo na listagem.
- GET /api/v1/students/{student_id}: detalhe do aluno. Aluno vê apenas o próprio.
- POST /api/v1/students: cria aluno e dispara convite de primeiro acesso.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PUT /api/v1/students/{student_id}: atualiza dados editáveis do aluno.
  Aplica @requires_role('coordenacao') e @audit_operation.
- PATCH /api/v1/students/{student_id}/qualificacao: registra aprovação na qualificação,
  gerando fato qualificacao_aprovada para o motor. Aplica @track_history.
- PATCH /api/v1/students/{student_id}/proficiencia: registra comprovação de proficiência.
  Aplica @track_history.
- PATCH /api/v1/students/{student_id}/situacao: atualiza situação registrada manualmente.
  Aplica @track_history.
"""

from fastapi import APIRouter

router = APIRouter()

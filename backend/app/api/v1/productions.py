"""
Router FastAPI para os endpoints de produções bibliográficas.

Responsabilidades:
- GET /api/v1/productions: lista produções com pontuação calculada pelo motor RL05.
  Aluno vê as próprias; orientador vê dos orientandos; coordenação vê todas.
- POST /api/v1/productions: aluno registra produção bibliográfica. Motor RL05 calcula
  pontuação ponderada pelo nível de relevância do veículo imediatamente após o registro.
  Aplica @requires_role('aluno'), @audit_operation e @check_deadlines (verifica período
  do curso). Persiste pontuacao_calculada, nivel_veiculo e peso_aplicado no documento.
"""

from fastapi import APIRouter

router = APIRouter()

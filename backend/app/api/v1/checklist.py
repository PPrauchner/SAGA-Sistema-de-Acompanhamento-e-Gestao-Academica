"""
Router FastAPI para o endpoint de checklist de integralização.

Responsabilidades:
- GET /api/v1/checklist/{student_id}: executa o motor lógico via ChecklistService →
  InferenceService e retorna o checklist completo com status de cada um dos 7 requisitos
  (créditos mínimos, créditos por grupo básico/específico/tecnológico, proficiência,
  qualificação, produção validada e plano concluído). Persiste snapshot imutável em
  students/{id}/inferred_status/. Aplica @requires_role para aluno (próprio), orientador
  (orientandos) e coordenação, além de @check_deadlines para garantir que fatos de prazo
  estejam atualizados antes da inferência.
"""

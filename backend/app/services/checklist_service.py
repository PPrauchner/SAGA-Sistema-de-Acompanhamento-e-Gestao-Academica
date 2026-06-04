"""
Serviço de negócio para geração do checklist de integralização.

Responsabilidades:
- get_checklist(student_id) -> ChecklistResponse: delega execução ao InferenceService e
  formata o resultado como checklist de 7 requisitos (créditos mínimos totais, créditos
  por grupo básico/específico/tecnológico, proficiência, qualificação, produção validada,
  plano concluído). Cada requisito retorna status 'cumprido' | 'pendente' | 'em_risco'
  com valores obtidos vs mínimos/máximos requeridos.
- Detectar conflito entre situacao_registrada e situacao_inferida.
- Calcular riscos_detectados[] a partir das regras RL03 (em_risco e suas 4 cláusulas).
- Utilizado pelo endpoint GET /api/v1/checklist/{student_id} e pela ChecklistPage do
  frontend, que exibe dados reais em substituição aos dados hardcoded.
"""

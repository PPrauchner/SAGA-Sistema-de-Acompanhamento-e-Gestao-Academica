"""
Modelos Pydantic para as entidades do plano de trabalho: WorkPlan, Stage, Task e Update.

Responsabilidades:
- Definir WorkPlanCreate e WorkPlanResponse para o plano (titulo, datas, progresso_percentual,
  status_geral).
- Definir StageCreate e StageResponse para etapas do plano (nome, ordem, datas, status).
- Definir TaskCreate e TaskResponse para tasks de uma etapa (titulo, descricao, prazo,
  prioridade, status, responsavel_id).
- Definir ProgressUpdateCreate e ProgressUpdateResponse para atualizações de progresso do
  aluno (conteudo, percentual, autor_id, criado_em).
- Definir WorkPlanFull como resposta completa do GET /api/v1/work-plan/{student_id}
  incluindo etapas aninhadas com suas tasks e última atualização.
- Mapear as sub-coleções Firestore: students/{id}/work_plan, /stages, /tasks, /updates.
"""

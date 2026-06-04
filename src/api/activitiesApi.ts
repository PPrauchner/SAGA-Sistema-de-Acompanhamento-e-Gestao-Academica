/**
 * Camada de acesso à API REST para atividades creditáveis e tipos de atividade.
 *
 * Responsabilidades:
 * - getActivities(filters?): GET /api/v1/activities — lista atividades com filtros de
 *   student_id, status e categoria. Substitui dados hardcoded da ActivitiesPage (1170 linhas).
 * - createActivity(data): POST /api/v1/activities — retorna elegibilidade_preliminar
 *   calculada pelo motor RL04.
 * - validateActivity(activityId, data): PATCH /api/v1/activities/{id}/validate —
 *   orientador emite parecer ou coordenação aprova/rejeita.
 * - getActivityTypes(): GET /api/v1/activity-types — lista tipos para formulário de
 *   nova atividade.
 * - createActivityType(data): POST /api/v1/activity-types.
 * - updateActivityType(typeId, data): PUT /api/v1/activity-types/{id}.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

/**
 * Camada de acesso à API REST para plano de trabalho, etapas, tasks e progresso.
 *
 * Responsabilidades:
 * - getWorkPlan(studentId): GET /api/v1/work-plan/{student_id} — retorna plano completo
 *   com etapas e tasks aninhadas. Substitui dados hardcoded da WorkPlanPage.
 * - createWorkPlan(studentId, data): POST /api/v1/work-plan/{student_id}.
 * - updateWorkPlan(planId, data): PUT /api/v1/work-plan/{plan_id}.
 * - createStage(planId, data): POST /api/v1/work-plan/{plan_id}/stages.
 * - createTask(stageId, data): POST /api/v1/stages/{stage_id}/tasks.
 * - updateTaskStatus(taskId, status): PATCH /api/v1/tasks/{task_id}/status.
 * - addProgressUpdate(taskId, data): POST /api/v1/tasks/{task_id}/updates.
 * - getTaskUpdates(taskId): GET /api/v1/tasks/{task_id}/updates.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

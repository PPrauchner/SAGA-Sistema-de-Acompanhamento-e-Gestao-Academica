/**
 * Camada de acesso à API REST para checklist de integralização e prorrogações.
 *
 * Responsabilidades:
 * - getChecklist(studentId): GET /api/v1/checklist/{student_id} — executa motor lógico
 *   e retorna os 7 requisitos com status cumprido/pendente/em_risco, valores reais de
 *   créditos, datas de qualificação e riscos detectados. Substitui dados hardcoded da
 *   ChecklistPage.
 * - getExtensions(filters?): GET /api/v1/extensions.
 * - createExtension(data): POST /api/v1/extensions — aluno solicita prorrogação.
 * - reviewExtension(extensionId, parecer): PATCH /api/v1/extensions/{id}/review.
 * - approveExtension(extensionId, data): PATCH /api/v1/extensions/{id}/approve.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

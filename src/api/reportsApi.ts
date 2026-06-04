/**
 * Camada de acesso à API REST para relatórios gerenciais e logs de auditoria.
 *
 * Responsabilidades:
 * - getStudentsAtRisk(): GET /api/v1/reports/students-at-risk — alimenta gráfico da
 *   ReportsPage com dados reais em substituição a mockados.
 * - getStudentsByStatus(): GET /api/v1/reports/students-by-status.
 * - getStudentsByAdvisor(): GET /api/v1/reports/students-by-advisor.
 * - getCompletionTime(): GET /api/v1/reports/completion-time.
 * - getProductionsReport(): GET /api/v1/reports/productions.
 * - getAuditLogs(filters, page, pageSize): GET /api/v1/audit-logs — paginado com filtros
 *   por operação, usuário e data. Substitui tabela hardcoded da AuditPage.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 * - Exclusivo da coordenação — useAuth().role deve ser verificado antes de chamar.
 */

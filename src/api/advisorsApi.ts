/**
 * Camada de acesso à API REST para o domínio de orientadores.
 *
 * Responsabilidades:
 * - getAdvisors(): GET /api/v1/advisors — lista orientadores com orientandos_ativos e
 *   limite_orientandos reais. Substitui array hardcoded da AdvisorsPage.
 * - createAdvisor(data): POST /api/v1/advisors — cria orientador e retorna invite_token.
 * - updateAdvisor(advisorId, data): PUT /api/v1/advisors/{id}.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

/**
 * Camada de acesso à API REST para o domínio de discentes.
 *
 * Responsabilidades:
 * - getStudents(filters?): GET /api/v1/students — lista alunos com filtros opcionais
 *   de status e orientador_id. Substitui array hardcoded da StudentsPage.
 * - getStudent(studentId): GET /api/v1/students/{id} — detalhe do aluno.
 * - createStudent(data): POST /api/v1/students — cria aluno e retorna invite_token.
 * - updateStudent(studentId, data): PUT /api/v1/students/{id}.
 * - patchQualificacao(studentId, data): PATCH /api/v1/students/{id}/qualificacao.
 * - patchProficiencia(studentId, data): PATCH /api/v1/students/{id}/proficiencia.
 * - patchSituacao(studentId, data): PATCH /api/v1/students/{id}/situacao.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 * - Alinhar nomenclatura de status com o backend: substituir 'atencao'/'critico' por
 *   'em_risco' em toda a StudentsPage.
 */

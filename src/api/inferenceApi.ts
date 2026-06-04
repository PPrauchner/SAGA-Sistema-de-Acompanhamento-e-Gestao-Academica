/**
 * Camada de acesso à API REST para inferência lógica detalhada.
 *
 * Responsabilidades:
 * - getInference(studentId): GET /api/v1/inference/{student_id} — executa todas as
 *   inferências do motor (RL01 a RL05) e retorna resultado completo com:
 *   situacao_inferida, apto_defesa, creditos_validos, em_risco, checklist detalhado,
 *   atividades_elegiveis[], pontuacoes_producoes[] e fatos_usados[] para visualização
 *   no grafo da InferencePage (substitui 1041 linhas de dados hardcoded).
 * - getDashboardAluno(studentId): GET /api/v1/dashboard/aluno/{student_id}.
 * - getDashboardOrientador(advisorId): GET /api/v1/dashboard/orientador/{advisor_id}.
 * - getDashboardCoordenacao(): GET /api/v1/dashboard/coordenacao.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

/**
 * Hook React para autenticação Firebase e identidade do usuário logado.
 *
 * Responsabilidades:
 * - Assinar onAuthStateChanged do Firebase Auth para rastrear estado de autenticação.
 * - Após login bem-sucedido, chamar GET /api/v1/auth/me para obter role, programa_id,
 *   student_id (se aluno) ou advisor_id (se orientador) — dados não disponíveis no
 *   token sem chamada à API.
 * - Expor: { currentUser, role, programaId, studentId, advisorId, token, login,
 *   logout, loading }.
 * - `token`: string retornada por user.getIdToken() — incluída no header
 *   Authorization: Bearer <token> em todas as chamadas à API do backend.
 * - `login(email, senha)`: chama Firebase Auth signInWithEmailAndPassword.
 * - `logout()`: chama Firebase Auth signOut e limpa estado local.
 * - `loading`: true enquanto onAuthStateChanged ainda não resolveu o estado inicial
 *   (evita flash de tela de login para usuários já autenticados).
 */

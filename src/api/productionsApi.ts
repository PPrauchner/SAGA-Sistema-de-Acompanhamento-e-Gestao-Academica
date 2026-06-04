/**
 * Camada de acesso à API REST para produções bibliográficas e veículos de publicação.
 *
 * Responsabilidades:
 * - getProductions(studentId?): GET /api/v1/productions — lista produções com
 *   pontuacao_calculada e nivel_veiculo do motor RL05. Substitui dados hardcoded da
 *   ProductionsPage.
 * - createProduction(data): POST /api/v1/productions — motor RL05 calcula pontuação
 *   imediatamente, retornando pontuacao_calculada, nivel_veiculo e peso_aplicado.
 * - getVehicles(): GET /api/v1/vehicles — carrega veículos com nível de relevância real
 *   para substituir o seletor Qualis fixo (A1/A2/B1/B2/B3/B4/C) da ProductionsPage.
 * - createVehicle(data): POST /api/v1/vehicles.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

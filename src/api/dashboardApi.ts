/**
 * Camada de acesso à API REST para os três dashboards por papel.
 *
 * Responsabilidades:
 * - getAlunoDashboard(studentId, token): GET /api/v1/dashboard/aluno/{student_id}
 * - getOrientadorDashboard(advisorId, token): GET /api/v1/dashboard/orientador/{advisor_id}
 * - getCoordDashboard(token): GET /api/v1/dashboard/coordenacao
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 * - Tipos TypeScript espelham os Pydantic models do backend.
 */

import { apiGet } from "./http";

export interface CreditosResumo {
  total: number;
  basico: number;
  especifico: number;
  tecnologico: number;
  minimo_requerido: number;
}

export interface ChecklistResumo {
  cumpridos: number;
  pendentes: number;
  em_risco: number;
  total: number;
}

export interface TaskProxima {
  task_id: string;
  titulo: string;
  prazo: string;
  status: string;
}

export interface AlunoDashboardData {
  student_id: string;
  nome: string;
  situacao_registrada: string;
  situacao_inferida: string;
  conflito_situacao: boolean;
  prazo_final: string | null;
  dias_restantes: number;
  progresso_plano_percentual: number;
  creditos: CreditosResumo;
  checklist_resumo: ChecklistResumo;
  tasks_proximas: TaskProxima[];
  producoes_aprovadas: number;
  atividades_pendentes_validacao: number;
}

export interface OrientandoResumo {
  student_id: string;
  nome: string;
  situacao_inferida: string;
  progresso_plano: number;
  dias_restantes_prazo: number;
  alertas: string[];
}

export interface OrientandosPorStatus {
  regular: number;
  em_risco: number;
  qualificado: number;
  fase_defesa: number;
  em_prorrogacao: number;
}

export interface OrientadorDashboardData {
  advisor_id: string;
  nome: string;
  total_orientandos: number;
  orientandos_por_status: OrientandosPorStatus;
  atividades_aguardando_parecer: number;
  orientandos: OrientandoResumo[];
}

export interface AlunosPorStatus {
  regular: number;
  em_risco: number;
  em_prorrogacao: number;
  qualificado: number;
  fase_defesa: number;
}

export interface AuditoriaRecenteItem {
  operacao: string;
  usuario: string;
  timestamp: string;
}

export interface CoordDashboardData {
  programa_id: string;
  total_alunos: number;
  total_alunos_ativos: number;
  alunos_por_status: AlunosPorStatus;
  atividades_aguardando_validacao: number;
  prorrogacoes_pendentes: number;
  producoes_ultimo_mes: number;
  total_concluidos: number;
  tempo_medio_integralizacao_meses: number | null;
  auditoria_recente: AuditoriaRecenteItem[];
}

export function getAlunoDashboard(
  studentId: string,
  token: string,
): Promise<AlunoDashboardData> {
  return apiGet<AlunoDashboardData>(
    `/dashboard/aluno/${encodeURIComponent(studentId)}`,
    token,
  );
}

export function getOrientadorDashboard(
  advisorId: string,
  token: string,
): Promise<OrientadorDashboardData> {
  return apiGet<OrientadorDashboardData>(
    `/dashboard/orientador/${encodeURIComponent(advisorId)}`,
    token,
  );
}

export function getCoordDashboard(
  token: string,
): Promise<CoordDashboardData> {
  return apiGet<CoordDashboardData>("/dashboard/coordenacao", token);
}

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

import { apiGet } from "@/api/http";

export type RequisitoStatus = "cumprido" | "pendente" | "em_risco";

export interface CreditoMinimoRequisito {
  status: RequisitoStatus;
  obtidos: number;
  minimo: number;
  descricao: string;
}

export interface CreditoMaximoRequisito {
  status: RequisitoStatus;
  obtidos: number;
  maximo: number;
  descricao: string;
}

export interface ProficienciaRequisito {
  status: RequisitoStatus;
  data_comprovacao: string | null;
}

export interface QualificacaoRequisito {
  status: RequisitoStatus;
  data_aprovacao: string | null;
}

export interface ProducaoRequisito {
  status: RequisitoStatus;
  quantidade_aprovadas: number;
}

export interface PlanoRequisito {
  status: RequisitoStatus;
  tasks_concluidas: number;
  tasks_total_nao_defesa: number;
}

export interface ChecklistRequisitos {
  creditos_minimos: CreditoMinimoRequisito;
  creditos_grupo_basico: CreditoMinimoRequisito;
  creditos_grupo_especifico: CreditoMinimoRequisito;
  creditos_grupo_tecnologico: CreditoMaximoRequisito;
  proficiencia: ProficienciaRequisito;
  qualificacao: QualificacaoRequisito;
  producao_validada: ProducaoRequisito;
  plano_concluido: PlanoRequisito;
}

export interface ChecklistResponse {
  student_id: string;
  student_nome: string;
  timestamp: string;
  situacao_registrada: string;
  situacao_inferida: string;
  conflito_situacao: boolean;
  apto_defesa: boolean;
  requisitos: ChecklistRequisitos;
  riscos_detectados: string[];
  snapshot_id: string;
}

export function getChecklist(studentId: string, token?: string): Promise<ChecklistResponse> {
  return apiGet<ChecklistResponse>(`/checklist/${studentId}`, token);
}

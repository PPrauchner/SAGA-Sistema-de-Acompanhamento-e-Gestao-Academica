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

import { apiGet } from "@/api/http";

export type RequisitoStatus = "cumprido" | "pendente" | "em_risco";
export type SituacaoInferida = "regular" | "em_risco" | "qualificado" | "fase_defesa";

export interface CreditoMinimoItem {
  status: RequisitoStatus;
  obtidos: number;
  minimo: number;
}

export interface CreditoMaximoItem {
  status: RequisitoStatus;
  obtidos: number;
  maximo: number;
}

export interface StatusItem {
  status: RequisitoStatus;
}

export interface InferenceChecklist {
  creditos_minimos: CreditoMinimoItem;
  creditos_grupo_basico: CreditoMinimoItem;
  creditos_grupo_especifico: CreditoMinimoItem;
  creditos_grupo_tecnologico: CreditoMaximoItem;
  proficiencia: StatusItem;
  qualificacao: StatusItem;
  producao_validada: StatusItem;
  plano_concluido: StatusItem;
}

export interface PontuacaoProducao {
  producao_id: string;
  score: number;
  nivel_veiculo: string;
  peso_aplicado: number;
}

export interface InferenceResult {
  student_id: string;
  programa_id: string;
  timestamp: string;
  situacao_inferida: SituacaoInferida;
  apto_defesa: boolean;
  creditos_validos: boolean;
  em_risco: boolean;
  checklist: InferenceChecklist;
  atividades_elegiveis: string[];
  pontuacoes_producoes: PontuacaoProducao[];
  fatos_usados: string[];
  riscos_detectados: string[];
  snapshot_id: string;
}

export function getInference(studentId: string, token?: string): Promise<InferenceResult> {
  return apiGet<InferenceResult>(`/inference/${studentId}`, token);
}

import { apiGet, apiPost } from "@/api/http";

export type SolicitacaoStatus =
  | "pendente"
  | "em_analise"
  | "aprovado"
  | "aprovada"
  | "reprovado"
  | "rejeitado"
  | "rejeitada";

export interface Solicitacao {
  id: string;
  tipo?: string | null;
  status: SolicitacaoStatus | string;
  student_id?: string | null;
  aluno_id?: string | null;
  aluno_nome?: string | null;
  aluno?: string | null;
  matricula?: string | null;
  nivel?: string | null;
  nova_data?: string | null;
  prazo_novo?: string | null;
  novaData?: string | null;
  data_atual?: string | null;
  prazo_atual?: string | null;
  dataAtual?: string | null;
  created_at?: string | null;
  solicitacao?: string | null;
  motivo?: string | null;
  justificativa?: string | null;
  parecer?: string | null;
}

export interface CreateSolicitacaoPayload {
  tipo: string;
  nova_data: string;
  motivo: string;
  student_id?: string;
}

export const solicitacoesApi = {
  list(token: string): Promise<Solicitacao[]> {
    return apiGet<Solicitacao[]>("/extensions", token);
  },

  // Fila de prorrogações do programa para a coordenação (default: status pendente).
  listPending(token: string, status?: string): Promise<Solicitacao[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return apiGet<Solicitacao[]>(`/extensions/pending${query}`, token);
  },

  create(token: string, payload: CreateSolicitacaoPayload): Promise<Solicitacao> {
    return apiPost<Solicitacao>("/extensions", payload, token);
  },

  // Decisao em-linha da coordenacao para prorrogacao/trancamento (issue #308):
  // aprovar recalcula o prazo do aluno no backend; rejeitar exige motivo.
  approve(token: string, extensionId: string): Promise<Solicitacao> {
    return apiPost<Solicitacao>(`/extensions/${extensionId}/approve`, {}, token);
  },

  reject(token: string, extensionId: string, motivo: string): Promise<Solicitacao> {
    return apiPost<Solicitacao>(`/extensions/${extensionId}/reject`, { motivo }, token);
  },
};

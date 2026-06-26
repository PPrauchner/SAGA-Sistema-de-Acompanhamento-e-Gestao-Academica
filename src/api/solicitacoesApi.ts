import { apiGet } from "@/api/http";

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

export const solicitacoesApi = {
  list(token: string): Promise<Solicitacao[]> {
    return apiGet<Solicitacao[]>("/extensions", token);
  },
};

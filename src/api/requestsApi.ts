import { API_ROOT } from "./http";

export interface RequestItem {
  id: string;
  tipo:
    | "atividade"
    | "producao"
    | "prorrogacao"
    | "prazo_defesa"
    | "prazo_qualificacao"
    | "trancamento"
    | "transferencia"
    | "transferencia_coordenacao";
  origem: "formulario" | "agregado";
  solicitante_nome: string;
  data_solicitacao: string;
  status: string;
  payload_original: Record<string, any>;
}

export const requestsApi = {
  async getRequests(token: string): Promise<RequestItem[]> {
    const res = await fetch(`${API_ROOT}/api/v1/requests`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch requests: ${res.statusText}`);
    }

    return res.json();
  },
};

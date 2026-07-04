import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type ExtensionStatus = "pendente" | "em_analise" | "aprovada" | "rejeitada";
export type ExtensionTipo =
  | "prazo_defesa"
  | "prazo_qualificacao"
  | "trancamento"
  | "mudanca_nivel";

export interface Extension {
  id: string;
  student_id: string;
  student_nome?: string | null;
  requester_id: string;
  programa_id?: string | null;
  tipo: ExtensionTipo;
  motivo: string;
  plano_atualizado: string;
  parecer_orientador: string | null;
  status: ExtensionStatus;
  nova_data: string;
  data_atual?: string | null;
  prazo_novo?: string | null;
  aprovado_por?: string | null;
  aprovado_em?: string | null;
  created_at: string;
}

export interface CreateExtensionInput {
  tipo: ExtensionTipo;
  motivo: string;
  plano_atualizado: string;
  nova_data: string; // ISO 8601
}

export const useExtensionsApi = () => {
  const { token, currentUser, role } = useAuth();
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [loading, setLoading] = useState(true);

  const getHeaders = () => ({ headers: { Authorization: `Bearer ${token}` } });

  // Escopo por papel é resolvido no backend (Spec 08 — GET /extensions).
  const loadExtensions = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await axios.get<Extension[]>(`${API_URL}/api/v1/extensions`, getHeaders());
      setExtensions(response.data);
    } catch (err) {
      console.error("Erro ao carregar prorrogações:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) loadExtensions();
  }, [token, role]);

  const createRequest = async (data: CreateExtensionInput): Promise<Extension> => {
    const response = await axios.post<Extension>(`${API_URL}/api/v1/extensions`, data, getHeaders());
    await loadExtensions();
    return response.data;
  };

  const submitReview = async (extensionId: string, parecer: string): Promise<Extension> => {
    const response = await axios.patch<Extension>(
      `${API_URL}/api/v1/extensions/${extensionId}/review`,
      { parecer_orientador: parecer },
      getHeaders(),
    );
    await loadExtensions();
    return response.data;
  };

  const submitDecision = async (
    extensionId: string,
    acao: "aprovar" | "rejeitar",
  ): Promise<Extension> => {
    const response = await axios.patch<Extension>(
      `${API_URL}/api/v1/extensions/${extensionId}/approve`,
      { acao },
      getHeaders(),
    );
    await loadExtensions();
    return response.data;
  };

  return {
    extensions,
    loading,
    role,
    currentUser,
    createRequest,
    submitReview,
    submitDecision,
    refresh: loadExtensions,
  };
};

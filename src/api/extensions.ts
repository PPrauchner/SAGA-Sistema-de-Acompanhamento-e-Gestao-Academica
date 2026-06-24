import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Extension {
  id: string;
  aluno_id: string;
  aluno_nome?: string;
  motivo: string;
  plano_atualizado: string;
  parecer_orientador: string | null;
  semestres_solicitados: number;
  status: "pendente" | "aprovada" | "rejeitada";
  prazo_novo?: string;
  criado_em: string;
}

export const useExtensionsApi = () => {
  const { token, currentUser, role, studentId } = useAuth();
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [loading, setLoading] = useState(true);

  const getHeaders = () => ({
    headers: { Authorization: `Bearer ${token}` }
  });

  const loadExtensions = async () => {
    if (!token) return;
    setLoading(true);
    try {
      // Correção C4: Mapeamento exato das URLs criadas no backend FastAPI
      const url = role === "aluno" && studentId
        ? `${API_URL}/api/v1/extensions/students/${studentId}`
        : `${API_URL}/api/v1/extensions/dashboard`;
      
      const response = await axios.get(url, getHeaders());
      setExtensions(response.data);
    } catch (err) {
      console.error("Erro ao carregar prorrogações:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) loadExtensions();
  }, [token, role, studentId]);

  // Correção m2: Remoção do campo morto tipo_solicitacao do contrato
  const createRequest = async (data: { motivo: string; plano_atualizado: string; semestres_solicitados: number }) => {
    const response = await axios.post(`${API_URL}/api/v1/extensions`, data, getHeaders());
    await loadExtensions();
    return response.data;
  };

  const submitReview = async (studentIdParam: string, extensionId: string, parecer: string) => {
    const response = await axios.patch(
      `${API_URL}/api/v1/extensions/${studentIdParam}/${extensionId}/review`, 
      { parecer_orientador: parecer }, 
      getHeaders()
    );
    await loadExtensions();
    return response.data;
  };

  // Correção C4/M1: Alinhado rota para /approve e payload para { aprovado: boolean }
  const submitDecision = async (studentIdParam: string, extensionId: string, decision: "aprovada" | "rejeitada") => {
    const isApproved = decision === "aprovada";
    const response = await axios.patch(
      `${API_URL}/api/v1/extensions/${studentIdParam}/${extensionId}/approve`, 
      { aprovado: isApproved }, 
      getHeaders()
    );
    await loadExtensions();
    return response.data;
  };

  return {
    extensions,
    loading,
    role,
    currentUser,
    studentId,
    createRequest,
    submitReview,
    submitDecision,
    refresh: loadExtensions
  };
};
import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "@/hooks/useAuth"; // Ajuste o path conforme seu projeto

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Extension {
  id: string;
  aluno_id: string;
  aluno_nome?: string; // Fallback ou enriquecido
  motivo: string;
  plano_atualizado: string;
  parecer_orientador: string | null;
  semestres_solicitados: number;
  status: "pendente" | "aprovada" | "rejeitada";
  prazo_novo?: string;
  criado_em: string;
  tipo_solicitacao?: string; // Preservado para compatibilidade com o seu front
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
      // Alunos buscam apenas os seus; Orientação/Coordenação buscam via query ou endpoint global
      const targetId = role === "aluno" ? studentId : "";
      const url = targetId 
        ? `${API_URL}/api/v1/students/${targetId}/extensions`
        : `${API_URL}/api/v1/extensions/dashboard`; // Rota gerencial ou filtro adaptado
      
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

  const createRequest = async (data: { motivo: string; plano_atualizado: string; semestres_solicitados: number; tipo_solicitacao?: string }) => {
    const response = await axios.post(`${API_URL}/api/v1/extensions`, data, getHeaders());
    await loadExtensions();
    return response.data;
  };

  const submitReview = async (studentIdParam: string, extensionId: string, parecer: string) => {
    const response = await axios.patch(`${API_URL}/api/v1/extensions/${studentIdParam}/${extensionId}/review`, { parecer_orientador: parecer }, getHeaders());
    await loadExtensions();
    return response.data;
  };

  const submitDecision = async (studentIdParam: string, extensionId: string, status: "aprovada" | "rejeitada") => {
    const response = await axios.patch(`${API_URL}/api/v1/extensions/${studentIdParam}/${extensionId}/decision`, { status }, getHeaders());
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
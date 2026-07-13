/**
 * Cliente HTTP e hook React do domínio de prorrogações de prazo (Spec 08).
 *
 * Responsabilidades:
 * - extensionsApi: list/create/review/decide contra /api/v1/extensions, via http.ts.
 * - useExtensionsApi(): carrega a lista no escopo do papel e expõe as mutações.
 *
 * O escopo por papel é resolvido no backend (GET /extensions): aluno vê as próprias,
 * orientador as dos orientandos, coordenação as do programa.
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "@/api/http";
import { useAuth } from "@/hooks/useAuth";
import type { UserRole } from "@/app/context/AppContext";

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
  matricula?: string | null;
  nivel?: string | null;
  requester_id: string;
  programa_id?: string | null;
  tipo: ExtensionTipo;
  motivo: string;
  plano_atualizado: string;
  parecer_orientador: string | null;
  observacao_coordenacao?: string | null;
  status: ExtensionStatus;
  nova_data: string;
  data_atual?: string | null;
  prazo_novo?: string | null;
  aprovado_por?: string | null;
  aprovado_em?: string | null;
  motivo_rejeicao?: string | null;
  rejeitado_por?: string | null;
  rejeitado_em?: string | null;
  created_at: string;
}

export interface CreateExtensionInput {
  tipo: ExtensionTipo;
  motivo: string;
  plano_atualizado: string;
  nova_data: string; // ISO 8601
}

export const extensionsApi = {
  list(token: string): Promise<Extension[]> {
    return apiGet<Extension[]>("/extensions", token);
  },

  create(token: string, payload: CreateExtensionInput): Promise<Extension> {
    return apiPost<Extension>("/extensions", payload, token);
  },

  review(token: string, extensionId: string, parecer: string): Promise<Extension> {
    return apiPatch<Extension>(
      `/extensions/${extensionId}/review`,
      { parecer_orientador: parecer },
      token,
    );
  },

  approve(token: string, extensionId: string, observacao?: string): Promise<Extension> {
    return apiPost<Extension>(`/extensions/${extensionId}/approve`, { observacao }, token);
  },

  // Spec 08: o indeferimento exige motivo; o backend o persiste em motivo_rejeicao.
  reject(token: string, extensionId: string, motivo: string): Promise<Extension> {
    return apiPost<Extension>(`/extensions/${extensionId}/reject`, { motivo }, token);
  },
};

interface UseExtensionsApiResult {
  extensions: Extension[];
  loading: boolean;
  error: string | null;
  role: UserRole | null;
  createRequest: (data: CreateExtensionInput) => Promise<Extension>;
  submitReview: (extensionId: string, parecer: string) => Promise<Extension>;
  submitApproval: (extensionId: string, observacao?: string) => Promise<Extension>;
  submitRejection: (extensionId: string, motivo: string) => Promise<Extension>;
  refresh: () => Promise<void>;
}

export function useExtensionsApi(): UseExtensionsApiResult {
  const { token, role } = useAuth();
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadExtensions = useCallback(async (): Promise<void> => {
    if (!token) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setExtensions(await extensionsApi.list(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar prorrogações.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadExtensions();
  }, [loadExtensions, role]);

  const createRequest = async (data: CreateExtensionInput): Promise<Extension> => {
    const created = await extensionsApi.create(token!, data);
    await loadExtensions();
    return created;
  };

  const submitReview = async (extensionId: string, parecer: string): Promise<Extension> => {
    const reviewed = await extensionsApi.review(token!, extensionId, parecer);
    await loadExtensions();
    return reviewed;
  };

  const submitApproval = async (extensionId: string, observacao?: string): Promise<Extension> => {
    const approved = await extensionsApi.approve(token!, extensionId, observacao);
    await loadExtensions();
    return approved;
  };

  const submitRejection = async (extensionId: string, motivo: string): Promise<Extension> => {
    const rejected = await extensionsApi.reject(token!, extensionId, motivo);
    await loadExtensions();
    return rejected;
  };

  return {
    extensions,
    loading,
    error,
    role,
    createRequest,
    submitReview,
    submitApproval,
    submitRejection,
    refresh: loadExtensions,
  };
}

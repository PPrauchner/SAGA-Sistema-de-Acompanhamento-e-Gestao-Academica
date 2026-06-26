import { API_ROOT, apiGet, apiPatch } from "@/api/http";

const API_BASE = `${API_ROOT}/api/v1`;

export interface PublicAdvisor {
  id: string;
  uid?: string | null;
  nome: string;
}

export interface RegistrationRequestPayload {
  nome: string;
  email: string;
  advisor_id: string;
}

export interface RegistrationRequest {
  id: string;
  nome: string;
  email: string;
  advisor_id?: string | null;
  advisor_nome?: string | null;
  orientador_nome?: string | null;
  orientador?: string | null;
  created_at?: string | null;
  solicitado_em?: string | null;
  status?: string | null;
}

async function publicRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : null;
    throw new Error(detail ?? `Falha na API (HTTP ${response.status})`);
  }
  return data as T;
}

export const registrationRequestsApi = {
  async listActiveAdvisors(): Promise<PublicAdvisor[]> {
    const advisors = await publicRequest<PublicAdvisor[]>("/registration-requests/advisors");
    return advisors.filter((advisor) => advisor.uid);
  },

  create(payload: RegistrationRequestPayload): Promise<{ id?: string; message?: string }> {
    return publicRequest<{ id?: string; message?: string }>("/registration-requests", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listPending(token: string): Promise<RegistrationRequest[]> {
    return apiGet<RegistrationRequest[]>("/registration-requests", token);
  },

  approve(token: string, id: string): Promise<{ message?: string }> {
    return apiPatch<{ message?: string }>(`/registration-requests/${id}/approve`, {}, token);
  },

  reject(token: string, id: string): Promise<{ message?: string }> {
    return apiPatch<{ message?: string }>(`/registration-requests/${id}/reject`, {}, token);
  },
};

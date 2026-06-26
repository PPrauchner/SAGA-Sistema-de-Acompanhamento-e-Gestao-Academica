import { API_ROOT } from "@/api/http";

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
};

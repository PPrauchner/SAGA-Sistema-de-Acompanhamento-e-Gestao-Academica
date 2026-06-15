import { API_URL } from "@/api/authApi";

export interface Advisor {
  id: string;
  uid?: string | null;
  nome: string;
  email: string;
  departamento: string;
  programa_id: string;
  lattes?: string | null;
  limite_orientandos: number;
  orientandos_ativos: number;
}

export interface AdvisorCreatePayload {
  uid?: string | null;
  nome: string;
  email: string;
  departamento: string;
  lattes?: string | null;
  programa_id: string;
  limite_orientandos: number;
}

export interface AdvisorCreateResult {
  id: string;
  nome: string;
  invite_token: string;
}

export interface AdvisorUpdatePayload {
  nome?: string;
  departamento?: string;
  lattes?: string | null;
  limite_orientandos?: number;
}

async function request<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? `Falha na API (HTTP ${response.status})`);
  }
  return data as T;
}

export function getAdvisors(token: string): Promise<Advisor[]> {
  return request<Advisor[]>("/api/v1/advisors", token);
}

export function createAdvisor(
  token: string,
  data: AdvisorCreatePayload,
): Promise<AdvisorCreateResult> {
  return request<AdvisorCreateResult>("/api/v1/advisors", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateAdvisor(
  token: string,
  advisorId: string,
  data: AdvisorUpdatePayload,
): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/v1/advisors/${advisorId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * API client for creditable activity types.
 *
 * A base deriva de API_ROOT (fonte única de http.ts, host raiz sem /api/v1 — issue #114);
 * o prefixo /api/v1 é adicionado aqui. Em respostas não-ok, propaga o `detail` do backend
 * para a UI exibir o motivo real da falha (validação/persistência).
 */

import { API_ROOT } from "@/api/http";

const API_BASE_URL = `${API_ROOT}/api/v1`;

async function request(token: string, path: string, init: RequestInit = {}): Promise<any> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? `Falha na API (HTTP ${response.status})`);
  }
  return data;
}

export const activityTypesApi = {
  getActivityTypes: (token: string) => request(token, "/activity-types"),

  createActivityType: (token: string, data: any) =>
    request(token, "/activity-types", { method: "POST", body: JSON.stringify(data) }),

  updateActivityType: (token: string, id: string, data: any) =>
    request(token, `/activity-types/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  toggleActivityType: (token: string, id: string) =>
    request(token, `/activity-types/${id}/toggle`, { method: "PATCH" }),
};

import { API_URL } from "@/api/authApi";

export type CoordinationTransferStatus = "pendente" | "aceita" | "rejeitada" | "cancelada" | "concluido";

export interface CoordinationTransfer {
  id: string;
  programa_id: string;
  initiator_uid: string;
  successor_uid: string;
  status: CoordinationTransferStatus;
  created_at: string;
  updated_at: string;
  decided_at?: string | null;
  cancelled_at?: string | null;
  rejected_at?: string | null;
  accepted_at?: string | null;
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
    const error = new Error(data.detail ?? `Falha na API (HTTP ${response.status})`);
    (error as Error & { status?: number }).status = response.status;
    throw error;
  }
  return data as T;
}

export const coordinationTransfersApi = {
  list(token: string): Promise<CoordinationTransfer[]> {
    return request<CoordinationTransfer[]>("/api/v1/coordination-transfers", token);
  },

  start(token: string, successorUid: string): Promise<CoordinationTransfer> {
    return request<CoordinationTransfer>("/api/v1/coordination-transfers", token, {
      method: "POST",
      body: JSON.stringify({ successor_uid: successorUid }),
    });
  },

  accept(token: string, transferId: string): Promise<{ message: string }> {
    return request<{ message: string }>(
      `/api/v1/coordination-transfers/${transferId}/accept`,
      token,
      { method: "POST", body: JSON.stringify({}) },
    );
  },

  reject(token: string, transferId: string): Promise<{ message: string }> {
    return request<{ message: string }>(
      `/api/v1/coordination-transfers/${transferId}/reject`,
      token,
      { method: "POST", body: JSON.stringify({}) },
    );
  },

  cancel(token: string, transferId: string): Promise<{ message: string }> {
    return request<{ message: string }>(
      `/api/v1/coordination-transfers/${transferId}/cancel`,
      token,
      { method: "POST", body: JSON.stringify({}) },
    );
  },
};

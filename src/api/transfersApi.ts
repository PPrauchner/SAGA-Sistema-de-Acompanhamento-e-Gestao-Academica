import { API_URL } from "@/api/authApi";

export interface DirectTransferPayload {
  student_id: string;
  orientador_destino_id: string;
  observacao?: string | null;
}

export interface DirectTransferResult {
  id: string;
  student_id: string;
  orientador_origem_id?: string | null;
  orientador_destino_id: string;
  coorientador_limpo: boolean;
  pending_cancelled: boolean;
  message: string;
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

export function directTransfer(
  token: string,
  data: DirectTransferPayload,
): Promise<DirectTransferResult> {
  return request<DirectTransferResult>("/api/v1/transfers/direct", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

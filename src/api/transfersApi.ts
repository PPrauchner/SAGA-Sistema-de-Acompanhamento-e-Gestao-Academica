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

export type TransferStatus = "pendente" | "aprovada" | "rejeitada" | "cancelada";
export type TransferTipo = "direta_coordenacao" | "solicitada_orientador" | "solicitada_aluno";

export interface TransferRequest {
  id: string;
  student_id: string;
  orientador_origem_id?: string | null;
  orientador_destino_id: string;
  solicitante_id: string;
  programa_id: string;
  status: TransferStatus;
  tipo: TransferTipo;
  motivo?: string | null;
  created_at?: string;
  updated_at?: string;
  decidido_por?: string | null;
  decidido_em?: string | null;
  cancelado_em?: string | null;
}

export interface TransferCreatePayload {
  student_id: string;
  orientador_destino_id: string;
  motivo?: string | null;
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

export function getTransfers(token: string): Promise<TransferRequest[]> {
  return request<TransferRequest[]>("/api/v1/transfers", token);
}

export function createTransferRequest(
  token: string,
  data: TransferCreatePayload,
): Promise<{ id: string; status: TransferStatus; message: string }> {
  return request<{ id: string; status: TransferStatus; message: string }>("/api/v1/transfers", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function approveTransferRequest(
  token: string,
  transferId: string,
): Promise<{ id: string; status: TransferStatus; message: string }> {
  return request<{ id: string; status: TransferStatus; message: string }>(`/api/v1/transfers/${transferId}/approve`, token, {
    method: "POST",
  });
}

export function rejectTransferRequest(
  token: string,
  transferId: string,
  motivo: string,
): Promise<{ id: string; status: TransferStatus; message: string }> {
  return request<{ id: string; status: TransferStatus; message: string }>(`/api/v1/transfers/${transferId}/reject`, token, {
    method: "POST",
    body: JSON.stringify({ motivo }),
  });
}

export function cancelTransferRequest(
  token: string,
  transferId: string,
): Promise<{ id: string; status: TransferStatus; message: string }> {
  return request<{ id: string; status: TransferStatus; message: string }>(`/api/v1/transfers/${transferId}/cancel`, token, {
    method: "POST",
  });
}

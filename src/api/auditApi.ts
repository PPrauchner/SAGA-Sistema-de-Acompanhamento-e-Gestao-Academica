/**
 * Cliente HTTP do domínio de auditoria (aspecto A02).
 *
 * Responsabilidades:
 * - getAuditLogs(token, filters): consome GET /api/v1/audit-logs com filtros opcionais
 *   (usuario_id, operacao, modulo, resultado_status, data_inicio, data_fim) e paginação
 *   (page, page_size), devolvendo o envelope AuditLogPage. O backend escopa por papel:
 *   coordenação recebe a visão total; orientador recebe apenas os logs dos seus orientandos.
 */

import { API_URL } from "@/api/authApi";

export type ResultadoStatus = "sucesso" | "erro";

export interface AuditLog {
  id: string;
  usuario_id?: string | null;
  usuario_nome?: string | null;
  role?: string | null;
  programa_id?: string | null;
  operacao?: string | null;
  modulo?: string | null;
  recurso?: string | null;
  valor_entrada?: Record<string, unknown> | null;
  resultado_status?: ResultadoStatus | null;
  erro_mensagem?: string | null;
  timestamp?: string | null;
  duracao_ms?: number | null;
}

export interface AuditLogPage {
  items: AuditLog[];
  page: number;
  page_size: number;
  total: number;
}

export interface AuditLogFilters {
  usuario_id?: string;
  operacao?: string;
  modulo?: string;
  resultado_status?: ResultadoStatus | "";
  data_inicio?: string;
  data_fim?: string;
  page?: number;
  page_size?: number;
}

function buildQuery(filters: AuditLogFilters): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== "") {
      params.append(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function getAuditLogs(
  token: string,
  filters: AuditLogFilters = {},
): Promise<AuditLogPage> {
  const response = await fetch(`${API_URL}/api/v1/audit-logs${buildQuery(filters)}`, {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? `Falha na API (HTTP ${response.status})`);
  }
  return data as AuditLogPage;
}

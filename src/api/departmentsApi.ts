/**
 * Camada de acesso à API REST para departamentos (ADR-0004, restrito ao papel adm).
 *
 * - getDepartments(token): GET /api/v1/departments
 * - createDepartment(token, payload): POST /api/v1/departments
 * - updateDepartment(token, departmentId, payload): PUT /api/v1/departments/{id}
 * - deleteDepartment(token, departmentId): DELETE /api/v1/departments/{id} — 400 se
 *   houver programa(s) vinculado(s) ao departamento.
 */

import { API_URL } from "@/api/authApi";

export interface Department {
  id: string;
  nome: string;
  instituicao: string | null;
  criado_em: string | null;
  atualizado_em: string | null;
}

export interface DepartmentCreatePayload {
  nome: string;
  instituicao?: string | null;
}

export interface DepartmentUpdatePayload {
  nome?: string;
  instituicao?: string | null;
}

/**
 * Extrai uma mensagem legível do campo `detail` de uma resposta de erro do FastAPI.
 * `detail` pode ser string (HTTPException), lista de objetos (422 de validação Pydantic,
 * cada item com `msg`) ou objeto arbitrário — nunca deve virar "[object Object]" na UI.
 */
function extractErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item?.msg === "string" ? item.msg : null))
      .filter((msg): msg is string => msg !== null);
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
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
    throw new Error(extractErrorMessage(data.detail, `Falha na API (HTTP ${response.status})`));
  }
  return data as T;
}

export function getDepartments(token: string): Promise<Department[]> {
  return request<Department[]>("/api/v1/departments", token);
}

export function createDepartment(
  token: string,
  data: DepartmentCreatePayload,
): Promise<Department> {
  return request<Department>("/api/v1/departments", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateDepartment(
  token: string,
  departmentId: string,
  data: DepartmentUpdatePayload,
): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/v1/departments/${departmentId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteDepartment(token: string, departmentId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/v1/departments/${departmentId}`, token, {
    method: "DELETE",
  });
}

import { API_URL } from "@/api/authApi";

export type StudentLevel = "mestrado" | "doutorado";
export type StudentStatus =
  | "regular"
  | "em_prorrogacao"
  | "em_risco"
  | "qualificado"
  | "em_fase_de_defesa"
  | "concluido"
  | "desligado";

export interface Student {
  id: string;
  uid?: string | null;
  nome: string;
  email: string;
  matricula: string;
  orientador_id: string;
  coorientador_id?: string | null;
  programa_id: string;
  nivel: StudentLevel;
  data_ingresso: string;
  prazo_final?: string | null;
  situacao_registrada: StudentStatus;
  situacao_inferida: string;
  qualificacao_aprovada?: boolean;
  proficiencia_comprovada?: boolean;
  qualificacao_data?: string | null;
  proficiencia_data?: string | null;
}

export interface StudentCreatePayload {
  nome: string;
  email: string;
  matricula: string;
  orientador_id: string;
  coorientador_id?: string | null;
  nivel: StudentLevel;
  data_ingresso: string;
  programa_id: string;
}

export interface StudentCreateResult {
  id: string;
  nome: string;
  invite_token: string;
}

export interface StudentUpdatePayload {
  nome?: string;
  orientador_id?: string;
  coorientador_id?: string | null;
  prazo_final?: string | null;
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

export function getStudents(token: string): Promise<Student[]> {
  return request<Student[]>("/api/v1/students", token);
}

export function createStudent(
  token: string,
  data: StudentCreatePayload,
): Promise<StudentCreateResult> {
  return request<StudentCreateResult>("/api/v1/students", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateStudent(
  token: string,
  studentId: string,
  data: StudentUpdatePayload,
): Promise<{ id: string; message: string }> {
  return request<{ id: string; message: string }>(`/api/v1/students/${studentId}`, token, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

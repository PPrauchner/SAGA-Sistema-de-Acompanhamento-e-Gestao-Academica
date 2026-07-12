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
  qualificacao_comprovante_url?: string | null;
  proficiencia_comprovante_url?: string | null;
  // Percentual (0-100) de tasks concluídas do plano de trabalho, calculado no backend.
  progresso_plano?: number;
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

export interface UpdateProficienciaPayload {
  comprovada: boolean;
  data_proficiencia?: string | null;
  comprovante_url?: string | null;
}

export interface UpdateQualificacaoPayload {
  aprovada: boolean;
  data_qualificacao: string;
  comprovante_url?: string | null;
}

/** Entrada mínima do diretório de co-autores (GET /students/coauthors), usada pelo
 * seletor de co-autores do formulário de produção (issue #310). Acessível também a
 * 'aluno' — diferente de getStudents(), que é orientador/coordenação apenas. */
export interface CoauthorCandidate {
  uid: string;
  nome: string;
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

export function getStudent(token: string, studentId: string): Promise<Student> {
  return request<Student>(`/api/v1/students/${studentId}`, token);
}

export function createStudent(
  token: string,
  data: StudentCreatePayload,
): Promise<StudentCreateResult> {
  const payload: StudentCreatePayload = { ...data, nivel: "mestrado" };
  return request<StudentCreateResult>("/api/v1/students", token, {
    method: "POST",
    body: JSON.stringify(payload),
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

export function updateProficiencia(
  token: string,
  studentId: string,
  data: UpdateProficienciaPayload,
): Promise<{ message: string; situacao_inferida?: string; situacao_inferida_atualizada?: boolean }> {
  return request<{ message: string; situacao_inferida?: string; situacao_inferida_atualizada?: boolean }>(
    `/api/v1/students/${studentId}/proficiencia`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
  );
}

export function updateQualificacao(
  token: string,
  studentId: string,
  data: UpdateQualificacaoPayload,
): Promise<{ message: string; situacao_inferida?: string; situacao_inferida_atualizada?: boolean }> {
  return request<{ message: string; situacao_inferida?: string; situacao_inferida_atualizada?: boolean }>(
    `/api/v1/students/${studentId}/qualificacao`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    },
  );
}

export function getCoauthorCandidates(token: string): Promise<CoauthorCandidate[]> {
  return request<CoauthorCandidate[]>("/api/v1/students/coauthors", token);
}

/**
 * Camada de acesso à API REST para o domínio de autenticação.
 *
 * Responsabilidades:
 * - API_URL: base da API do backend (VITE_API_URL, default http://localhost:8000).
 * - getMe(token): GET /api/v1/auth/me — perfil do usuário autenticado, mapeado para
 *   camelCase. Requer Authorization: Bearer <token>. Lança ApiError (com o status HTTP)
 *   em resposta não-ok, para que o chamador distinga falha de auth (401/403) de
 *   indisponibilidade transitória (5xx).
 * - activateFirstAccess(token, senha): POST /api/v1/auth/first-access — endpoint público
 *   que ativa a conta convidada e retorna uid, role e e-mail. O papel vem do convite,
 *   não do cliente.
 */

import type { UserRole } from "@/app/context/AppContext";
import { ApiError } from "@/api/http";

// Base da API do backend; em dev o FastAPI roda em http://localhost:8000.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Perfil retornado por GET /api/v1/auth/me, já em camelCase. */
export interface AuthProfile {
  uid: string;
  email: string;
  nome: string;
  role: UserRole;
  programaId: string;
  studentId: string | null;
  advisorId: string | null;
}

/** Resultado de POST /api/v1/auth/first-access. */
export interface FirstAccessResult {
  uid: string;
  role: UserRole;
  email: string;
}

export async function getMe(token: string): Promise<AuthProfile> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Falha ao carregar perfil (HTTP ${response.status})`);
  }
  const data = await response.json();
  return {
    uid: data.uid,
    email: data.email,
    nome: data.nome,
    role: data.role,
    programaId: data.programa_id,
    studentId: data.student_id ?? null,
    advisorId: data.advisor_id ?? null,
  };
}

export async function activateFirstAccess(
  token: string,
  senha: string,
): Promise<FirstAccessResult> {
  const response = await fetch(`${API_URL}/api/v1/auth/first-access`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, senha }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? `Falha ao ativar conta (HTTP ${response.status})`);
  }
  return { uid: data.uid, role: data.role, email: data.email };
}

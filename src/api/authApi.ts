/**
 * Camada de acesso à API REST para o domínio de autenticação.
 *
 * Responsabilidades:
 * - API_URL: base da API do backend para clientes que embutem /api/v1 no path. Reexporta
 *   a fonte única API_ROOT de http.ts (ver issue #114) — não lê VITE_API_URL diretamente.
 * - getMe(token): GET /api/v1/auth/me — perfil do usuário autenticado, mapeado para
 *   camelCase. Delega a apiGet, que lança ApiError (com o status HTTP) em resposta não-ok,
 *   para que o chamador distinga falha de auth (4xx) de indisponibilidade transitória (5xx).
 * - activateFirstAccess(token, senha): POST /api/v1/auth/first-access — endpoint público
 *   que ativa a conta convidada e retorna uid, role e e-mail. O papel vem do convite,
 *   não do cliente.
 */

import type { NotificationPreferences, UserRole } from "@/app/context/AppContext";
import { API_ROOT, apiGet } from "@/api/http";

// Base da API para os clientes que montam o path com /api/v1 (studentsApi, activitiesApi,
// advisorsApi, auditApi, useNotifications). Deriva da fonte única em http.ts.
export const API_URL = API_ROOT;

/** Perfil retornado por GET /api/v1/auth/me, já em camelCase. */
export interface AuthProfile {
  uid: string;
  email: string;
  nome: string;
  role: UserRole;
  programaId: string;
  departamento: string | null;
  matricula: string | null;
  studentId: string | null;
  advisorId: string | null;
  notificationPreferences: NotificationPreferences;
}

const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  email: true,
  in_app: true,
  work_plan: true,
  transfers: true,
  activities: true,
  extensions: true,
};

/** Forma crua de GET /api/v1/auth/me (snake_case), antes do mapeamento para camelCase. */
interface RawProfile {
  uid: string;
  email: string;
  nome: string;
  role: UserRole;
  programa_id: string;
  departamento?: string | null;
  matricula?: string | null;
  student_id?: string | null;
  advisor_id?: string | null;
  notification_preferences?: Partial<NotificationPreferences> | null;
}

/** Resultado de POST /api/v1/auth/first-access. */
export interface FirstAccessResult {
  uid: string;
  role: UserRole;
  email: string;
}

export async function getMe(token: string): Promise<AuthProfile> {
  const data = await apiGet<RawProfile>("/auth/me", token);
  return {
    uid: data.uid,
    email: data.email,
    nome: data.nome,
    role: data.role,
    programaId: data.programa_id,
    departamento: data.departamento ?? null,
    matricula: data.matricula ?? null,
    studentId: data.student_id ?? null,
    advisorId: data.advisor_id ?? null,
    notificationPreferences: {
      ...DEFAULT_NOTIFICATION_PREFERENCES,
      ...(data.notification_preferences ?? {}),
    },
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

export async function activateGoogleFirstAccess(
  token: string,
): Promise<FirstAccessResult> {
  const response = await fetch(`${API_URL}/api/v1/auth/google-first-access`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail ?? `Falha ao ativar conta (HTTP ${response.status})`);
  }
  return { uid: data.uid, role: data.role, email: data.email };
}

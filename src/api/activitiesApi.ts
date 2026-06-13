/**
 * Camada de acesso à API REST para atividades creditáveis e tipos de atividade.
 *
 * Responsabilidades:
 * - getActivityTypes(): GET /api/v1/activity-types
 * - createActivityType(data): POST /api/v1/activity-types
 * - updateActivityType(typeId, data): PUT /api/v1/activity-types/{id}
 * - toggleActivityType(typeId): PATCH /api/v1/activity-types/{id}/toggle
 * - getActivities(filters?): GET /api/v1/activities
 * - createActivity(data): POST /api/v1/activities — retorna elegibilidade_preliminar (RL04)
 * - validateActivity(activityId, studentId, data): PATCH /api/v1/activities/{id}/validate
 * - uploadComprovante(activityId, studentId, file): POST /api/v1/activities/{id}/comprovante
 */

const BASE = "/api/v1";

async function authHeaders(token?: string): Promise<HeadersInit> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Activity Types ───────────────────────────────────────────────────────────

export interface ActivityType {
  id: string;
  nome: string;
  categoria: "basico" | "especifico" | "tecnologico";
  pontuacao_base: number;
  limite_maximo_creditos: number | null;
  exige_comprovante: boolean;
  permite_multiplas: boolean;
  ativo: boolean;
}

export interface ActivityTypeCreate {
  nome: string;
  categoria: "basico" | "especifico" | "tecnologico";
  pontuacao_base: number;
  limite_maximo_creditos?: number | null;
  exige_comprovante?: boolean;
  permite_multiplas?: boolean;
}

export async function getActivityTypes(
  token?: string,
  onlyActive = false,
): Promise<ActivityType[]> {
  const params = onlyActive ? "?only_active=true" : "";
  const res = await fetch(`${BASE}/activity-types${params}`, {
    headers: await authHeaders(token),
  });
  if (!res.ok) throw new Error(`getActivityTypes: ${res.status}`);
  return res.json();
}

export async function createActivityType(
  data: ActivityTypeCreate,
  token?: string,
): Promise<ActivityType> {
  const res = await fetch(`${BASE}/activity-types`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders(token)) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`createActivityType: ${res.status}`);
  return res.json();
}

export async function updateActivityType(
  typeId: string,
  data: Partial<ActivityTypeCreate>,
  token?: string,
): Promise<ActivityType> {
  const res = await fetch(`${BASE}/activity-types/${typeId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(await authHeaders(token)) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`updateActivityType: ${res.status}`);
  return res.json();
}

export async function toggleActivityType(
  typeId: string,
  token?: string,
): Promise<ActivityType> {
  const res = await fetch(`${BASE}/activity-types/${typeId}/toggle`, {
    method: "PATCH",
    headers: await authHeaders(token),
  });
  if (!res.ok) throw new Error(`toggleActivityType: ${res.status}`);
  return res.json();
}

// ─── Activities ───────────────────────────────────────────────────────────────

export interface ActivityResponse {
  id: string;
  student_id: string;
  tipo_id: string;
  tipo_nome: string | null;
  categoria: string | null;
  descricao: string;
  data_realizacao: string;
  comprovante_url: string | null;
  creditos_gerados: number;
  status: string;
  parecer_orientador: string | null;
  observacao_coordenacao: string | null;
  elegivel: boolean | null;
}

export interface ActivityCreate {
  tipo_id: string;
  descricao: string;
  data_realizacao: string;
  comprovante_url?: string | null;
  status?: "rascunho" | "enviado";
}

export interface ActivitySubmitResponse {
  id: string;
  elegibilidade_preliminar: boolean;
  notificacao_enviada: boolean;
}

export interface ActivityValidateRequest {
  acao: "parecer_orientador" | "aprovar" | "rejeitar";
  observacao?: string | null;
  creditos_concedidos?: number | null;
}

export interface ActivityValidateResponse {
  message: string;
  novo_status: string;
  creditos_contabilizados: number | null;
  motor_inferencia_executado: boolean;
  fato_gerado: string | null;
}

export interface GetActivitiesFilters {
  student_id?: string;
  status?: string;
  categoria?: string;
}

export async function getActivities(
  filters?: GetActivitiesFilters,
  token?: string,
): Promise<ActivityResponse[]> {
  const params = new URLSearchParams();
  if (filters?.student_id) params.set("student_id", filters.student_id);
  if (filters?.status)     params.set("status", filters.status);
  if (filters?.categoria)  params.set("categoria", filters.categoria);
  const qs = params.toString() ? `?${params}` : "";

  const res = await fetch(`${BASE}/activities${qs}`, {
    headers: await authHeaders(token),
  });
  if (!res.ok) throw new Error(`getActivities: ${res.status}`);
  return res.json();
}

export async function createActivity(
  data: ActivityCreate,
  token?: string,
): Promise<ActivitySubmitResponse> {
  const res = await fetch(`${BASE}/activities`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders(token)) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`createActivity: ${res.status}`);
  return res.json();
}

export async function validateActivity(
  activityId: string,
  studentId: string,
  data: ActivityValidateRequest,
  token?: string,
): Promise<ActivityValidateResponse> {
  const params = new URLSearchParams({ student_id: studentId });
  const res = await fetch(`${BASE}/activities/${activityId}/validate?${params}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await authHeaders(token)) },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`validateActivity: ${res.status}`);
  return res.json();
}

export async function uploadComprovante(
  activityId: string,
  studentId: string,
  file: File,
  token?: string,
): Promise<{ comprovante_url: string }> {
  const form = new FormData();
  form.append("file", file);
  const params = new URLSearchParams({ student_id: studentId });

  const res = await fetch(`${BASE}/activities/${activityId}/comprovante?${params}`, {
    method: "POST",
    headers: await authHeaders(token),
    body: form,
  });
  if (!res.ok) throw new Error(`uploadComprovante: ${res.status}`);
  return res.json();
}

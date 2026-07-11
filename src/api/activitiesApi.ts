/**
 * Camada de acesso à API REST para atividades creditáveis e tipos de atividade.
 *
 * Responsabilidades:
 * - getActivities(token, filters?): GET /api/v1/activities — lista atividades visíveis ao
 *   usuário (aluno vê as próprias), com filtros opcionais de student_id, status e categoria.
 * - createActivity(token, payload): POST /api/v1/activities — registra a atividade e retorna
 *   a elegibilidade_preliminar calculada pelo motor RL04.
 * - uploadComprovante(token, activityId, file): POST /api/v1/activities/{id}/comprovante —
 *   envia o arquivo (multipart) ao Firebase Storage e devolve a URL de download tokenizada.
 * - emitirParecer(token, activityId, parecer): PATCH /api/v1/activities/{id}/parecer —
 *   orientador registra o parecer textual sobre a atividade do orientando.
 * - validarAtividade(token, activityId, payload): PATCH /api/v1/activities/{id}/validate —
 *   coordenação aprova/rejeita a atividade, contabiliza créditos e dispara a re-inferência.
 * - deleteActivity(token, activityId): DELETE /api/v1/activities/{id} — exclui atividade em
 *   rascunho/enviado/rejeitado. Aluno só a própria; coordenação, qualquer uma.
 * - getActivityTypes(token): GET /api/v1/activity-types — lista tipos para o formulário de
 *   nova atividade.
 * - Todas as funções incluem Authorization: Bearer <token>.
 */

import { API_URL } from "@/api/authApi";

export type ActivityCategory = "basico" | "especifico" | "tecnologico";
export type ActivityStatus = "rascunho" | "enviado" | "aprovado" | "rejeitado";
export type ActivityCreateStatus = "rascunho" | "enviado";

/** Atividade retornada por GET /api/v1/activities (enriquecida com tipo_nome/categoria). */
export interface Activity {
  id: string;
  aluno_nome: string | null;
  orientador_nome: string | null;
  // null para atividades lastreadas em produção bibliográfica (sem tipo creditável).
  tipo_id: string | null;
  // preenchido apenas em atividades de produção bibliográfica (FK para productions/).
  producao_id: string | null;
  tipo_nome: string | null;
  categoria: ActivityCategory | string | null;
  descricao: string;
  data_realizacao: string | null;
  criado_em: string | null;
  comprovante_url: string | null;
  creditos_gerados: number;
  status: ActivityStatus | string;
  parecer_orientador: string | null;
  observacao_coordenacao: string | null;
  elegivel: boolean | null;
}

/** Tipo de atividade creditável retornado por GET /api/v1/activity-types. */
export interface ActivityType {
  id: string;
  nome: string;
  categoria: ActivityCategory | string;
  pontuacao_base: number;
  limite_maximo_creditos: number | null;
  exige_comprovante: boolean;
  permite_multiplas: boolean;
  ativo: boolean;
}

export interface ActivityCreatePayload {
  tipo_id: string;
  descricao: string;
  data_realizacao: string;
  comprovante_url?: string | null;
  status: ActivityCreateStatus;
}

/** Payload de POST /activities/orientador — orientador cria atividade para um orientando. */
export interface ActivityCreateForOrientandoPayload {
  aluno_id: string;
  tipo_id: string;
  descricao: string;
  data_realizacao: string;
  comprovante_url?: string | null;
  parecer: string;
}

export interface ActivityCreateResult {
  id: string;
  elegibilidade_preliminar: boolean;
  notificacao_enviada: boolean;
}

export interface ComprovanteUploadResult {
  comprovante_url: string;
  path_bucket: string;
}

export type ValidateAction = "aprovar" | "rejeitar";

export interface ValidateActivityPayload {
  acao: ValidateAction;
  observacao?: string | null;
  creditos_concedidos?: number | null;
}

export interface ValidateActivityResult {
  message: string;
  novo_status: ActivityStatus;
  creditos_contabilizados: number | null;
  motor_inferencia_executado: boolean;
  fato_gerado: string | null;
}

export interface ActivityFilters {
  student_id?: string;
  status?: string;
  categoria?: string;
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

async function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
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

export function getActivities(token: string, filters: ActivityFilters = {}): Promise<Activity[]> {
  const params = new URLSearchParams();
  if (filters.student_id) params.set("student_id", filters.student_id);
  if (filters.status) params.set("status", filters.status);
  if (filters.categoria) params.set("categoria", filters.categoria);
  const query = params.toString();
  return request<Activity[]>(`/api/v1/activities${query ? `?${query}` : ""}`, token);
}

export function getActivityTypes(token: string): Promise<ActivityType[]> {
  return request<ActivityType[]>("/api/v1/activity-types", token);
}

/** Orientador emite o parecer textual sobre uma atividade do orientando. */
export function emitirParecer(
  token: string,
  activityId: string,
  parecer: string,
): Promise<Activity> {
  return request<Activity>(`/api/v1/activities/${activityId}/parecer`, token, {
    method: "PATCH",
    body: JSON.stringify({ parecer }),
  });
}

/** Coordenação aprova ou rejeita definitivamente a atividade submetida. */
export function validarAtividade(
  token: string,
  activityId: string,
  payload: ValidateActivityPayload,
): Promise<ValidateActivityResult> {
  return request<ValidateActivityResult>(`/api/v1/activities/${activityId}/validate`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createActivity(
  token: string,
  payload: ActivityCreatePayload,
): Promise<ActivityCreateResult> {
  return request<ActivityCreateResult>("/api/v1/activities", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Orientador cria atividade para um orientando (nasce 'enviado' com parecer preenchido). */
export function createActivityForOrientando(
  token: string,
  payload: ActivityCreateForOrientandoPayload,
): Promise<ActivityCreateResult> {
  return request<ActivityCreateResult>("/api/v1/activities/orientador", token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Exclui (hard delete) atividade em rascunho, enviado ou rejeitado. */
export async function deleteActivity(token: string, activityId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/activities/${activityId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(extractErrorMessage(data.detail, `Falha ao excluir atividade (HTTP ${response.status})`));
  }
}

/**
 * Envia o comprovante via multipart/form-data. Não define Content-Type manualmente — o
 * browser o preenche com o boundary correto a partir do FormData.
 */
export async function uploadComprovante(
  token: string,
  activityId: string,
  file: File,
): Promise<ComprovanteUploadResult> {
  const form = new FormData();
  form.append("arquivo", file);

  const response = await fetch(`${API_URL}/api/v1/activities/${activityId}/comprovante`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      extractErrorMessage(data.detail, `Falha no upload do comprovante (HTTP ${response.status})`),
    );
  }
  return data as ComprovanteUploadResult;
}

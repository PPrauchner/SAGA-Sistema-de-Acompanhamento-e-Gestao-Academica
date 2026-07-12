/**
 * Helper HTTP compartilhado pelas camadas de API do frontend.
 *
 * Responsabilidades:
 * - API_ROOT: fonte única da base da API, derivada de VITE_API_URL (host raiz, SEM o
 *   prefixo de versão /api/v1 — o código é dono do prefixo). Fallback: http://localhost:8000.
 *   Normaliza o valor para tolerar barra final e um /api/v1 acidental.
 * - apiGet/apiPost/apiPatch/apiPut/apiDelete(path, token?): incluem header Authorization: Bearer <token>
 *   quando um token é fornecido (forward-compatible com a autenticação das issues #04/#10),
 *   contra API_ROOT/api/v1.
 * - Lançar ApiError com o status HTTP e uma mensagem legível extraída do corpo da resposta
 *   (campo `detail` do FastAPI — string em HTTPException, ou lista de erros de validação
 *   Pydantic com `.msg`) em respostas não-ok, para tratamento nas páginas (issue #253).
 */

/** Extrai uma mensagem legível de `detail`: string (HTTPException) ou lista Pydantic (422). */
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

// Fonte única da base da API: único ponto que lê VITE_API_URL no frontend. Mantém o host
// raiz sem /api/v1 para que clientes que embutem o prefixo no path e clientes que usam
// a base com prefixo derivem da mesma origem (evita /api/v1 duplicado ou ausente — issue #114).
// Normaliza removendo barra(s) final(is) e um sufixo /api/v1 acidental, tornando a base
// robusta independentemente de como VITE_API_URL é informado.
export const API_ROOT: string = (
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000"
)
  .replace(/\/+$/, "")
  .replace(/\/api\/v1$/, "");

// Base com prefixo de versão, usada internamente por apiGet.
const API_BASE: string = `${API_ROOT}/api/v1`;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, { headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      extractErrorMessage(data.detail, `Falha na requisição (${response.status})`),
    );
  }
  return (await response.json()) as T;
}

async function apiJson<T>(method: "POST" | "PATCH" | "PUT", path: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      extractErrorMessage(data.detail, `Falha na requisição (${response.status})`),
    );
  }
  return (await response.json()) as T;
}

export function apiPost<T>(path: string, body: unknown, token?: string): Promise<T> {
  return apiJson<T>("POST", path, body, token);
}

export function apiPatch<T>(path: string, body: unknown, token?: string): Promise<T> {
  return apiJson<T>("PATCH", path, body, token);
}

export function apiPut<T>(path: string, body: unknown, token?: string): Promise<T> {
  return apiJson<T>("PUT", path, body, token);
}

export async function apiDelete<T>(path: string, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE}${path}`, { method: "DELETE", headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      extractErrorMessage(data.detail, `Falha na requisição (${response.status})`),
    );
  }
  return (await response.json()) as T;
}

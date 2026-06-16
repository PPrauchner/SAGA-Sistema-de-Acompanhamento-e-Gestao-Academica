/**
 * Helper HTTP compartilhado pelas camadas de API do frontend.
 *
 * Responsabilidades:
 * - Resolver a base da API a partir de VITE_API_URL (fallback: http://localhost:8000/api/v1).
 * - Expor apiGet(path, token?): faz GET com header Authorization: Bearer <token> quando um
 *   token é fornecido (forward-compatible com a autenticação das issues #04/#10).
 * - Lançar erro com o status HTTP em respostas não-ok, para tratamento nas páginas.
 */

const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

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
    throw new ApiError(response.status, `Falha na requisição (${response.status})`);
  }
  return (await response.json()) as T;
}

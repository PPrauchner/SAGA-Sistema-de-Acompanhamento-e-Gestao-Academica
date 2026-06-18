/**
 * Camada de acesso à API REST para produções bibliográficas e veículos de publicação.
 *
 * Responsabilidades:
 * - getProductions(token): GET /api/v1/productions — lista produções com
 *   pontuacao_calculada e nivel_veiculo do motor RL05. Substitui dados hardcoded da
 *   ProductionsPage.
 * - createProduction(token, data): POST /api/v1/productions — motor RL05 calcula pontuação
 *   imediatamente, retornando pontuacao_calculada, nivel_veiculo e peso_aplicado.
 * - getVehicles(token): GET /api/v1/vehicles — carrega veículos com nível de relevância real
 *   para substituir o seletor Qualis fixo (A1/A2/B/C) da ProductionsPage.
 * - Todas as funções incluem Authorization: Bearer <token> obtido via useAuth().
 */

import { API_URL } from "@/api/authApi";

export type RelevanceLevel = "A1" | "A2" | "B" | "C";
export type TipoProducao = "artigo" | "livro" | "capitulo";
export type StatusPublicacao = "publicado" | "submetido" | "aceito";

export interface Vehicle {
  id: string;
  nome: string;
  tipo: "evento" | "revista";
  sigla?: string | null;
  issn?: string | null;
  nivel: RelevanceLevel;
  peso: number;
}

export interface Production {
  id: string;
  aluno_id: string;
  aluno_nome: string;
  titulo: string;
  doi?: string | null;
  veiculo_nome: string;
  nivel_veiculo: string;
  tipo_producao: TipoProducao;
  status_publicacao: StatusPublicacao;
  observacao?: string | null;
  pontuacao_calculada: number;
  peso_aplicado: number;
  status_atividade: string;
}

export interface ProductionCreatePayload {
  titulo: string;
  doi?: string | null;
  veiculo_id: string;
  tipo_producao: TipoProducao;
  status_publicacao: StatusPublicacao;
  observacao?: string | null;
  data_realizacao: string;
  comprovante_url?: string | null;
}

export interface ProductionCreateResult {
  id: string;
  activity_id: string | null;
  pontuacao_calculada: number;
  nivel_veiculo: string;
  peso_aplicado: number;
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

export function getProductions(token: string): Promise<Production[]> {
  return request<Production[]>("/api/v1/productions", token);
}

export function getVehicles(token: string): Promise<Vehicle[]> {
  return request<Vehicle[]>("/api/v1/vehicles", token);
}

export function createProduction(
  token: string,
  data: ProductionCreatePayload,
): Promise<ProductionCreateResult> {
  return request<ProductionCreateResult>("/api/v1/productions", token, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

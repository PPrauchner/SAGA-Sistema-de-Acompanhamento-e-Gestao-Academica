/**
 * Cliente HTTP do domínio de pesos Qualis versionados por programa (config da coordenação).
 *
 * Responsabilidades:
 * - getActive: pesos vigentes do programa (GET /qualis-weights).
 * - getHistory: histórico de versões, mais recente primeiro (GET /qualis-weights/history).
 * - setWeights: cria uma nova versão de pesos (POST /qualis-weights) — não sobrescreve.
 *
 * Toda escrita passa pelo backend (Admin SDK); o token é enviado em Authorization: Bearer.
 */

import { apiGet, apiPost } from "@/api/http";

/** Escala Qualis (A1–A8 + fallback SC), na ordem de exibição. */
export const QUALIS_LEVELS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "SC"] as const;

export type QualisLevel = (typeof QUALIS_LEVELS)[number];

/** Mapa nível → peso. */
export type QualisWeights = Record<string, number>;

/** Uma versão persistida de pesos (a coleção versionada é o próprio histórico). */
export interface QualisWeightsVersion {
  id: string;
  pesos: QualisWeights;
  vigente_desde: string;
  alterado_por: string;
  alterado_em: string;
}

/** Resposta da criação de uma nova versão. */
export interface QualisWeightsCreated {
  id: string;
  vigente_desde: string;
  pesos: QualisWeights;
}

export const qualisWeightsApi = {
  getActive: (token: string): Promise<QualisWeights> =>
    apiGet<QualisWeights>("/qualis-weights", token),

  getHistory: (token: string): Promise<QualisWeightsVersion[]> =>
    apiGet<QualisWeightsVersion[]>("/qualis-weights/history", token),

  setWeights: (token: string, pesos: QualisWeights): Promise<QualisWeightsCreated> =>
    apiPost<QualisWeightsCreated>("/qualis-weights", { pesos }, token),
};

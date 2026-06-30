/**
 * Hook React para a fila de validação da coordenação (dashboard).
 *
 * Responsabilidades:
 * - useValidationQueue(): carrega atividades e produções com status "enviado" (aguardando
 *   validação) e funde numa lista unificada de itens, expondo loading/error/data.
 * - Atividades de produção bibliográfica (com producao_id) são excluídas da lista de
 *   atividades para não duplicar com as produções.
 * - O token de autenticação vem do useAuth() via AppContext; exclusivo da coordenação.
 */

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import { getActivities } from "@/api/activitiesApi";
import { getProductions } from "@/api/productionsApi";

export interface ValidationQueueItem {
  id: string;
  tipo: "atividade" | "producao";
  aluno: string;
  orientador: string;
  descricao: string;
  data: string | null;
}

interface UseValidationQueueResult {
  data: ValidationQueueItem[] | null;
  loading: boolean;
  error: string | null;
}

export function useValidationQueue(): UseValidationQueueResult {
  const { token } = useAuth();
  const [data, setData] = useState<ValidationQueueItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getActivities(token, { status: "enviado" }),
      getProductions(token, "enviado"),
    ])
      .then(([activities, productions]) => {
        if (cancelled) return;
        const items: ValidationQueueItem[] = [
          // Exclui atividades de produção (producao_id) — representadas pelas produções.
          ...activities
            .filter((activity) => !activity.producao_id)
            .map((activity) => ({
              id: activity.id,
              tipo: "atividade" as const,
              aluno: activity.aluno_nome ?? "—",
              orientador: activity.orientador_nome ?? "—",
              descricao: activity.descricao,
              data: activity.criado_em,
            })),
          ...productions.map((production) => ({
            id: production.id,
            tipo: "producao" as const,
            aluno: production.aluno_nome ?? "—",
            orientador: production.orientador_nome ?? "—",
            descricao: production.titulo,
            data: production.criado_em,
          })),
        ];
        setData(items);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return { data, loading, error };
}

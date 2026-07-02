/**
 * Hook React para a fila de prorrogações pendentes do programa (dashboard da coordenação).
 *
 * Responsabilidades:
 * - usePendingExtensions(): carrega GET /extensions/pending e expõe loading/error/data.
 * - O token de autenticação vem do useAuth() via AppContext; exclusivo da coordenação.
 */

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import { solicitacoesApi, type Solicitacao } from "@/api/solicitacoesApi";

interface UsePendingExtensionsResult {
  data: Solicitacao[] | null;
  loading: boolean;
  error: string | null;
}

export function usePendingExtensions(): UsePendingExtensionsResult {
  const { token } = useAuth();
  const [data, setData] = useState<Solicitacao[] | null>(null);
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
    solicitacoesApi
      .listPending(token)
      .then((result) => {
        if (!cancelled) setData(result);
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

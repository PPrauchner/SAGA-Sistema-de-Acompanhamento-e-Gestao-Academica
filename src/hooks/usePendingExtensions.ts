/**
 * Hook React para a fila de prorrogações pendentes do programa (dashboard da coordenação).
 *
 * Responsabilidades:
 * - usePendingExtensions(): carrega GET /extensions e expõe apenas as pendentes.
 * - O token de autenticação vem do useAuth() via AppContext; exclusivo da coordenação.
 *
 * O backend já restringe GET /extensions ao programa do coordenador autenticado, então
 * o filtro por status aqui basta para reproduzir a fila de decisão.
 */

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import { extensionsApi, type Extension } from "@/api/extensions";

interface UsePendingExtensionsResult {
  data: Extension[] | null;
  loading: boolean;
  error: string | null;
}

export function usePendingExtensions(): UsePendingExtensionsResult {
  const { token } = useAuth();
  const [data, setData] = useState<Extension[] | null>(null);
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
    extensionsApi
      .list(token)
      .then((result) => {
        if (!cancelled) setData(result.filter((ext) => ext.status === "pendente"));
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

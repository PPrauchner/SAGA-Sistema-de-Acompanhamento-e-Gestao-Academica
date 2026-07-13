/**
 * Hook React para a série mensal de produções validadas (dashboard da coordenação).
 *
 * Responsabilidades:
 * - useProductionsByMonth(meses?): carrega GET /reports/productions-by-month e expõe
 *   estado de loading, error e data.
 * - O token de autenticação vem do useAuth() via AppContext; exclusivo da coordenação.
 */

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import {
  getProductionsByMonth,
  type ProductionByMonthItem,
} from "@/api/reportsApi";

interface UseProductionsByMonthResult {
  data: ProductionByMonthItem[] | null;
  loading: boolean;
  error: string | null;
}

export function useProductionsByMonth(meses?: number): UseProductionsByMonthResult {
  const { token } = useAuth();
  const [data, setData] = useState<ProductionByMonthItem[] | null>(null);
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
    getProductionsByMonth(token, meses)
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
  }, [token, meses]);

  return { data, loading, error };
}

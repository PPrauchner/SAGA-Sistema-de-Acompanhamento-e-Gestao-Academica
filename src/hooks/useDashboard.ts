/**
 * Hooks React para consumir a API de dashboards.
 *
 * Responsabilidades:
 * - useAlunoDashboard(): carrega dados do dashboard do aluno autenticado.
 * - useOrientadorDashboard(advisorId): carrega dados do dashboard do orientador.
 * - useCoordDashboard(): carrega dados do dashboard da coordenação.
 * - Cada hook gerencia estado de loading, error e data.
 * - O token de autenticação vem do useAuth() via AppContext.
 */

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import {
  getMeuAlunoDashboard,
  getOrientadorDashboard,
  getCoordDashboard,
  type AlunoDashboardData,
  type OrientadorDashboardData,
  type CoordDashboardData,
} from "@/api/dashboardApi";

interface UseDashboardResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAlunoDashboard(): UseDashboardResult<AlunoDashboardData> {
  const { token } = useAuth();
  const [data, setData] = useState<AlunoDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getMeuAlunoDashboard(token)
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
  }, [token, refreshKey]);

  return { data, loading, error, refetch };
}

export function useOrientadorDashboard(
  advisorId: string | undefined,
): UseDashboardResult<OrientadorDashboardData> {
  const { token } = useAuth();
  const [data, setData] = useState<OrientadorDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    if (!advisorId || !token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getOrientadorDashboard(advisorId, token)
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
  }, [advisorId, token, refreshKey]);

  return { data, loading, error, refetch };
}

export function useCoordDashboard(): UseDashboardResult<CoordDashboardData> {
  const { token } = useAuth();
  const [data, setData] = useState<CoordDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refetch = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    getCoordDashboard(token)
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
  }, [token, refreshKey]);

  return { data, loading, error, refetch };
}

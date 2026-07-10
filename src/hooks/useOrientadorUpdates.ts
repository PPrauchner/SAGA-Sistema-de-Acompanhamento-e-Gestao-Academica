/**
 * Hook React para a timeline de atualizações recentes do OrientadorDashboard.
 *
 * Responsabilidades:
 * - useOrientadorUpdates(): carrega as entradas mais recentes de audit_logs via
 *   GET /api/v1/audit-logs (page_size limitado) e as mapeia para itens enxutos de timeline
 *   (incluindo o autor pelo nome resolvido no backend, com fallback para o uid),
 *   expondo loading/error/data.
 * - O backend escopa por papel: para o orientador autenticado, retorna apenas os logs dos
 *   seus orientandos (ações executadas por eles). Nenhuma filtragem extra é feita aqui.
 * - O token de autenticação vem do useAuth() via AppContext.
 */

import { useEffect, useState } from "react";

import { getAuditLogs, type AuditLog } from "@/api/auditApi";
import { useAuth } from "./useAuth";

export interface OrientadorUpdateItem {
  id: string;
  operacao: string | null;
  recurso: string | null;
  autor: string | null;
  resultadoStatus: "sucesso" | "erro" | null;
  timestamp: string | null;
}

interface UseOrientadorUpdatesResult {
  data: OrientadorUpdateItem[] | null;
  loading: boolean;
  error: string | null;
}

const PAGE_SIZE = 8;

export function useOrientadorUpdates(): UseOrientadorUpdatesResult {
  const { token } = useAuth();
  const [data, setData] = useState<OrientadorUpdateItem[] | null>(null);
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
    getAuditLogs(token, { page_size: PAGE_SIZE })
      .then((page) => {
        if (cancelled) return;
        setData(
          page.items.map((log: AuditLog) => ({
            id: log.id,
            operacao: log.operacao ?? null,
            recurso: log.recurso ?? null,
            autor: log.usuario_nome ?? log.usuario_id ?? null,
            resultadoStatus: log.resultado_status ?? null,
            timestamp: log.timestamp ?? null,
          })),
        );
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

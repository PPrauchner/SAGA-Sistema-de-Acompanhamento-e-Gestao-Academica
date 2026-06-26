import { useCallback, useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, Clock, Mail, UserCheck, XCircle } from "lucide-react";

import {
  registrationRequestsApi,
  type RegistrationRequest,
} from "@/api/registrationRequestsApi";
import { useApp } from "../../context/AppContext";

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

function getAdvisorName(request: RegistrationRequest): string {
  return request.advisor_nome ?? request.orientador_nome ?? request.orientador ?? request.advisor_id ?? "Orientador não informado";
}

function getCreatedAt(request: RegistrationRequest): string | null {
  return request.created_at ?? request.solicitado_em ?? null;
}

export function RegistrationRequestsPage() {
  const { token } = useApp();
  const [requests, setRequests] = useState<RegistrationRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const loadRequests = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await registrationRequestsApi.listPending(token);
      setRequests(data.filter((request) => !request.status || request.status === "pendente"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar solicitações de cadastro.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  async function handleAction(id: string, action: "approve" | "reject"): Promise<void> {
    if (!token || busyId) return;

    setBusyId(id);
    setFeedback(null);
    setActionError(null);
    try {
      if (action === "approve") {
        await registrationRequestsApi.approve(token, id);
      } else {
        await registrationRequestsApi.reject(token, id);
      }
      setRequests((current) => current.filter((request) => request.id !== id));
      setFeedback(action === "approve" ? "Solicitação aprovada com sucesso." : "Solicitação rejeitada com sucesso.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Falha ao atualizar solicitação.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div className="min-w-0">
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Solicitações de Cadastro</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            Revise pedidos públicos de ingresso enviados por futuros alunos.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-xl px-3 py-2 self-start sm:self-auto" style={{ background: "#eef3fc", color: "#123C7A", fontSize: "12px", fontWeight: 700 }}>
          <Clock size={14} /> {requests.length} pendente(s)
        </div>
      </div>

      {feedback && (
        <div className="rounded-2xl p-4 mb-4" style={{ background: "#dcfce7", color: "#166534", border: "1px solid #bbf7d0", fontSize: "13px", fontWeight: 600 }}>
          {feedback}
        </div>
      )}

      {actionError && (
        <div className="rounded-2xl p-4 mb-4" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca", fontSize: "13px", fontWeight: 600 }}>
          {actionError}
        </div>
      )}

      {loading && (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Carregando solicitações de cadastro...
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl p-5" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca" }}>
          {error}
        </div>
      )}

      {!loading && !error && requests.length === 0 && (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Nenhuma solicitação pendente.
        </div>
      )}

      {!loading && !error && requests.length > 0 && (
        <div className="space-y-3">
          {requests.map((request) => {
            const busy = busyId === request.id;
            return (
              <div key={request.id} className="rounded-2xl p-4 sm:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width: 40, height: 40, background: "#123C7A", color: "#fff", fontWeight: 800 }}>
                        {request.nome.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate" style={{ fontSize: "15px", fontWeight: 800, color: "var(--foreground)" }}>{request.nome}</p>
                        <p className="truncate flex items-center gap-1.5" style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                          <Mail size={12} /> {request.email}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1" style={{ background: "#eef3fc", color: "#123C7A", fontSize: "12px", fontWeight: 700 }}>
                        <UserCheck size={13} /> {getAdvisorName(request)}
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1" style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "12px", fontWeight: 700 }}>
                        <Clock size={13} /> {formatDate(getCreatedAt(request))}
                      </span>
                    </div>
                  </div>

                  <div className="flex gap-2 flex-shrink-0">
                    <button
                      type="button"
                      disabled={Boolean(busyId)}
                      onClick={() => void handleAction(request.id, "approve")}
                      className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5"
                      style={{ background: "#dcfce7", color: "#166534", fontWeight: 800, fontSize: "13px", opacity: Boolean(busyId) && !busy ? 0.55 : 1 }}
                    >
                      <CheckCircle2 size={15} /> {busy ? "Processando..." : "Aprovar"}
                    </button>
                    <button
                      type="button"
                      disabled={Boolean(busyId)}
                      onClick={() => void handleAction(request.id, "reject")}
                      className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5"
                      style={{ background: "#fee2e2", color: "#991b1b", fontWeight: 800, fontSize: "13px", opacity: Boolean(busyId) && !busy ? 0.55 : 1 }}
                    >
                      <XCircle size={15} /> Rejeitar
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && !error && requests.length > 0 && (
        <div className="flex items-start gap-2 rounded-2xl p-4 mt-5" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: "12px", lineHeight: 1.5 }}>
            Aprovar ou rejeitar remove a solicitação desta lista assim que a API confirma a ação.
          </p>
        </div>
      )}
    </div>
  );
}

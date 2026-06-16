import { FormEvent, useCallback, useEffect, useState } from "react";
import { CheckCircle, ChevronLeft, ChevronRight, Search, XCircle } from "lucide-react";

import {
  getAuditLogs,
  type AuditLog,
  type AuditLogFilters,
  type AuditLogPage,
} from "@/api/auditApi";
import { useAuth } from "@/hooks/useAuth";

const PAGE_SIZE = 20;

const emptyFilters: AuditLogFilters = {
  usuario_id: "",
  operacao: "",
  modulo: "",
  resultado_status: "",
  data_inicio: "",
  data_fim: "",
};

function formatTimestamp(value?: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function StatusBadge({ status }: { status: AuditLog["resultado_status"] }) {
  const erro = status === "erro";
  const color = erro ? "#dc2626" : "#1F8A70";
  const bg = erro ? "#fee2e2" : "#dcfce7";
  return (
    <span
      className="flex items-center gap-1 px-2 py-0.5 rounded-lg"
      style={{ background: bg, color, fontSize: "10px", fontWeight: 600 }}
    >
      {erro ? <XCircle size={11} /> : <CheckCircle size={11} />}
      {erro ? "Erro" : "Sucesso"}
    </span>
  );
}

export function AuditPage() {
  const { token } = useAuth();
  const [form, setForm] = useState<AuditLogFilters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<AuditLogFilters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AuditLogPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(
    async (authToken: string): Promise<void> => {
      setLoading(true);
      setError(null);
      try {
        const result = await getAuditLogs(authToken, {
          ...appliedFilters,
          page,
          page_size: PAGE_SIZE,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Falha ao carregar logs");
      } finally {
        setLoading(false);
      }
    },
    [appliedFilters, page],
  );

  useEffect(() => {
    if (token) void loadData(token);
  }, [token, loadData]);

  function applyFilters(event: FormEvent): void {
    event.preventDefault();
    setPage(1);
    setAppliedFilters(form);
  }

  function clearFilters(): void {
    setForm(emptyFilters);
    setAppliedFilters(emptyFilters);
    setPage(1);
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const logs = data?.items ?? [];

  const inputStyle = {
    background: "var(--card)",
    border: "1px solid var(--border)",
    fontSize: "13px",
    color: "var(--foreground)",
  } as const;

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Logs de Auditoria</h1>
        <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
          Registro imutável das operações do sistema (aspecto A02)
        </p>
      </div>

      <form onSubmit={applyFilters} className="flex items-end gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2"
            style={{ color: "var(--muted-foreground)" }}
          />
          <input
            placeholder="Operação (ex: create_student)"
            value={form.operacao}
            onChange={(e) => setForm({ ...form, operacao: e.target.value })}
            className="w-full rounded-xl pl-9 pr-4 py-2 outline-none"
            style={inputStyle}
          />
        </div>
        <input
          placeholder="usuario_id"
          value={form.usuario_id}
          onChange={(e) => setForm({ ...form, usuario_id: e.target.value })}
          className="rounded-xl px-3 py-2 outline-none min-w-[140px]"
          style={inputStyle}
        />
        <input
          placeholder="módulo"
          value={form.modulo}
          onChange={(e) => setForm({ ...form, modulo: e.target.value })}
          className="rounded-xl px-3 py-2 outline-none min-w-[140px]"
          style={inputStyle}
        />
        <select
          value={form.resultado_status}
          onChange={(e) =>
            setForm({ ...form, resultado_status: e.target.value as AuditLogFilters["resultado_status"] })
          }
          className="rounded-xl px-3 py-2 outline-none"
          style={inputStyle}
        >
          <option value="">Todos os status</option>
          <option value="sucesso">Sucesso</option>
          <option value="erro">Erro</option>
        </select>
        <input
          type="date"
          value={form.data_inicio}
          onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
          className="rounded-xl px-3 py-2 outline-none"
          style={inputStyle}
        />
        <input
          type="date"
          value={form.data_fim}
          onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
          className="rounded-xl px-3 py-2 outline-none"
          style={inputStyle}
        />
        <button
          type="submit"
          className="rounded-xl px-4 py-2"
          style={{ background: "#1F8A70", color: "#fff", fontWeight: 600, fontSize: "13px" }}
        >
          Filtrar
        </button>
        <button
          type="button"
          onClick={clearFilters}
          className="rounded-xl px-4 py-2"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}
        >
          Limpar
        </button>
      </form>

      {error && (
        <div
          className="rounded-xl px-4 py-3 mb-4"
          style={{ background: "#fee2e2", color: "#dc2626", fontSize: "13px" }}
        >
          {error}
        </div>
      )}

      <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div
          className="px-4 py-3 flex items-center justify-between"
          style={{ borderBottom: "1px solid var(--border)", background: "var(--muted)" }}
        >
          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>
            {loading ? "Carregando…" : `${total} registro(s)`}
          </p>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
            Página {page} de {totalPages}
          </p>
        </div>

        {!loading && logs.length === 0 ? (
          <div className="p-12 text-center" style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            Nenhum registro encontrado.
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--border)" }}>
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-4 px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="flex-shrink-0" style={{ minWidth: 120 }}>
                  <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--foreground)" }}>
                    {formatTimestamp(log.timestamp)}
                  </p>
                  {log.duracao_ms != null && (
                    <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{log.duracao_ms} ms</p>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                    <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>
                      {log.operacao ?? "—"}
                    </p>
                    {log.role && (
                      <span
                        className="px-1.5 py-0.5 rounded"
                        style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "9px", fontWeight: 600 }}
                      >
                        {log.role}
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                    {log.recurso ?? log.modulo ?? "—"}
                  </p>
                  {log.resultado_status === "erro" && log.erro_mensagem && (
                    <p style={{ fontSize: "11px", color: "#dc2626", marginTop: "2px" }}>{log.erro_mensagem}</p>
                  )}
                  {log.usuario_id && (
                    <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "2px" }}>
                      {log.usuario_id}
                    </p>
                  )}
                </div>

                <div className="flex-shrink-0">
                  <StatusBadge status={log.resultado_status} />
                </div>
              </div>
            ))}
          </div>
        )}

        <div
          className="px-4 py-3 flex items-center justify-end gap-2"
          style={{ borderTop: "1px solid var(--border)", background: "var(--muted)" }}
        >
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
            className="flex items-center gap-1 rounded-lg px-3 py-1.5"
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              fontSize: "12px",
              fontWeight: 600,
              opacity: page <= 1 || loading ? 0.5 : 1,
            }}
          >
            <ChevronLeft size={14} /> Anterior
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
            className="flex items-center gap-1 rounded-lg px-3 py-1.5"
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              color: "var(--foreground)",
              fontSize: "12px",
              fontWeight: 600,
              opacity: page >= totalPages || loading ? 0.5 : 1,
            }}
          >
            Próxima <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

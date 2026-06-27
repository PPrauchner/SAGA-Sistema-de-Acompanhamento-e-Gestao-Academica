import { useEffect, useState, useMemo } from "react";
import { Clock, CheckCircle, XCircle, FileText, AlertTriangle, Filter } from "lucide-react";
import { useApp } from "@/app/context/AppContext";
import { requestsApi, RequestItem } from "@/api/requestsApi";
import * as activitiesApi from "@/api/activitiesApi";
import { coordinationTransfersApi } from "@/api/coordinationTransfersApi";

const TYPE_LABELS: Record<string, string> = {
  atividade: "Atividade Creditável",
  prorrogacao: "Prorrogação",
  transferencia: "Transferência de Orientando",
  transferencia_coordenacao: "Transferência de Coordenação",
};

const STATUS_MAP: Record<string, { label: string; bg: string; color: string; icon: JSX.Element }> = {
  pendente_parecer: { label: "Pendente Parecer", bg: "#fef9c3", color: "#D4A017", icon: <Clock size={12} /> },
  pendente_validacao: { label: "Pendente Validação", bg: "#fef9c3", color: "#D4A017", icon: <AlertTriangle size={12} /> },
  pendente_aprovacao: { label: "Pendente Aprovação", bg: "#fef9c3", color: "#D4A017", icon: <AlertTriangle size={12} /> },
  pendente_aceite: { label: "Aguardando Aceite", bg: "#eef3fc", color: "#123C7A", icon: <Clock size={12} /> },
  pendente: { label: "Pendente", bg: "#fef9c3", color: "#D4A017", icon: <AlertTriangle size={12} /> },
};

export function RequestsPage() {
  const { token, currentUser } = useApp();
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filterTipo, setFilterTipo] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterPeriodo, setFilterPeriodo] = useState<string>("");

  const loadData = async () => {
    if (!token) return;
    try {
      setLoading(true);
      const data = await requestsApi.getRequests(token);
      setRequests(data);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar solicitações");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  const handleAction = async (req: RequestItem, action: "approve" | "reject" | "parecer") => {
    if (!token) return;
    try {
      if (req.tipo === "atividade") {
        if (currentUser?.role === "orientador") {
          await activitiesApi.emitirParecer(token, req.id, "Deferido");
        } else if (currentUser?.role === "coordenacao") {
          await activitiesApi.validarAtividade(token, req.id, { acao: "aprovar", observacao: "" });
        }
      } else if (req.tipo === "transferencia_coordenacao") {
        if (action === "approve") {
          await coordinationTransfersApi.accept(req.id, token);
        }
      }
      await loadData();
    } catch (err: any) {
      alert("Erro na ação: " + err.message);
    }
  };

  const filteredRequests = useMemo(() => {
    return requests.filter((r) => {
      if (filterTipo && r.tipo !== filterTipo) return false;
      if (filterStatus && r.status !== filterStatus) return false;
      if (filterPeriodo && filterPeriodo !== "all") {
        const reqDate = new Date(r.data_solicitacao);
        const daysAgo = (new Date().getTime() - reqDate.getTime()) / (1000 * 3600 * 24);
        if (filterPeriodo === "7" && daysAgo > 7) return false;
        if (filterPeriodo === "30" && daysAgo > 30) return false;
        if (filterPeriodo === "90" && daysAgo > 90) return false;
      }
      return true;
    });
  }, [requests, filterTipo, filterStatus, filterPeriodo]);

  if (loading) {
    return <div className="p-8 text-center">Carregando solicitações...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-red-600">{error}</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Caixa de Entrada (Solicitações)</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            Acompanhe e despache as solicitações pendentes sob sua responsabilidade.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <div className="flex items-center gap-2 rounded-xl px-3 py-2.5" style={{ background: "var(--card)", border: "1px solid var(--border)", height: "42px" }}>
          <Filter size={15} style={{ color: "var(--muted-foreground)" }} />
          <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>Filtros:</span>
        </div>
        <select
          value={filterTipo}
          onChange={(e) => setFilterTipo(e.target.value)}
          className="rounded-xl px-3 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)", height: "42px" }}
        >
          <option value="">Todos os Tipos</option>
          {Object.entries(TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-xl px-3 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)", height: "42px" }}
        >
          <option value="">Todos os Status</option>
          {Object.entries(STATUS_MAP).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <select
          value={filterPeriodo}
          onChange={(e) => setFilterPeriodo(e.target.value)}
          className="rounded-xl px-3 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)", height: "42px" }}
        >
          <option value="all">Qualquer Período</option>
          <option value="7">Últimos 7 dias</option>
          <option value="30">Últimos 30 dias</option>
          <option value="90">Últimos 90 dias</option>
        </select>
      </div>

      <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--muted)" }}>
              {["Tipo", "Solicitante", "Data", "Status", "Ações"].map((h) => (
                <th
                  key={h}
                  className={`px-4 py-3 text-sm ${h === "Ações" ? "text-center" : "text-left"}`}
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "var(--muted-foreground)",
                    textTransform: "uppercase",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRequests.map((req, i) => (
              <tr
                key={req.id}
                style={{
                  borderBottom: i < filteredRequests.length - 1 ? "1px solid var(--border)" : "none",
                }}
              >
                <td className="px-4 py-3 text-sm font-medium" style={{ color: "var(--foreground)" }}>
                  {TYPE_LABELS[req.tipo] || req.tipo}
                </td>
                <td className="px-4 py-3 text-sm" style={{ color: "var(--muted-foreground)" }}>
                  {req.solicitante_nome}
                </td>
                <td className="px-4 py-3 text-sm" style={{ color: "var(--muted-foreground)" }}>
                  {new Date(req.data_solicitacao).toLocaleDateString("pt-BR")}
                </td>
                <td className="px-4 py-3">
                  <span
                    className="flex items-center gap-1 px-2 py-1 rounded-lg w-fit"
                    style={{
                      background: STATUS_MAP[req.status]?.bg || "#eee",
                      color: STATUS_MAP[req.status]?.color || "#333",
                      fontSize: "11px",
                      fontWeight: 600,
                    }}
                  >
                    {STATUS_MAP[req.status]?.icon} {STATUS_MAP[req.status]?.label || req.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm flex gap-2 justify-center">
                  <button
                    onClick={() => handleAction(req, "approve")}
                    className="p-1.5 rounded-lg text-green-600 hover:bg-green-50 transition-colors"
                    title="Aprovar / Aceitar"
                  >
                    <CheckCircle size={15} />
                  </button>
                  <button
                    onClick={() => handleAction(req, "reject")}
                    className="p-1.5 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
                    title="Rejeitar"
                  >
                    <XCircle size={15} />
                  </button>
                  <button
                    className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                    title="Ver Detalhes"
                  >
                    <FileText size={15} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredRequests.length === 0 && (
          <div className="text-center py-12">
            <FileText size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
            <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Nenhuma solicitação encontrada</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { Search, Filter, Shield, User, FileText, Settings, Trash2, Eye, Edit3, Plus, Download } from "lucide-react";

const AUDIT_LOGS = [
  { id: "1", timestamp: "2025-03-01 14:32:18", usuario: "roberto.almeida@ppg.ufx.br", role: "coordenacao", acao: "UPDATE", modulo: "alunos", recurso: "Aluno #2023001", detalhes: "Alterou status de 'regular' para 'atenção'", ip: "192.168.1.10", severity: "medium" },
  { id: "2", timestamp: "2025-03-01 13:21:45", usuario: "carla.mendes@ppg.ufx.br", role: "orientador", acao: "CREATE", modulo: "relatorios", recurso: "Relatório Semestral #RS-2025-001", detalhes: "Submeteu relatório semestral para aprovação", ip: "192.168.1.25", severity: "low" },
  { id: "3", timestamp: "2025-03-01 11:05:33", usuario: "ana.costa@pos.ufx.br", role: "aluno", acao: "UPLOAD", modulo: "producoes", recurso: "Produção #P-2025-015", detalhes: "Enviou comprovante de publicação IEEE Transactions", ip: "192.168.2.50", severity: "low" },
  { id: "4", timestamp: "2025-03-01 10:45:12", usuario: "roberto.almeida@ppg.ufx.br", role: "coordenacao", acao: "APPROVE", modulo: "prorrogacoes", recurso: "Prorrogação #PRO-2025-003", detalhes: "Aprovou solicitação de prorrogação de Ana Paula Costa", ip: "192.168.1.10", severity: "high" },
  { id: "5", timestamp: "2025-03-01 09:30:00", usuario: "sistema@ppg.ufx.br", role: "sistema", acao: "AUTO", modulo: "inferencia", recurso: "Análise #INF-20250301", detalhes: "Motor de inferência processou 248 alunos automaticamente", ip: "127.0.0.1", severity: "info" },
  { id: "6", timestamp: "2025-02-28 16:55:22", usuario: "carlos.lima@pos.ufx.br", role: "aluno", acao: "LOGIN", modulo: "autenticacao", recurso: "Sessão #S-2025-10231", detalhes: "Login realizado com sucesso", ip: "192.168.3.75", severity: "info" },
  { id: "7", timestamp: "2025-02-28 15:10:08", usuario: "roberto.almeida@ppg.ufx.br", role: "coordenacao", acao: "DELETE", modulo: "atividades", recurso: "Atividade #A-2025-021", detalhes: "Removeu atividade duplicada do aluno Marcos Oliveira", ip: "192.168.1.10", severity: "high" },
  { id: "8", timestamp: "2025-02-28 14:00:00", usuario: "sistema@ppg.ufx.br", role: "sistema", acao: "BACKUP", modulo: "sistema", recurso: "Backup Automático", detalhes: "Backup completo realizado com sucesso", ip: "127.0.0.1", severity: "info" },
];

const ACAO_MAP: Record<string, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  CREATE: { label: "Criação", icon: <Plus size={12} />, color: "#1F8A70", bg: "#dcfce7" },
  UPDATE: { label: "Atualização", icon: <Edit3 size={12} />, color: "#123C7A", bg: "#eef3fc" },
  DELETE: { label: "Exclusão", icon: <Trash2 size={12} />, color: "#dc2626", bg: "#fee2e2" },
  VIEW: { label: "Visualização", icon: <Eye size={12} />, color: "#8b5cf6", bg: "#ede9fe" },
  APPROVE: { label: "Aprovação", icon: <Shield size={12} />, color: "#D4A017", bg: "#fef9c3" },
  LOGIN: { label: "Login", icon: <User size={12} />, color: "#3b82f6", bg: "#dbeafe" },
  UPLOAD: { label: "Upload", icon: <FileText size={12} />, color: "#1F8A70", bg: "#dcfce7" },
  AUTO: { label: "Automático", icon: <Settings size={12} />, color: "#94a3b8", bg: "#f1f5f9" },
  BACKUP: { label: "Backup", icon: <Shield size={12} />, color: "#94a3b8", bg: "#f1f5f9" },
};

const SEVERITY_MAP = {
  high: { label: "Alto", color: "#dc2626", bg: "#fee2e2" },
  medium: { label: "Médio", color: "#D4A017", bg: "#fef9c3" },
  low: { label: "Baixo", color: "#1F8A70", bg: "#dcfce7" },
  info: { label: "Info", color: "#3b82f6", bg: "#dbeafe" },
};

const ROLE_MAP: Record<string, { label: string; color: string }> = {
  coordenacao: { label: "Coordenação", color: "#123C7A" },
  orientador: { label: "Orientador", color: "#1F8A70" },
  aluno: { label: "Aluno", color: "#D4A017" },
  sistema: { label: "Sistema", color: "#94a3b8" },
};

export function AuditPage() {
  const [search, setSearch] = useState("");
  const [filterAcao, setFilterAcao] = useState("todas");
  const [filterModulo, setFilterModulo] = useState("todos");
  const [filterSeverity, setFilterSeverity] = useState("todos");

  const filtered = AUDIT_LOGS.filter((log) => {
    const matchSearch = log.usuario.toLowerCase().includes(search.toLowerCase()) ||
      log.detalhes.toLowerCase().includes(search.toLowerCase()) ||
      log.recurso.toLowerCase().includes(search.toLowerCase());
    const matchAcao = filterAcao === "todas" || log.acao === filterAcao;
    const matchModulo = filterModulo === "todos" || log.modulo === filterModulo;
    const matchSeverity = filterSeverity === "todos" || log.severity === filterSeverity;
    return matchSearch && matchAcao && matchModulo && matchSeverity;
  });

  const modulos = [...new Set(AUDIT_LOGS.map(l => l.modulo))];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Logs de Auditoria</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Registro completo de atividades do sistema</p>
        </div>
        <button className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#1F8A70", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Download size={16} /> Exportar Logs
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total de Logs", value: AUDIT_LOGS.length, color: "#123C7A", bg: "#eef3fc" },
          { label: "Ações Críticas", value: AUDIT_LOGS.filter(l => l.severity === "high").length, color: "#dc2626", bg: "#fee2e2" },
          { label: "Hoje", value: AUDIT_LOGS.filter(l => l.timestamp.startsWith("2025-03-01")).length, color: "#1F8A70", bg: "#dcfce7" },
          { label: "Usuários Únicos", value: new Set(AUDIT_LOGS.map(l => l.usuario)).size, color: "#D4A017", bg: "#fef9c3" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-2xl p-4" style={{ background: stat.bg }}>
            <p style={{ fontSize: "26px", fontWeight: 800, color: stat.color }}>{stat.value}</p>
            <p style={{ fontSize: "12px", color: stat.color, fontWeight: 600 }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
          <input
            placeholder="Buscar nos logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl pl-9 pr-4 py-2 outline-none"
            style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
          />
        </div>
        {[
          { value: filterAcao, onChange: setFilterAcao, options: [["todas", "Todas as Ações"], ...Object.keys(ACAO_MAP).map(k => [k, ACAO_MAP[k].label])], label: "Ação" },
          { value: filterModulo, onChange: setFilterModulo, options: [["todos", "Todos os Módulos"], ...modulos.map(m => [m, m])], label: "Módulo" },
          { value: filterSeverity, onChange: setFilterSeverity, options: [["todos", "Severidade"], ...Object.entries(SEVERITY_MAP).map(([k, v]) => [k, v.label])], label: "Severidade" },
        ].map((filter, i) => (
          <select
            key={i}
            value={filter.value}
            onChange={(e) => filter.onChange(e.target.value)}
            className="rounded-xl px-3 py-2 outline-none"
            style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
          >
            {filter.options.map(([val, lbl]) => <option key={val} value={val}>{lbl}</option>)}
          </select>
        ))}
      </div>

      <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border)", background: "var(--muted)" }}>
          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>{filtered.length} registros encontrados</p>
          <p className="hidden sm:block" style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Última atualização: 01/03/2025 14:32</p>
        </div>

        {/* Mobile card layout */}
        <div className="md:hidden divide-y" style={{ borderColor: "var(--border)" }}>
          {filtered.map((log) => {
            const acao = ACAO_MAP[log.acao] || ACAO_MAP.AUTO;
            const severity = SEVERITY_MAP[log.severity as keyof typeof SEVERITY_MAP];
            const role = ROLE_MAP[log.role] || { label: log.role, color: "#94a3b8" };
            return (
              <div key={log.id} className="p-4" style={{ borderBottom: "1px solid var(--border)" }}>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: acao.bg, color: acao.color, fontSize: "10px", fontWeight: 700 }}>
                      {acao.icon} {acao.label}
                    </span>
                    <span className="px-1.5 py-0.5 rounded-lg" style={{ background: severity.bg, color: severity.color, fontSize: "10px", fontWeight: 600 }}>
                      {severity.label}
                    </span>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p style={{ fontSize: "10px", fontWeight: 600, color: "var(--foreground)" }}>{log.timestamp.split(" ")[1]}</p>
                    <p style={{ fontSize: "9px", color: "var(--muted-foreground)" }}>{new Date(log.timestamp.split(" ")[0]).toLocaleDateString("pt-BR")}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{log.usuario}</p>
                  <span className="px-1.5 py-0.5 rounded" style={{ background: `${role.color}18`, color: role.color, fontSize: "9px", fontWeight: 600 }}>
                    {role.label}
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--muted-foreground)", lineHeight: 1.5 }}>{log.detalhes}</p>
                <div className="flex items-center justify-between mt-2">
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{log.modulo} › {log.recurso}</p>
                  <p style={{ fontSize: "10px", fontFamily: "monospace", color: "var(--muted-foreground)" }}>{log.ip}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Desktop table layout */}
        <div className="hidden md:block divide-y" style={{ borderColor: "var(--border)" }}>
          {filtered.map((log) => {
            const acao = ACAO_MAP[log.acao] || ACAO_MAP.AUTO;
            const severity = SEVERITY_MAP[log.severity as keyof typeof SEVERITY_MAP];
            const role = ROLE_MAP[log.role] || { label: log.role, color: "#94a3b8" };

            return (
              <div
                key={log.id}
                className="flex items-start gap-4 px-4 py-3 transition-colors"
                style={{ borderBottom: "1px solid var(--border)" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
              >
                {/* Severity indicator */}
                <div className="flex-shrink-0 mt-1">
                  <div className="w-2 h-2 rounded-full" style={{ background: severity.color }} />
                </div>

                {/* Timestamp */}
                <div className="flex-shrink-0" style={{ minWidth: 80 }}>
                  <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--foreground)" }}>
                    {log.timestamp.split(" ")[1]}
                  </p>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>
                    {new Date(log.timestamp.split(" ")[0]).toLocaleDateString("pt-BR")}
                  </p>
                </div>

                {/* Action badge */}
                <div className="flex-shrink-0">
                  <span className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: acao.bg, color: acao.color, fontSize: "11px", fontWeight: 600 }}>
                    {acao.icon} {acao.label}
                  </span>
                </div>

                {/* Main content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                    <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{log.usuario}</p>
                    <span className="px-1.5 py-0.5 rounded" style={{ background: `${role.color}18`, color: role.color, fontSize: "9px", fontWeight: 600 }}>
                      {role.label}
                    </span>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{log.detalhes}</p>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "2px" }}>
                    {log.modulo} › {log.recurso}
                  </p>
                </div>

                {/* IP */}
                <div className="flex-shrink-0 text-right" style={{ minWidth: 90 }}>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>IP</p>
                  <p style={{ fontSize: "11px", fontFamily: "monospace", color: "var(--foreground)" }}>{log.ip}</p>
                </div>

                {/* Severity badge */}
                <div className="flex-shrink-0">
                  <span className="px-2 py-0.5 rounded-lg" style={{ background: severity.bg, color: severity.color, fontSize: "10px", fontWeight: 600 }}>
                    {severity.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

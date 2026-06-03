import { useState } from "react";
import { Plus, Clock, CheckCircle, XCircle, AlertTriangle, FileText, Calendar } from "lucide-react";

const EXTENSIONS = [
  { id: "1", aluno: "Ana Paula Costa", matricula: "2021003", nivel: "Doutorado", tipo: "prazo_defesa", motivo: "Necessidade de mais experimentos para validação do modelo proposto. Os resultados iniciais foram promissores, mas a análise estatística indicou a necessidade de dados adicionais para robustez científica.", dataAtual: "2025-12-31", novaData: "2026-06-30", status: "aprovado", solicitacao: "2024-10-15", parecer: "Aprovado pelo orientador e coordenação. Justificativa aceita." },
  { id: "2", aluno: "Carlos Eduardo Lima", matricula: "2022001", nivel: "Mestrado", tipo: "prazo_qualificacao", motivo: "Problemas de saúde que impediram o andamento regular das atividades acadêmicas. Laudo médico anexado.", dataAtual: "2025-03-31", novaData: "2025-08-31", status: "pendente", solicitacao: "2025-02-01", parecer: null },
  { id: "3", aluno: "Marcos Oliveira", matricula: "2023001", nivel: "Mestrado", tipo: "prazo_defesa", motivo: "Orientador assumiu cargo administrativo e houve redução das reuniões de orientação no período.", dataAtual: "2025-06-30", novaData: "2025-12-31", status: "em_analise", solicitacao: "2025-01-20", parecer: "Em análise pelo colegiado." },
  { id: "4", aluno: "Lucas Ferreira", matricula: "2022003", nivel: "Mestrado", tipo: "trancamento", motivo: "Motivo pessoal relevante com documentação comprobatória.", dataAtual: "2025-12-31", novaData: "2026-06-30", status: "reprovado", solicitacao: "2024-11-30", parecer: "Reprovado. Não atende aos critérios do regulamento." },
];

const STATUS_MAP = {
  aprovado: { label: "Aprovado", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={14} /> },
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fef9c3", icon: <Clock size={14} /> },
  em_analise: { label: "Em Análise", color: "#123C7A", bg: "#eef3fc", icon: <AlertTriangle size={14} /> },
  reprovado: { label: "Reprovado", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} /> },
};

const TIPO_MAP: Record<string, string> = {
  prazo_defesa: "Prorrogação de Prazo de Defesa",
  prazo_qualificacao: "Prorrogação de Qualificação",
  trancamento: "Trancamento de Matrícula",
  mudanca_nivel: "Mudança de Nível",
};

export function ExtensionsPage() {
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div className="min-w-0">
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Prorrogações e Solicitações</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Gerenciamento de solicitações de extensão de prazo</p>
        </div>
        <button onClick={() => setShowForm(true)} className="flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 flex-shrink-0 self-start sm:self-auto" style={{ background: "var(--primary)", color: "var(--primary-foreground)", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> <span className="whitespace-nowrap">Nova Solicitação</span>
        </button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        {Object.entries(STATUS_MAP).map(([key, val]) => (
          <div key={key} className="rounded-2xl p-3 sm:p-4 flex items-center gap-3 min-w-0" style={{ background: val.bg }}>
            <span className="flex-shrink-0" style={{ color: val.color }}>{val.icon}</span>
            <div className="min-w-0">
              <p style={{ fontSize: "22px", fontWeight: 800, color: val.color, lineHeight: 1.1 }}>{EXTENSIONS.filter(e => e.status === key).length}</p>
              <p className="truncate" style={{ fontSize: "12px", color: val.color, fontWeight: 600 }}>{val.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        {EXTENSIONS.map((ext) => {
          const status = STATUS_MAP[ext.status as keyof typeof STATUS_MAP];
          const isExpanded = expandedId === ext.id;

          return (
            <div
              key={ext.id}
              className="rounded-2xl overflow-hidden transition-all"
              style={{ background: "var(--card)", border: `1px solid ${isExpanded ? "#123C7A" : "var(--border)"}` }}
            >
              <div className="p-4 sm:p-5 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : ext.id)}>
                <div className="flex flex-col sm:flex-row items-start justify-between gap-3 sm:gap-4">
                  <div className="flex-1 min-w-0 w-full">
                    <div className="flex items-center gap-3 mb-2 min-w-0">
                      <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width: 36, height: 36, background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "13px", fontWeight: 700 }}>
                        {ext.aluno.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate" style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{ext.aluno}</p>
                        <p className="truncate" style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Mat. {ext.matricula} · {ext.nivel}</p>
                      </div>
                    </div>
                    <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--tint-blue-text)", marginBottom: "8px", wordBreak: "break-word" }}>
                      {TIPO_MAP[ext.tipo] || ext.tipo}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <Calendar size={12} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
                        <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Prazo: {new Date(ext.dataAtual).toLocaleDateString("pt-BR")}</span>
                      </div>
                      <span style={{ color: "var(--muted-foreground)" }}>→</span>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--tint-blue-text)" }}>Novo: {new Date(ext.novaData).toLocaleDateString("pt-BR")}</span>
                    </div>
                  </div>
                  <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-start">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg flex-shrink-0" style={{ background: status.bg, color: status.color, fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                      {status.icon} {status.label}
                    </span>
                    <span className="truncate" style={{ fontSize: "10px", color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>
                      {new Date(ext.solicitacao).toLocaleDateString("pt-BR")}
                    </span>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-5 pb-5 border-t" style={{ borderColor: "var(--border)" }}>
                  <div className="pt-4 space-y-4">
                    <div>
                      <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                        Justificativa
                      </p>
                      <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, padding: "12px", background: "var(--muted)", borderRadius: "8px" }}>
                        {ext.motivo}
                      </p>
                    </div>

                    {ext.parecer && (
                      <div>
                        <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                          Parecer
                        </p>
                        <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, padding: "12px", background: status.bg, borderRadius: "8px", borderLeft: `3px solid ${status.color}` }}>
                          {ext.parecer}
                        </p>
                      </div>
                    )}

                    {(ext.status === "pendente" || ext.status === "em_analise") && (
                      <div className="flex gap-3 pt-2">
                        <button className="flex items-center gap-2 px-4 py-2 rounded-xl" style={{ background: "#dcfce7", color: "#1F8A70", fontWeight: 600, fontSize: "13px" }}>
                          <CheckCircle size={14} /> Aprovar
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2 rounded-xl" style={{ background: "#fee2e2", color: "#dc2626", fontWeight: 600, fontSize: "13px" }}>
                          <XCircle size={14} /> Reprovar
                        </button>
                        <button className="flex items-center gap-2 px-4 py-2 rounded-xl" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "13px" }}>
                          <FileText size={14} /> Solicitar Info
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <div className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Nova Solicitação</h2>
              <button onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>✕</button>
            </div>
            <div className="space-y-4">
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Tipo de Solicitação</label>
                <select className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                  {Object.entries(TIPO_MAP).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Data Prazo Atual</label>
                  <input type="date" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Nova Data Solicitada</label>
                  <input type="date" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Justificativa Detalhada</label>
                <textarea
                  rows={4}
                  placeholder="Descreva detalhadamente o motivo da solicitação..."
                  className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                  onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Documentos Comprobatórios</label>
                <div className="rounded-xl p-4 text-center border-2 border-dashed cursor-pointer" style={{ borderColor: "var(--border)" }}>
                  <p style={{ color: "var(--muted-foreground)", fontSize: "13px" }}>Anexar documentos (opcional)</p>
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600 }}>Enviar Solicitação</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

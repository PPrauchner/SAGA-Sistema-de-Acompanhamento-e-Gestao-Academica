import { useState, type FocusEvent, type ReactNode } from "react";
import { Plus, Clock, CheckCircle, XCircle, FileText, Calendar } from "lucide-react";
import { toast } from "sonner";
import { useExtensionsApi, type Extension, type ExtensionTipo } from "@/api/extensions";

const STATUS_MAP: Record<string, { label: string; color: string; bg: string; icon: ReactNode }> = {
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fef9c3", icon: <Clock size={14} /> },
  aprovada: { label: "Aprovada", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={14} /> },
  rejeitada: { label: "Rejeitada", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} /> },
};

const TIPO_MAP: Record<ExtensionTipo, string> = {
  prazo_defesa: "Prorrogação de Prazo de Defesa",
  prazo_qualificacao: "Prorrogação de Qualificação",
  trancamento: "Trancamento de Matrícula",
  mudanca_nivel: "Mudança de Nível",
};

const formatDate = (value?: string | null): string =>
  value ? new Date(value).toLocaleDateString("pt-BR") : "—";

export function ExtensionsPage() {
  const { extensions, loading, role, createRequest, submitReview, submitDecision } = useExtensionsApi();

  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Estados do modal de nova solicitação.
  const [tipoSol, setTipoSol] = useState<ExtensionTipo>("prazo_defesa");
  const [novaData, setNovaData] = useState("");
  const [motivo, setMotivo] = useState("");
  const [planoAtualizado, setPlanoAtualizado] = useState("");
  const [parecerTexto, setParecerTexto] = useState("");

  const handleCreateRequest = async () => {
    if (!motivo.trim() || motivo.trim().length < 10) {
      toast.error("Descreva a justificativa (mínimo 10 caracteres).");
      return;
    }
    if (!novaData) {
      toast.error("Informe a nova data solicitada.");
      return;
    }
    if (!planoAtualizado.trim()) {
      toast.error("Descreva o plano de trabalho atualizado.");
      return;
    }
    try {
      await createRequest({
        tipo: tipoSol,
        motivo: motivo.trim(),
        plano_atualizado: planoAtualizado.trim(),
        nova_data: new Date(novaData).toISOString(),
      });
      setMotivo("");
      setNovaData("");
      setPlanoAtualizado("");
      setShowForm(false);
      toast.success("Solicitação de prorrogação enviada.");
    } catch {
      toast.error("Erro ao criar a solicitação.");
    }
  };

  const handleReview = async (extensionId: string) => {
    if (!parecerTexto.trim() || parecerTexto.trim().length < 10) {
      toast.error("Escreva o parecer (mínimo 10 caracteres).");
      return;
    }
    try {
      await submitReview(extensionId, parecerTexto.trim());
      setParecerTexto("");
      toast.success("Parecer registrado.");
    } catch {
      toast.error("Erro ao registrar o parecer.");
    }
  };

  const handleDecision = async (extensionId: string, acao: "aprovar" | "rejeitar") => {
    try {
      await submitDecision(extensionId, acao);
      toast.success(acao === "aprovar" ? "Prorrogação deferida." : "Prorrogação indeferida.");
    } catch {
      toast.error("Erro ao homologar a decisão.");
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center" style={{ color: "var(--muted-foreground)" }}>
        Carregando solicitações...
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div className="min-w-0">
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Prorrogações e Solicitações</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Gerenciamento de solicitações de extensão de prazo</p>
        </div>

        {role === "aluno" && (
          <button onClick={() => setShowForm(true)} className="flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 flex-shrink-0 self-start sm:self-auto" style={{ background: "var(--primary)", color: "var(--primary-foreground)", fontWeight: 600, fontSize: "14px" }}>
            <Plus size={16} /> <span className="whitespace-nowrap">Nova Solicitação</span>
          </button>
        )}
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 mb-6">
        {Object.entries(STATUS_MAP).map(([key, val]) => (
          <div key={key} className="rounded-2xl p-3 sm:p-4 flex items-center gap-3 min-w-0" style={{ background: val.bg }}>
            <span className="flex-shrink-0" style={{ color: val.color }}>{val.icon}</span>
            <div className="min-w-0">
              <p style={{ fontSize: "22px", fontWeight: 800, color: val.color, lineHeight: 1.1 }}>
                {extensions.filter((e) => e.status === key).length}
              </p>
              <p className="truncate" style={{ fontSize: "12px", color: val.color, fontWeight: 600 }}>{val.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Lista de Extensões */}
      <div className="space-y-3">
        {extensions.map((ext: Extension) => {
          const status = STATUS_MAP[ext.status] || STATUS_MAP.pendente;
          const isExpanded = expandedId === ext.id;
          const nomeAluno = ext.student_nome || "Aluno";

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
                        {nomeAluno.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate" style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{nomeAluno}</p>
                        <p className="truncate" style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Novo prazo solicitado: {formatDate(ext.nova_data)}</p>
                      </div>
                    </div>
                    <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--tint-blue-text)", marginBottom: "8px", wordBreak: "break-word" }}>
                      {TIPO_MAP[ext.tipo] || "Prorrogação"}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <Calendar size={12} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
                        <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Solicitado em: {formatDate(ext.created_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-start">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg flex-shrink-0" style={{ background: status.bg, color: status.color, fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                      {status.icon} {status.label}
                    </span>
                    <span className="truncate" style={{ fontSize: "10px", color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>
                      {formatDate(ext.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              {isExpanded && (
                <div className="px-5 pb-5 border-t" style={{ borderColor: "var(--border)" }}>
                  <div className="pt-4 space-y-4">
                    <div>
                      <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                        Justificativa e Plano
                      </p>
                      <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, padding: "12px", background: "var(--muted)", borderRadius: "8px" }}>
                        <strong>Motivo:</strong> {ext.motivo} <br />
                        <span className="block mt-2 font-medium text-xs text-[var(--muted-foreground)]">{ext.plano_atualizado}</span>
                      </p>
                    </div>

                    <div className="flex items-center gap-6 flex-wrap" style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                      <span>Novo prazo solicitado: <strong style={{ color: "var(--foreground)" }}>{formatDate(ext.nova_data)}</strong></span>
                      {ext.status === "aprovada" && (
                        <span>Prazo homologado: <strong style={{ color: "#1F8A70" }}>{formatDate(ext.prazo_novo)}</strong></span>
                      )}
                    </div>

                    {ext.parecer_orientador && (
                      <div>
                        <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>
                          Parecer do Orientador
                        </p>
                        <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, padding: "12px", background: "#eef3fc", borderRadius: "8px", borderLeft: `3px solid #123C7A` }}>
                          {ext.parecer_orientador}
                        </p>
                      </div>
                    )}

                    {ext.status === "pendente" && (
                      <div className="flex flex-col gap-2 pt-2">
                        {role === "orientador" && !ext.parecer_orientador && (
                          <div className="w-full mb-2">
                            <input
                              type="text"
                              placeholder="Escreva o parecer técnico..."
                              className="w-full rounded-xl px-3 py-2 outline-none mb-2"
                              style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}
                              value={parecerTexto}
                              onChange={(e) => setParecerTexto(e.target.value)}
                            />
                            <button
                              onClick={() => handleReview(ext.id)}
                              className="flex items-center gap-2 px-4 py-2 rounded-xl"
                              style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "13px" }}
                            >
                              <FileText size={14} /> Salvar Parecer do Orientador
                            </button>
                          </div>
                        )}

                        {role === "coordenacao" && (
                          <div className="flex gap-3">
                            <button onClick={() => handleDecision(ext.id, "aprovar")} className="flex items-center gap-2 px-4 py-2 rounded-xl" style={{ background: "#dcfce7", color: "#1F8A70", fontWeight: 600, fontSize: "13px" }}>
                              <CheckCircle size={14} /> Deferir (Aprovar)
                            </button>
                            <button onClick={() => handleDecision(ext.id, "rejeitar")} className="flex items-center gap-2 px-4 py-2 rounded-xl" style={{ background: "#fee2e2", color: "#dc2626", fontWeight: 600, fontSize: "13px" }}>
                              <XCircle size={14} /> Indeferir (Rejeitar)
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Modal */}
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
                <select value={tipoSol} onChange={(e) => setTipoSol(e.target.value as ExtensionTipo)} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                  {(Object.entries(TIPO_MAP) as [ExtensionTipo, string][]).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Nova Data Solicitada</label>
                <input type="date" value={novaData} onChange={(e) => setNovaData(e.target.value)} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Justificativa Detalhada</label>
                <textarea
                  rows={4}
                  placeholder="Descreva detalhadamente o motivo da solicitação..."
                  className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  onFocus={(e: FocusEvent<HTMLTextAreaElement>) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                  onBlur={(e: FocusEvent<HTMLTextAreaElement>) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Plano de Trabalho Atualizado</label>
                <textarea
                  rows={3}
                  placeholder="Descreva o plano de trabalho revisado (ou cole o link do documento)..."
                  className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}
                  value={planoAtualizado}
                  onChange={(e) => setPlanoAtualizado(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={handleCreateRequest} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600 }}>Enviar Solicitação</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

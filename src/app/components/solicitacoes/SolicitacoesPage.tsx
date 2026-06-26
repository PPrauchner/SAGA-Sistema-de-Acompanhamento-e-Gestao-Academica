import { useEffect, useState } from "react";
import { Plus, Clock, CheckCircle, XCircle, AlertTriangle, FileText, Calendar } from "lucide-react";

import { solicitacoesApi, type Solicitacao } from "@/api/solicitacoesApi";
import { useApp } from "../../context/AppContext";

const STATUS_MAP = {
  aprovado: { label: "Aprovado", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={14} /> },
  aprovada: { label: "Aprovada", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={14} /> },
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fef9c3", icon: <Clock size={14} /> },
  em_analise: { label: "Em Análise", color: "#123C7A", bg: "#eef3fc", icon: <AlertTriangle size={14} /> },
  reprovado: { label: "Reprovado", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} /> },
  rejeitado: { label: "Rejeitado", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} /> },
  rejeitada: { label: "Rejeitada", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={14} /> },
};

const TIPO_MAP: Record<string, string> = {
  prazo_defesa: "Prorrogação de Prazo de Defesa",
  prazo_qualificacao: "Prorrogação de Qualificação",
  trancamento: "Trancamento de Matrícula",
  mudanca_nivel: "Mudança de Nível",
};

function getStatus(status: string) {
  return STATUS_MAP[status as keyof typeof STATUS_MAP] ?? {
    label: status || "Indefinido",
    color: "#64748b",
    bg: "var(--muted)",
    icon: <AlertTriangle size={14} />,
  };
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

function getStudentId(solicitacao: Solicitacao): string | null {
  return solicitacao.student_id ?? solicitacao.aluno_id ?? null;
}

function getStudentName(solicitacao: Solicitacao): string {
  return solicitacao.aluno_nome ?? solicitacao.aluno ?? "Aluno não informado";
}

function getCurrentDate(solicitacao: Solicitacao): string | null {
  return solicitacao.data_atual ?? solicitacao.prazo_atual ?? solicitacao.dataAtual ?? null;
}

function getProposedDate(solicitacao: Solicitacao): string | null {
  return solicitacao.nova_data ?? solicitacao.prazo_novo ?? solicitacao.novaData ?? null;
}

function getCreatedAt(solicitacao: Solicitacao): string | null {
  return solicitacao.created_at ?? solicitacao.solicitacao ?? null;
}

export function SolicitacoesPage() {
  const { currentUser, token } = useApp();
  const [solicitacoes, setSolicitacoes] = useState<Solicitacao[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const canCreateRequest = currentUser?.role === "aluno" || currentUser?.role === "orientador";
  const isStudentRequest = currentUser?.role === "aluno";
  const isAdvisorRequest = currentUser?.role === "orientador";
  const advisorStudents: Array<{ id: string; nome: string; matricula?: string }> = [];

  useEffect(() => {
    if (!token) return;
    const authToken = token;
    let active = true;

    async function loadSolicitacoes() {
      setLoading(true);
      setError(null);
      try {
        const data = await solicitacoesApi.list(authToken);
        if (active) setSolicitacoes(data);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Falha ao carregar solicitações");
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadSolicitacoes();
    return () => {
      active = false;
    };
  }, [token]);

  const visibleSolicitacoes = solicitacoes.filter((solicitacao) => {
    if (currentUser?.role !== "aluno") return true;
    const studentId = getStudentId(solicitacao);
    return !studentId || studentId === currentUser.student_id;
  });

  function openRequestForm(): void {
    setSelectedStudentId(isStudentRequest ? currentUser?.student_id ?? currentUser?.id ?? "" : "");
    setShowForm(true);
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div className="min-w-0">
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Solicitações</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Acompanhe solicitações acadêmicas e prorrogações</p>
        </div>
        {canCreateRequest && (
          <button onClick={openRequestForm} className="flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 flex-shrink-0 self-start sm:self-auto" style={{ background: "var(--primary)", color: "var(--primary-foreground)", fontWeight: 600, fontSize: "14px" }}>
            <Plus size={16} /> <span className="whitespace-nowrap">Nova Solicitação</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        {Object.entries(STATUS_MAP).slice(0, 4).map(([key, val]) => (
          <div key={key} className="rounded-2xl p-3 sm:p-4 flex items-center gap-3 min-w-0" style={{ background: val.bg }}>
            <span className="flex-shrink-0" style={{ color: val.color }}>{val.icon}</span>
            <div className="min-w-0">
              <p style={{ fontSize: "22px", fontWeight: 800, color: val.color, lineHeight: 1.1 }}>{visibleSolicitacoes.filter((item) => item.status === key).length}</p>
              <p className="truncate" style={{ fontSize: "12px", color: val.color, fontWeight: 600 }}>{val.label}</p>
            </div>
          </div>
        ))}
      </div>

      {loading && (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Carregando solicitações...
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl p-5" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca" }}>
          {error}
        </div>
      )}

      {!loading && !error && visibleSolicitacoes.length === 0 && (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Nenhuma solicitação encontrada.
        </div>
      )}

      {!loading && !error && visibleSolicitacoes.length > 0 && (
        <div className="space-y-3">
          {visibleSolicitacoes.map((solicitacao) => {
            const status = getStatus(solicitacao.status);
            const isExpanded = expandedId === solicitacao.id;
            const tipo = solicitacao.tipo ? TIPO_MAP[solicitacao.tipo] ?? solicitacao.tipo : "Tipo não informado";
            const aluno = getStudentName(solicitacao);
            const createdAt = getCreatedAt(solicitacao);
            const novaData = getProposedDate(solicitacao);

            return (
              <div key={solicitacao.id} className="rounded-2xl overflow-hidden transition-all" style={{ background: "var(--card)", border: `1px solid ${isExpanded ? "#123C7A" : "var(--border)"}` }}>
                <div className="p-4 sm:p-5 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : solicitacao.id)}>
                  <div className="flex flex-col sm:flex-row items-start justify-between gap-3 sm:gap-4">
                    <div className="flex-1 min-w-0 w-full">
                      <div className="flex items-center gap-3 mb-2 min-w-0">
                        <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width: 36, height: 36, background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "13px", fontWeight: 700 }}>
                          {aluno.charAt(0)}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate" style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{aluno}</p>
                          <p className="truncate" style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                            {solicitacao.matricula ? `Mat. ${solicitacao.matricula}` : "Matrícula não informada"}{solicitacao.nivel ? ` · ${solicitacao.nivel}` : ""}
                          </p>
                        </div>
                      </div>
                      <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--tint-blue-text)", marginBottom: "8px", wordBreak: "break-word" }}>
                        {tipo}
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <Calendar size={12} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
                          <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Data proposta: {formatDate(novaData)}</span>
                        </div>
                        <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Criada em: {formatDate(createdAt)}</span>
                      </div>
                    </div>
                    <div className="flex flex-row sm:flex-col items-start sm:items-end gap-2 flex-shrink-0 w-full sm:w-auto justify-between sm:justify-start">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg flex-shrink-0" style={{ background: status.bg, color: status.color, fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                        {status.icon} {status.label}
                      </span>
                      <span className="truncate" style={{ fontSize: "10px", color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>
                        {formatDate(createdAt)}
                      </span>
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-5 border-t" style={{ borderColor: "var(--border)" }}>
                    <div className="pt-4 space-y-4">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <Info label="Tipo" value={tipo} />
                        <Info label="Data proposta" value={formatDate(novaData)} />
                        <Info label="Criada em" value={formatDate(createdAt)} />
                      </div>
                      {getCurrentDate(solicitacao) && <Info label="Prazo atual" value={formatDate(getCurrentDate(solicitacao))} />}
                      {(solicitacao.motivo || solicitacao.justificativa) && (
                        <Info label="Justificativa" value={solicitacao.motivo ?? solicitacao.justificativa ?? ""} multiline />
                      )}
                      {solicitacao.parecer && <Info label="Parecer" value={solicitacao.parecer} multiline />}
                      {(solicitacao.status === "pendente" || solicitacao.status === "em_analise") && currentUser?.role === "coordenacao" && (
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
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <div className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Nova Solicitação</h2>
              <button onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>x</button>
            </div>
            <div className="space-y-4">
              {isStudentRequest && (
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Aluno</label>
                  <input readOnly value={currentUser?.name ?? ""} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "13px" }} />
                </div>
              )}
              {isAdvisorRequest && (
                <div>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Orientando</label>
                  <select disabled={advisorStudents.length === 0} value={selectedStudentId} onChange={(e) => setSelectedStudentId(e.target.value)} className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px", opacity: advisorStudents.length === 0 ? 0.7 : 1 }}>
                    <option value="">Selecione um orientando</option>
                    {advisorStudents.map((student) => <option key={student.id} value={student.id}>{student.nome}</option>)}
                  </select>
                  {advisorStudents.length === 0 && <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "6px" }}>Lista de orientandos será carregada pela integração futura.</p>}
                </div>
              )}
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
                <textarea rows={4} placeholder="Descreva detalhadamente o motivo da solicitação..." className="w-full rounded-xl px-3 py-2.5 outline-none resize-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
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

function Info({ label, value, multiline = false }: { label: string; value: string; multiline?: boolean }) {
  return (
    <div>
      <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>{label}</p>
      <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.6, padding: "12px", background: "var(--muted)", borderRadius: "8px", whiteSpace: multiline ? "pre-wrap" : "normal" }}>
        {value}
      </p>
    </div>
  );
}

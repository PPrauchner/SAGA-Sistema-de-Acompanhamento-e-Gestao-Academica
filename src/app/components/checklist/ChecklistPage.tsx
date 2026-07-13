import { useEffect, useState } from "react";
import { CheckCircle2, Circle, AlertTriangle, Loader2, Search, ChevronDown, FileDown } from "lucide-react";
import { useChecklistStudent } from "@/hooks/useChecklistStudent";
import { useAuth } from "@/hooks/useAuth";
import {
  getChecklist,
  type ChecklistResponse,
  type RequisitoStatus,
} from "@/api/checklistApi";
import { updateProficiencia, updateQualificacao } from "@/api/studentsApi";
import { exportChecklistPdf } from "@/utils/exportChecklistPdf";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/app/components/ui/accordion";
import { Progress } from "@/app/components/ui/progress";

const STATUS_CFG: Record<RequisitoStatus, { label: string; color: string; bg: string }> = {
  cumprido: { label: "Cumprido", color: "#1F8A70", bg: "#dcfce7" },
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fef9c3" },
  em_risco: { label: "Em risco", color: "#dc2626", bg: "#fee2e2" },
};

// Ciclo de vida do discente (issue #255). Mesmo enum de situacao_registrada/situacao_inferida.
const SITUACAO_CFG: Record<string, { label: string; color: string; bg: string }> = {
  regular: { label: "Regular", color: "#123C7A", bg: "#eef3fc" },
  em_prorrogacao: { label: "Em Prorrogação", color: "#D4A017", bg: "#fef9c3" },
  em_risco: { label: "Em Risco", color: "#dc2626", bg: "#fee2e2" },
  qualificado: { label: "Qualificado", color: "#1F8A70", bg: "#dcfce7" },
  em_fase_de_defesa: { label: "Fase de Defesa", color: "#7c3aed", bg: "#ede9fe" },
  concluido: { label: "Concluído", color: "#0891b2", bg: "#e0f2fe" },
  desligado: { label: "Desligado", color: "#64748b", bg: "#f1f5f9" },
};

function situacaoMeta(situacao: string) {
  return SITUACAO_CFG[situacao] ?? { label: situacao || "—", color: "#64748b", bg: "var(--muted)" };
}

interface RequisitoView {
  key: string;
  label: string;
  descricao: string;
  status: RequisitoStatus;
  detalhe: string;
}

const GROUPS = [
  {
    id: "creditos",
    label: "Créditos Acadêmicos",
    keys: ["creditos_minimos", "creditos_grupo_basico", "creditos_grupo_especifico", "creditos_grupo_tecnologico"],
  },
  {
    id: "proficiencia_qualificacao",
    label: "Proficiência e Qualificação",
    keys: ["proficiencia", "qualificacao"],
  },
  {
    id: "producao_plano",
    label: "Produção e Plano de Trabalho",
    keys: ["producao_validada", "plano_concluido"],
  },
];

interface FatoAcademicoLabels {
  cumprido: string;
  naoCumpridoComData: string;
  semData: string;
}

// O status é a fonte de verdade: a coordenação pode salvar a data sem aprovar o
// requisito, e nesse caso o card não pode se declarar aprovado (issue #342).
function fatoAcademicoDetalhe(
  status: RequisitoStatus,
  data: string | null | undefined,
  labels: FatoAcademicoLabels,
): string {
  if (status === "cumprido") return data ? `${labels.cumprido} em ${data}` : labels.cumprido;
  if (data) return `Registrada em ${data} — ${labels.naoCumpridoComData}`;
  return labels.semData;
}

function buildRequisitos(data: ChecklistResponse): RequisitoView[] {
  const r = data.requisitos;
  return [
    { key: "creditos_minimos", label: "Créditos mínimos totais", descricao: r.creditos_minimos.descricao, status: r.creditos_minimos.status, detalhe: `${r.creditos_minimos.obtidos} / ${r.creditos_minimos.minimo} créditos` },
    { key: "creditos_grupo_basico", label: "Créditos — grupo básico", descricao: r.creditos_grupo_basico.descricao, status: r.creditos_grupo_basico.status, detalhe: `${r.creditos_grupo_basico.obtidos} / ${r.creditos_grupo_basico.minimo} créditos` },
    { key: "creditos_grupo_especifico", label: "Créditos — grupo específico", descricao: r.creditos_grupo_especifico.descricao, status: r.creditos_grupo_especifico.status, detalhe: `${r.creditos_grupo_especifico.obtidos} / ${r.creditos_grupo_especifico.minimo} créditos` },
    { key: "creditos_grupo_tecnologico", label: "Créditos — grupo tecnológico", descricao: r.creditos_grupo_tecnologico.descricao, status: r.creditos_grupo_tecnologico.status, detalhe: `${r.creditos_grupo_tecnologico.obtidos} / máx ${r.creditos_grupo_tecnologico.maximo} créditos` },
    { key: "proficiencia", label: "Proficiência", descricao: "Proficiência em língua estrangeira", status: r.proficiencia.status, detalhe: fatoAcademicoDetalhe(r.proficiencia.status, r.proficiencia.data_comprovacao, { cumprido: "Comprovada", naoCumpridoComData: "não comprovada", semData: "Não comprovada" }) },
    { key: "qualificacao", label: "Qualificação", descricao: "Aprovação no exame de qualificação", status: r.qualificacao.status, detalhe: fatoAcademicoDetalhe(r.qualificacao.status, r.qualificacao.data_aprovacao, { cumprido: "Aprovada", naoCumpridoComData: "não aprovada", semData: "Pendente" }) },
    { key: "producao_validada", label: "Produção bibliográfica", descricao: "Produção bibliográfica validada", status: r.producao_validada.status, detalhe: `${r.producao_validada.quantidade_aprovadas} validada(s)` },
    { key: "plano_concluido", label: "Plano de trabalho", descricao: "Conclusão das etapas (não-defesa)", status: r.plano_concluido.status, detalhe: `${r.plano_concluido.tasks_concluidas}/${r.plano_concluido.tasks_total_nao_defesa} etapas concluídas` },
  ];
}

function toDateInput(value: string | null | undefined): string {
  if (!value) return "";
  return value.slice(0, 10);
}

function toIsoDate(value: string): string {
  return `${value}T00:00:00Z`;
}

export function ChecklistPage() {
  const { studentId, students, setStudentId } = useChecklistStudent();
  const { token, role } = useAuth();
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [selectorSearch, setSelectorSearch] = useState("");
  const [data, setData] = useState<ChecklistResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [savingAcademicFact, setSavingAcademicFact] = useState<"proficiencia" | "qualificacao" | null>(null);
  const [academicForm, setAcademicForm] = useState({
    proficienciaComprovada: false,
    proficienciaData: "",
    proficienciaComprovanteUrl: "",
    qualificacaoAprovada: false,
    qualificacaoData: "",
    qualificacaoComprovanteUrl: "",
  });
  const canEditAcademicFacts = role === "coordenacao";

  function applyChecklist(response: ChecklistResponse): void {
    setData(response);
    setAcademicForm({
      proficienciaComprovada: response.requisitos.proficiencia.status === "cumprido",
      proficienciaData: toDateInput(response.requisitos.proficiencia.data_comprovacao),
      proficienciaComprovanteUrl: response.requisitos.proficiencia.comprovante_url ?? "",
      qualificacaoAprovada: response.requisitos.qualificacao.status === "cumprido",
      qualificacaoData: toDateInput(response.requisitos.qualificacao.data_aprovacao),
      qualificacaoComprovanteUrl: response.requisitos.qualificacao.comprovante_url ?? "",
    });
  }

  async function reloadChecklist(): Promise<void> {
    if (!studentId || !token) return;
    const response = await getChecklist(studentId, token);
    applyChecklist(response);
  }

  useEffect(() => {
    if (!studentId || !token) return;
    let active = true;
    setLoading(true);
    setError(null);
    getChecklist(studentId, token)
      .then((res) => { if (active) applyChecklist(res); })
      .catch(() => { if (active) setError("Não foi possível carregar o checklist."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  const requisitos = data ? buildRequisitos(data) : [];
  const cumpridos = requisitos.filter((r) => r.status === "cumprido").length;
  const emRiscoCount = requisitos.filter((r) => r.status === "em_risco").length;
  const pendenteCount = requisitos.filter((r) => r.status === "pendente").length;
  const total = requisitos.length;
  const pct = total > 0 ? Math.round((cumpridos / total) * 100) : 0;

  const selectedStudent = students?.find((s) => s.id === studentId);
  const filteredStudents = students?.filter((s) =>
    s.label.toLowerCase().includes(selectorSearch.toLowerCase())
  ) ?? [];

  async function handleSaveProficiencia(): Promise<void> {
    if (!token || !studentId) return;
    if (academicForm.proficienciaComprovada && !academicForm.proficienciaData) {
      setError("Informe a data da proficiência.");
      return;
    }
    setSavingAcademicFact("proficiencia");
    setError(null);
    setFeedback(null);
    try {
      await updateProficiencia(token, studentId, {
        comprovada: academicForm.proficienciaComprovada,
        data_proficiencia: academicForm.proficienciaData ? toIsoDate(academicForm.proficienciaData) : null,
        comprovante_url: academicForm.proficienciaComprovanteUrl.trim() || null,
      });
      await reloadChecklist();
      setFeedback("Proficiência atualizada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar proficiência.");
    } finally {
      setSavingAcademicFact(null);
    }
  }

  async function handleSaveQualificacao(): Promise<void> {
    if (!token || !studentId) return;
    if (!academicForm.qualificacaoData) {
      setError("Informe a data da qualificação.");
      return;
    }
    setSavingAcademicFact("qualificacao");
    setError(null);
    setFeedback(null);
    try {
      await updateQualificacao(token, studentId, {
        aprovada: academicForm.qualificacaoAprovada,
        data_qualificacao: toIsoDate(academicForm.qualificacaoData),
        comprovante_url: academicForm.qualificacaoComprovanteUrl.trim() || null,
      });
      await reloadChecklist();
      setFeedback("Qualificação atualizada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar qualificação.");
    } finally {
      setSavingAcademicFact(null);
    }
  }

  function handleExportPdf(): void {
    if (!data) return;
    setExportingPdf(true);
    setError(null);
    try {
      exportChecklistPdf(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao exportar checklist em PDF.");
    } finally {
      setExportingPdf(false);
    }
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 md:mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h1 style={{ color: "var(--foreground)" }}>Checklist de Integralização</h1>
            {data && !loading && (
              <span
                className="rounded-lg px-2.5 py-1"
                title="Situação inferida pelo motor a partir dos requisitos"
                style={{ background: situacaoMeta(data.situacao_inferida).bg, color: situacaoMeta(data.situacao_inferida).color, fontSize: "12px", fontWeight: 700 }}
              >
                {situacaoMeta(data.situacao_inferida).label}
              </span>
            )}
          </div>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            Acompanhe todos os requisitos para a conclusão do curso
          </p>
        </div>

        {/* Seletor de aluno — orientador e coordenação apenas */}
        <button
          type="button"
          onClick={handleExportPdf}
          disabled={!data || loading || exportingPdf}
          className="flex items-center gap-2 rounded-xl px-4 py-2 transition-opacity disabled:opacity-60"
          style={{ background: "#eef3fc", border: "1px solid #c7d9f5", color: "#123C7A", fontSize: "13px", fontWeight: 700 }}
          aria-label="Exportar checklist em PDF"
        >
          {exportingPdf ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />}
          Exportar checklist em PDF
        </button>

        {students && (
          <div className="relative">
            <button
              onClick={() => setSelectorOpen((o) => !o)}
              className="flex items-center gap-2 rounded-xl px-4 py-2"
              style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}
            >
              {selectedStudent?.label ?? "Selecionar aluno"}
              <ChevronDown size={14} style={{ color: "var(--muted-foreground)" }} />
            </button>

            {selectorOpen && (
              <div
                className="absolute right-0 mt-1 rounded-xl shadow-lg z-10"
                style={{ background: "var(--card)", border: "1px solid var(--border)", width: "220px" }}
              >
                <div className="p-2">
                  <div className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: "var(--muted)" }}>
                    <Search size={13} style={{ color: "var(--muted-foreground)" }} />
                    <input
                      autoFocus
                      type="text"
                      placeholder="Buscar aluno..."
                      value={selectorSearch}
                      onChange={(e) => setSelectorSearch(e.target.value)}
                      className="flex-1 bg-transparent outline-none"
                      style={{ fontSize: "13px", color: "var(--foreground)" }}
                    />
                  </div>
                </div>
                <div className="pb-2 max-h-48 overflow-y-auto">
                  {filteredStudents.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => { setStudentId(s.id); setSelectorOpen(false); setSelectorSearch(""); }}
                      className="w-full text-left px-4 py-2.5"
                      style={{
                        fontSize: "13px",
                        fontWeight: s.id === studentId ? 700 : 400,
                        color: s.id === studentId ? "#123C7A" : "var(--foreground)",
                        background: s.id === studentId ? "#eef3fc" : "transparent",
                      }}
                    >
                      {s.label}
                    </button>
                  ))}
                  {filteredStudents.length === 0 && (
                    <p className="px-4 py-2" style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                      Nenhum aluno encontrado
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legenda de status */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        {[
          { label: "Cumprido",     dot: "#1F8A70", bg: "#dcfce7", color: "#1F8A70" },
          { label: "Pendente",      dot: "#D4A017", bg: "#fef9c3", color: "#D4A017" },
          { label: "Em Risco",  dot: "#dc2626", bg: "#fee2e2", color: "#dc2626" },
        ].map(({ label, dot, bg, color }) => (
          <span
            key={label}
            className="flex items-center gap-1.5 rounded-full px-3 py-1"
            style={{ background: bg, fontSize: "12px", fontWeight: 600, color }}
          >
            <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: dot, flexShrink: 0, display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>

      {loading && (
        <div className="flex items-center gap-2" style={{ color: "var(--muted-foreground)", padding: "32px 0" }}>
          <Loader2 size={18} className="animate-spin" /> Carregando checklist…
        </div>
      )}

      {error && !loading && (
        <div className="rounded-xl p-4" style={{ background: "#fee2e2", color: "#dc2626", fontSize: "14px" }}>
          {error}
        </div>
      )}

      {feedback && !loading && (
        <div className="rounded-xl p-4 mb-4" style={{ background: "#dcfce7", color: "#166534", fontSize: "14px" }}>
          {feedback}
        </div>
      )}

      {data && !loading && (
        <>
          {/* Cards de resumo */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", marginBottom: "8px" }}>Progresso Geral</p>
              <div className="flex items-end justify-between mb-2">
                <p style={{ fontSize: "22px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1.1 }}>
                  {cumpridos} <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--muted-foreground)" }}>/ {total}</span>
                </p>
                <span style={{ fontSize: "20px", fontWeight: 800, color: "#123C7A" }}>{pct}%</span>
              </div>
              <Progress value={pct} />
            </div>

            <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", marginBottom: "8px" }}>Obrigatórios Cumpridos</p>
              <p style={{ fontSize: "22px", fontWeight: 800, color: "#1F8A70", lineHeight: 1.1, marginBottom: "4px" }}>
                {cumpridos} <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--muted-foreground)" }}>/ {total}</span>
              </p>
              <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>requisito(s) integralizado(s)</p>
            </div>

            <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", marginBottom: "8px" }}>Em Risco / Pendentes</p>
              {emRiscoCount === 0 && pendenteCount === 0 ? (
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={20} style={{ color: "#1F8A70" }} />
                  <p style={{ fontSize: "13px", color: "#1F8A70", fontWeight: 600 }}>Tudo em dia</p>
                </div>
              ) : (
                <div className="flex items-center gap-4">
                  {emRiscoCount > 0 && (
                    <div>
                      <p style={{ fontSize: "22px", fontWeight: 800, color: "#dc2626", lineHeight: 1.1 }}>{emRiscoCount}</p>
                      <p style={{ fontSize: "11px", color: "#dc2626" }}>em risco</p>
                    </div>
                  )}
                  {pendenteCount > 0 && (
                    <div>
                      <p style={{ fontSize: "22px", fontWeight: 800, color: "#D4A017", lineHeight: 1.1 }}>{pendenteCount}</p>
                      <p style={{ fontSize: "11px", color: "#D4A017" }}>pendente(s)</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Conflito de situação: registrada (manual/coordenação) x inferida (motor) lado a lado */}
          {data.conflito_situacao && (
            <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", border: "1px solid #fca5a5" }}>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={16} style={{ color: "#dc2626", flexShrink: 0 }} />
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#dc2626" }}>Conflito de situação detectado</span>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <span style={{ fontSize: "11px", color: "#991b1b" }}>Registrada:</span>
                  <span className="rounded-lg px-2 py-0.5" style={{ background: situacaoMeta(data.situacao_registrada).bg, color: situacaoMeta(data.situacao_registrada).color, fontSize: "11px", fontWeight: 700 }}>
                    {situacaoMeta(data.situacao_registrada).label}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span style={{ fontSize: "11px", color: "#991b1b" }}>Inferida:</span>
                  <span className="rounded-lg px-2 py-0.5" style={{ background: situacaoMeta(data.situacao_inferida).bg, color: situacaoMeta(data.situacao_inferida).color, fontSize: "11px", fontWeight: 700 }}>
                    {situacaoMeta(data.situacao_inferida).label}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Riscos detectados */}
          {data.riscos_detectados.length > 0 && (
            <div className="rounded-2xl p-4 mb-4" style={{ background: "#fffbeb", border: "1px solid #fde68a" }}>
              <p style={{ fontSize: "13px", fontWeight: 700, color: "#92400e", marginBottom: "8px" }}>Riscos detectados</p>
              <ul className="space-y-1">
                {data.riscos_detectados.map((risco, i) => (
                  <li key={i} className="flex items-center gap-2" style={{ fontSize: "13px", color: "#92400e" }}>
                    <AlertTriangle size={14} /> {risco}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Requisitos agrupados por categoria */}
          <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <Accordion type="multiple" defaultValue={GROUPS.map((g) => g.id)}>
              {GROUPS.map((group) => {
                const groupReqs = requisitos.filter((r) => group.keys.includes(r.key));
                const groupCumpridos = groupReqs.filter((r) => r.status === "cumprido").length;
                const groupPct = groupReqs.length > 0 ? Math.round((groupCumpridos / groupReqs.length) * 100) : 0;

                return (
                  <AccordionItem key={group.id} value={group.id}>
                    <AccordionTrigger
                      className="px-5 py-4 hover:no-underline"
                      style={{ background: "var(--card)" }}
                    >
                      <div className="flex-1 flex items-center justify-between gap-4 mr-2">
                        <span style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>
                          {group.label}
                        </span>
                        <div className="flex items-center gap-3">
                          <span style={{ fontSize: "12px", color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>
                            {groupCumpridos}/{groupReqs.length} cumpridos
                          </span>
                          <div style={{ width: "72px" }}>
                            <Progress value={groupPct} className="h-1.5" />
                          </div>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="px-4 pb-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                        {groupReqs.map((req) => {
                          const cfg = STATUS_CFG[req.status];
                          return (
                            <div
                              key={req.key}
                              className="rounded-xl p-4 flex items-start gap-3"
                              style={{ background: "var(--muted)", border: "1px solid var(--border)" }}
                            >
                              <div style={{ flexShrink: 0, paddingTop: "2px" }}>
                                {req.status === "cumprido"
                                  ? <CheckCircle2 size={20} style={{ color: cfg.color }} />
                                  : <Circle size={20} style={{ color: cfg.color }} />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{req.label}</p>
                                  <span
                                    className="rounded-lg px-2 py-0.5 flex-shrink-0"
                                    style={{ background: cfg.bg, color: cfg.color, fontSize: "11px", fontWeight: 700 }}
                                  >
                                    {cfg.label}
                                  </span>
                                </div>
                                <p style={{ fontSize: "12px", color: "var(--muted-foreground)", marginTop: "2px" }}>{req.descricao}</p>
                                <p style={{ fontSize: "13px", color: "var(--foreground)", marginTop: "6px", fontWeight: 600 }}>{req.detalhe}</p>
                                {req.key === "proficiencia" && data.requisitos.proficiencia.comprovante_url && (
                                  <a
                                    href={data.requisitos.proficiencia.comprovante_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ display: "inline-block", marginTop: "6px", fontSize: "12px", color: "#123C7A", fontWeight: 700 }}
                                  >
                                    Ver comprovante
                                  </a>
                                )}
                                {req.key === "qualificacao" && data.requisitos.qualificacao.comprovante_url && (
                                  <a
                                    href={data.requisitos.qualificacao.comprovante_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ display: "inline-block", marginTop: "6px", fontSize: "12px", color: "#123C7A", fontWeight: 700 }}
                                  >
                                    Ver comprovante
                                  </a>
                                )}
                                {canEditAcademicFacts && req.key === "proficiencia" && (
                                  <AcademicFactEditor
                                    checked={academicForm.proficienciaComprovada}
                                    date={academicForm.proficienciaData}
                                    comprovanteUrl={academicForm.proficienciaComprovanteUrl}
                                    checkedLabel="Proficiência comprovada"
                                    dateLabel="Data da proficiência"
                                    saving={savingAcademicFact === "proficiencia"}
                                    onCheckedChange={(value) => setAcademicForm((f) => ({ ...f, proficienciaComprovada: value }))}
                                    onDateChange={(value) => setAcademicForm((f) => ({ ...f, proficienciaData: value }))}
                                    onComprovanteChange={(value) => setAcademicForm((f) => ({ ...f, proficienciaComprovanteUrl: value }))}
                                    onSave={handleSaveProficiencia}
                                  />
                                )}
                                {canEditAcademicFacts && req.key === "qualificacao" && (
                                  <AcademicFactEditor
                                    checked={academicForm.qualificacaoAprovada}
                                    date={academicForm.qualificacaoData}
                                    comprovanteUrl={academicForm.qualificacaoComprovanteUrl}
                                    checkedLabel="Qualificação aprovada"
                                    dateLabel="Data da qualificação"
                                    saving={savingAcademicFact === "qualificacao"}
                                    onCheckedChange={(value) => setAcademicForm((f) => ({ ...f, qualificacaoAprovada: value }))}
                                    onDateChange={(value) => setAcademicForm((f) => ({ ...f, qualificacaoData: value }))}
                                    onComprovanteChange={(value) => setAcademicForm((f) => ({ ...f, qualificacaoComprovanteUrl: value }))}
                                    onSave={handleSaveQualificacao}
                                  />
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                );
              })}
            </Accordion>
          </div>
        </>
      )}
    </div>
  );
}

function AcademicFactEditor({
  checked,
  date,
  comprovanteUrl,
  checkedLabel,
  dateLabel,
  saving,
  onCheckedChange,
  onDateChange,
  onComprovanteChange,
  onSave,
}: {
  checked: boolean;
  date: string;
  comprovanteUrl: string;
  checkedLabel: string;
  dateLabel: string;
  saving: boolean;
  onCheckedChange: (value: boolean) => void;
  onDateChange: (value: string) => void;
  onComprovanteChange: (value: string) => void;
  onSave: () => void;
}) {
  return (
    <div className="mt-3 rounded-xl p-3 space-y-2" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <label className="flex items-center gap-2" style={{ fontSize: "12px", color: "var(--foreground)", fontWeight: 700 }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onCheckedChange(event.target.checked)}
        />
        {checkedLabel}
      </label>
      <label className="flex flex-col gap-1">
        <span style={{ fontSize: "11px", color: "var(--muted-foreground)", fontWeight: 700 }}>{dateLabel}</span>
        <input
          type="date"
          value={date}
          onChange={(event) => onDateChange(event.target.value)}
          className="rounded-lg px-2 py-1.5 outline-none"
          style={{ background: "var(--muted)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "12px" }}
        />
      </label>
      <label className="flex flex-col gap-1">
        <span style={{ fontSize: "11px", color: "var(--muted-foreground)", fontWeight: 700 }}>URL do comprovante (opcional)</span>
        <input
          type="url"
          value={comprovanteUrl}
          onChange={(event) => onComprovanteChange(event.target.value)}
          placeholder="https://..."
          className="rounded-lg px-2 py-1.5 outline-none"
          style={{ background: "var(--muted)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "12px" }}
        />
      </label>
      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="rounded-lg px-3 py-1.5"
        style={{ background: "#123C7A", color: "#fff", fontSize: "12px", fontWeight: 700, opacity: saving ? 0.6 : 1 }}
      >
        {saving ? "Salvando..." : "Salvar"}
      </button>
    </div>
  );
}

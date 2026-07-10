/**
 * Página de detalhes do aluno (issue #318).
 *
 * Carrega os dados reais via GET /students/{id} (cadastro, situações, prazos e
 * progresso do plano) e o nome do orientador via GET /advisors. Os cards de
 * módulos navegam para as páginas correspondentes. A transferência de
 * orientador (coordenação) permanece disponível via TransferModal.
 */
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Award,
  BookOpen,
  Calendar,
  CheckCircle,
  ClipboardList,
  GraduationCap,
  ListChecks,
  Mail,
} from "lucide-react";

import { getAdvisors, type Advisor } from "@/api/advisorsApi";
import { getStudent, type Student, type StudentStatus } from "@/api/studentsApi";
import { useApp } from "../../context/AppContext";
import { TransferModal } from "../transfers/TransferModal";

const STATUS_META: Record<StudentStatus, { label: string; color: string; bg: string }> = {
  regular: { label: "Regular", color: "#1F8A70", bg: "#dcfce7" },
  em_prorrogacao: { label: "Prorrogação", color: "#D4A017", bg: "#fef9c3" },
  em_risco: { label: "Em Risco", color: "#dc2626", bg: "#fee2e2" },
  qualificado: { label: "Qualificado", color: "#123C7A", bg: "#eef3fc" },
  em_fase_de_defesa: { label: "Fase de Defesa", color: "#7c3aed", bg: "#ede9fe" },
  concluido: { label: "Concluído", color: "#3b82f6", bg: "#dbeafe" },
  desligado: { label: "Desligado", color: "#dc2626", bg: "#fee2e2" },
};

function statusMeta(status: string) {
  return (
    STATUS_META[status as StudentStatus] ?? {
      label: status || "—",
      color: "#64748b",
      bg: "var(--muted)",
    }
  );
}

function formatDate(value?: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short" }).format(new Date(value));
}

function daysRemaining(value?: string | null): number | null {
  if (!value) return null;
  const deadline = new Date(value);
  if (Number.isNaN(deadline.getTime())) return null;
  return Math.ceil((deadline.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

const MODULE_CARDS = [
  { label: "Plano de Trabalho", page: "plano-trabalho", color: "#123C7A", icon: <ClipboardList size={18} /> },
  { label: "Atividades Creditáveis", page: "atividades", color: "#1F8A70", icon: <Award size={18} /> },
  { label: "Produções Científicas", page: "producoes", color: "#D4A017", icon: <BookOpen size={18} /> },
  { label: "Checklist de Conclusão", page: "checklist", color: "#8b5cf6", icon: <ListChecks size={18} /> },
] as const;

export function StudentDetailPage() {
  const { currentUser, setCurrentPage, selectedStudentId, token } = useApp();
  const [student, setStudent] = useState<Student | null>(null);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTransferModalOpen, setIsTransferModalOpen] = useState(false);

  useEffect(() => {
    if (!token || !selectedStudentId) {
      setLoading(false);
      if (!selectedStudentId) setError("Nenhum aluno selecionado.");
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([
      getStudent(token, selectedStudentId),
      // Aluno não tem acesso a GET /advisors — segue sem o nome do orientador.
      getAdvisors(token).catch(() => [] as Advisor[]),
    ])
      .then(([studentData, advisorsData]) => {
        if (!active) return;
        setStudent(studentData);
        setAdvisors(advisorsData);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Falha ao carregar o aluno.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token, selectedStudentId]);

  const advisorName = (id?: string | null): string =>
    advisors.find((advisor) => advisor.id === id)?.nome ?? (id ? id : "—");

  const st = student ? statusMeta(student.situacao_registrada) : null;
  const sti = student ? statusMeta(student.situacao_inferida) : null;
  const divergente = Boolean(
    student && student.situacao_inferida !== student.situacao_registrada,
  );
  const dias = daysRemaining(student?.prazo_final);
  const progresso = Math.round(student?.progresso_plano ?? 0);

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <button
          onClick={() => setCurrentPage("alunos")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}
        >
          <ArrowLeft size={14} /> Voltar para Alunos
        </button>
        {currentUser?.role === "coordenacao" && (
          <button
            onClick={() => setIsTransferModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl"
            style={{ background: "#123C7A", color: "#fff", fontSize: "13px", fontWeight: 600 }}
          >
            Transferir orientador
          </button>
        )}
      </div>

      {loading ? (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Carregando aluno...
        </div>
      ) : error ? (
        <div className="rounded-2xl px-4 py-3" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>{error}</div>
      ) : student && st && sti ? (
        <div className="space-y-5">
          {/* Cabeçalho com identidade e situações */}
          <div className="rounded-2xl p-6" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="rounded-full flex items-center justify-center" style={{ width: 56, height: 56, background: "#123C7A", color: "#fff", fontSize: "22px", fontWeight: 700 }}>
                  {student.nome.charAt(0)}
                </div>
                <div>
                  <h1 style={{ color: "var(--foreground)", marginBottom: "2px" }}>{student.nome}</h1>
                  <p className="flex items-center gap-2" style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>
                    <GraduationCap size={13} /> Mat. {student.matricula} · {student.programa_id} · {student.nivel}
                  </p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1.5">
                <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg" style={{ background: st.bg, color: st.color, fontSize: "12px", fontWeight: 700 }}>
                  <CheckCircle size={12} /> {st.label}
                </span>
                <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-lg" title="Situação inferida pelo motor" style={{ border: `1px solid ${sti.color}50`, color: sti.color, fontSize: "11px", fontWeight: 600 }}>
                  {divergente && <AlertTriangle size={11} />} inferida: {sti.label}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
              <div>
                <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase" }}>E-mail</p>
                <p className="flex items-center gap-1.5 mt-1" style={{ fontSize: "13px", color: "var(--foreground)" }}><Mail size={13} /> {student.email}</p>
              </div>
              <div>
                <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase" }}>Orientador</p>
                <p className="mt-1" style={{ fontSize: "13px", color: "var(--foreground)" }}>{advisorName(student.orientador_id)}</p>
                {student.coorientador_id && (
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Coorientador: {advisorName(student.coorientador_id)}</p>
                )}
              </div>
              <div>
                <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase" }}>Ingresso</p>
                <p className="flex items-center gap-1.5 mt-1" style={{ fontSize: "13px", color: "var(--foreground)" }}><Calendar size={13} /> {formatDate(student.data_ingresso)}</p>
              </div>
              <div>
                <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase" }}>Prazo Final</p>
                <p className="flex items-center gap-1.5 mt-1" style={{ fontSize: "13px", fontWeight: 600, color: dias == null ? "var(--foreground)" : dias < 0 ? "#dc2626" : dias < 90 ? "#D4A017" : "#1F8A70" }}>
                  <Calendar size={13} /> {formatDate(student.prazo_final)}
                  {dias != null && <span style={{ fontSize: "11px", fontWeight: 600 }}>({dias < 0 ? `expirado há ${-dias} d` : `${dias} d restantes`})</span>}
                </p>
              </div>
            </div>

            <div className="mt-6">
              <div className="flex justify-between mb-1.5">
                <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Progresso do plano de trabalho</span>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)" }}>{progresso}%</span>
              </div>
              <div className="rounded-full overflow-hidden" style={{ height: 8, background: "var(--muted)" }}>
                <div className="h-full rounded-full" style={{ width: `${progresso}%`, background: progresso > 70 ? "#1F8A70" : progresso > 40 ? "#D4A017" : "#dc2626" }} />
              </div>
            </div>

            <div className="flex flex-wrap gap-4 mt-4" style={{ fontSize: "12px" }}>
              <span className="flex items-center gap-1.5" style={{ color: student.qualificacao_aprovada ? "#1F8A70" : "var(--muted-foreground)" }}>
                <CheckCircle size={13} /> Qualificação {student.qualificacao_aprovada ? `aprovada${student.qualificacao_data ? ` em ${formatDate(student.qualificacao_data)}` : ""}` : "pendente"}
              </span>
              <span className="flex items-center gap-1.5" style={{ color: student.proficiencia_comprovada ? "#1F8A70" : "var(--muted-foreground)" }}>
                <CheckCircle size={13} /> Proficiência {student.proficiencia_comprovada ? `comprovada${student.proficiencia_data ? ` em ${formatDate(student.proficiencia_data)}` : ""}` : "pendente"}
              </span>
            </div>
          </div>

          {/* Navegação para os módulos do aluno */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {MODULE_CARDS.map((item) => (
              <button
                key={item.label}
                onClick={() => setCurrentPage(item.page)}
                className="rounded-xl p-4 text-left transition-all"
                style={{ background: `${item.color}10`, border: `1px solid ${item.color}30` }}
              >
                <p className="flex items-center gap-2" style={{ fontWeight: 600, color: item.color }}>{item.icon} {item.label}</p>
                <p style={{ fontSize: "12px", color: "var(--muted-foreground)", marginTop: "4px" }}>Abrir módulo</p>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {isTransferModalOpen && (
        <TransferModal
          onClose={() => setIsTransferModalOpen(false)}
          onSuccess={() => {
            setIsTransferModalOpen(false);
            alert("Transferência realizada/solicitada com sucesso!");
          }}
          initialStudentId={selectedStudentId || undefined}
        />
      )}
    </div>
  );
}

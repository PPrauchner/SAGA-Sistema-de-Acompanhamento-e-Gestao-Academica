import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Edit3,
  Eye,
  GraduationCap,
  Plus,
  Search,
} from "lucide-react";

import { getAdvisors, type Advisor } from "@/api/advisorsApi";
import { programsApi, type Program } from "@/api/programsApi";
import {
  createStudent,
  getStudents,
  type Student,
  type StudentCreatePayload,
  type StudentStatus,
  updateStudent,
} from "@/api/studentsApi";
import { useApp } from "../../context/AppContext";
import { TableExportMenu } from "@/app/components/export/TableExportMenu";
import type { ExportColumn } from "@/utils/exportData";

const STATUS_MAP: Record<
  StudentStatus,
  { label: string; color: string; bg: string; icon: JSX.Element }
> = {
  regular: { label: "Regular", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={12} /> },
  em_prorrogacao: { label: "Prorrogação", color: "#D4A017", bg: "#fef9c3", icon: <AlertTriangle size={12} /> },
  em_risco: { label: "Em Risco", color: "#dc2626", bg: "#fee2e2", icon: <AlertTriangle size={12} /> },
  qualificado: { label: "Qualificado", color: "#123C7A", bg: "#eef3fc", icon: <CheckCircle size={12} /> },
  em_fase_de_defesa: { label: "Fase de Defesa", color: "#7c3aed", bg: "#ede9fe", icon: <GraduationCap size={12} /> },
  concluido: { label: "Concluído", color: "#3b82f6", bg: "#dbeafe", icon: <CheckCircle size={12} /> },
  desligado: { label: "Desligado", color: "#dc2626", bg: "#fee2e2", icon: <AlertTriangle size={12} /> },
};

const emptyForm: StudentCreatePayload = {
  nome: "",
  email: "",
  matricula: "",
  orientador_id: "",
  coorientador_id: null,
  nivel: "mestrado",
  data_ingresso: "",
  programa_id: "",
};

function formatDate(value?: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", { month: "2-digit", year: "numeric" }).format(new Date(value));
}

function progressFor(student: Student): number {
  const checks = [
    Boolean(student.qualificacao_aprovada),
    Boolean(student.proficiencia_comprovada),
    student.situacao_registrada === "qualificado" || student.situacao_registrada === "em_fase_de_defesa" || student.situacao_registrada === "concluido",
    student.situacao_registrada === "concluido",
  ];
  return 20 + checks.filter(Boolean).length * 20;
}

export function StudentsPage() {
  const { activeView, currentUser, setCurrentPage, setSelectedStudentId, token } = useApp();
  const [students, setStudents] = useState<Student[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("todos");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<StudentCreatePayload>(emptyForm);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [studentsData, advisorsData, programsData] = await Promise.all([
        getStudents(authToken),
        getAdvisors(authToken).catch(() => []),
        programsApi.getPrograms(authToken),
      ]);
      setStudents(studentsData);
      setAdvisors(advisorsData);
      setPrograms(programsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar alunos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) void loadData(token);
  }, [token]);

  const advisorById = useMemo(
    () => new Map(advisors.map((advisor) => [advisor.id, advisor])),
    [advisors],
  );

  const visibleStudents =
    activeView === "orientador" && currentUser?.advisor_id
      ? students.filter((student) => student.orientador_id === currentUser.advisor_id)
      : students;

  const filtered = visibleStudents.filter((student) => {
    const normalizedSearch = search.toLowerCase();
    const matchSearch =
      student.nome.toLowerCase().includes(normalizedSearch) ||
      student.matricula.includes(search);
    const matchStatus = filterStatus === "todos" || student.situacao_registrada === filterStatus;
    return matchSearch && matchStatus;
  });

  function openCreateForm(): void {
    setEditingStudent(null);
    setForm({
      ...emptyForm,
      programa_id: currentUser?.role === "orientador" ? currentUser.programa_id ?? "" : "",
    });
    setInviteToken(null);
    setShowForm(true);
  }

  function openEditForm(student: Student): void {
    setEditingStudent(student);
    setForm({
      nome: student.nome,
      email: student.email,
      matricula: student.matricula,
      orientador_id: student.orientador_id,
      coorientador_id: student.coorientador_id ?? null,
      nivel: "mestrado",
      data_ingresso: student.data_ingresso.slice(0, 10),
      programa_id: student.programa_id,
    });
    setInviteToken(null);
    setShowForm(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) return;
    if (!editingStudent && !form.programa_id) {
      setError("Selecione um programa para cadastrar o aluno");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editingStudent) {
        await updateStudent(token, editingStudent.id, {
          nome: form.nome,
          orientador_id: form.orientador_id,
          coorientador_id: form.coorientador_id,
        });
        setShowForm(false);
      } else {
        const result = await createStudent(token, { ...form, nivel: "mestrado" });
        setInviteToken(result.invite_token);
        setShowForm(false);
      }
      setForm(emptyForm);
      setEditingStudent(null);
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao cadastrar aluno");
    } finally {
      setSaving(false);
    }
  }

  const regularCount = visibleStudents.filter((s) => s.situacao_registrada === "regular").length;
  const canEdit = currentUser?.role === "coordenacao" && activeView === "coordenador";
  const canCreate =
    canEdit ||
    (currentUser?.role === "orientador" && activeView === "orientador");
  const availablePrograms =
    currentUser?.role === "orientador"
      ? programs.filter((program) => program.id === currentUser.programa_id)
      : programs;
  const studentExportColumns = useMemo<ExportColumn<Student>[]>(
    () =>
      viewMode === "table"
        ? [
            { key: "nome", label: "Aluno" },
            { key: "matricula", label: "Matricula" },
            { key: "orientador_id", label: "Orientador", value: (student) => advisorById.get(student.orientador_id)?.nome ?? student.orientador_id },
            { key: "programa_id", label: "Programa" },
            { key: "id", label: "Progresso", value: (student) => progressFor(student) },
            { key: "situacao_registrada", label: "Status", value: (student) => STATUS_MAP[student.situacao_registrada]?.label ?? student.situacao_registrada },
          ]
        : [
            { key: "nome", label: "Nome" },
            { key: "matricula", label: "Matricula" },
            { key: "programa_id", label: "Programa" },
            { key: "prazo_final", label: "Prazo", value: (student) => formatDate(student.prazo_final) },
            { key: "id", label: "Progresso", value: (student) => progressFor(student) },
            { key: "situacao_registrada", label: "Status", value: (student) => STATUS_MAP[student.situacao_registrada]?.label ?? student.situacao_registrada },
          ],
    [advisorById, viewMode],
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Gerenciamento de Alunos</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            {visibleStudents.length} alunos cadastrados · {regularCount} regulares
          </p>
        </div>
        {canCreate && (
          <button onClick={openCreateForm} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
            <Plus size={16} />
            Novo Aluno
          </button>
        )}
      </div>

      {error && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>{error}</div>}
      {inviteToken && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#dcfce7", color: "#166534", fontSize: "13px" }}>Convite criado: {inviteToken}</div>}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6">
        {[
          { label: "Total", value: visibleStudents.length, color: "#123C7A", bg: "#eef3fc" },
          { label: "Regular", value: regularCount, color: "#1F8A70", bg: "#dcfce7" },
          { label: "Prorrogação", value: visibleStudents.filter(s => s.situacao_registrada === "em_prorrogacao").length, color: "#D4A017", bg: "#fef9c3" },
          { label: "Concluído", value: visibleStudents.filter(s => s.situacao_registrada === "concluido").length, color: "#3b82f6", bg: "#dbeafe" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl p-3 sm:p-4 flex items-center gap-2 sm:gap-3 min-w-0" style={{ background: stat.bg }}>
            <p className="flex-shrink-0" style={{ fontSize: "22px", fontWeight: 800, color: stat.color, lineHeight: 1.1 }}>{stat.value}</p>
            <p className="truncate min-w-0" style={{ fontSize: "13px", color: stat.color, fontWeight: 600 }}>{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
          <input placeholder="Buscar por nome ou matrícula..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full rounded-xl pl-9 pr-4 py-2.5 outline-none" style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }} />
        </div>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded-xl px-3 py-2.5 outline-none" style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}>
          <option value="todos">Todos os Status</option>
          {Object.entries(STATUS_MAP).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
        </select>
        <div className="flex rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
          {(["table", "cards"] as const).map((mode) => (
            <button key={mode} onClick={() => setViewMode(mode)} className="px-3 py-2 transition-colors" style={{ background: viewMode === mode ? "#123C7A" : "var(--card)", color: viewMode === mode ? "#fff" : "var(--muted-foreground)", fontSize: "12px", fontWeight: 600 }}>
              {mode === "table" ? "Tabela" : "Cards"}
            </button>
          ))}
        </div>
        <TableExportMenu title="Alunos" fileName="alunos" rows={filtered} columns={studentExportColumns} />
      </div>

      {loading ? (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>Carregando alunos...</div>
      ) : viewMode === "table" ? (
        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--muted)" }}>
                {["Aluno", "Orientador", "Progresso", "Status", "Ações"].map((h) => (
                  <th key={h} className="text-left px-4 py-3" style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((student, i) => {
                const st = STATUS_MAP[student.situacao_registrada];
                const progress = progressFor(student);
                const advisor = advisorById.get(student.orientador_id);
                return (
                  <tr key={student.id} style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none" }}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-full flex items-center justify-center" style={{ width: 34, height: 34, background: "#123C7A", color: "#fff", fontSize: "13px", fontWeight: 700, flexShrink: 0 }}>{student.nome.charAt(0)}</div>
                        <div>
                          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{student.nome}</p>
                          <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Mat. {student.matricula}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3"><p style={{ fontSize: "12px", color: "var(--foreground)" }}>{advisor?.nome ?? student.orientador_id}</p><p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{student.programa_id}</p></td>
                    <td className="px-4 py-3"><div className="flex items-center gap-2"><div className="rounded-full overflow-hidden" style={{ width: 60, height: 6, background: "var(--muted)" }}><div className="h-full rounded-full" style={{ width: `${progress}%`, background: progress > 70 ? "#1F8A70" : progress > 40 ? "#D4A017" : "#dc2626" }} /></div><span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)" }}>{progress}%</span></div></td>
                    <td className="px-4 py-3"><span className="flex items-center gap-1 px-2 py-1 rounded-lg w-fit" style={{ background: st.bg, color: st.color, fontSize: "11px", fontWeight: 600 }}>{st.icon} {st.label}</span></td>
                    <td className="px-4 py-3"><div className="flex items-center gap-1"><button onClick={() => { setSelectedStudentId(student.id); setCurrentPage("aluno-detail"); }} className="p-1.5 rounded-lg" style={{ color: "#123C7A" }} title="Ver detalhes"><Eye size={15} /></button>{canEdit && <button onClick={() => openEditForm(student)} className="p-1.5 rounded-lg" style={{ color: "#1F8A70" }} title="Editar"><Edit3 size={15} /></button>}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && <div className="text-center py-12"><GraduationCap size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} /><p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Nenhum aluno encontrado</p></div>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((student) => {
            const st = STATUS_MAP[student.situacao_registrada];
            const progress = progressFor(student);
            return (
              <div key={student.id} className="rounded-2xl p-5 transition-all cursor-pointer" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }} onClick={() => { setSelectedStudentId(student.id); setCurrentPage("aluno-detail"); }}>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3"><div className="rounded-full flex items-center justify-center" style={{ width: 42, height: 42, background: "#123C7A", color: "#fff", fontSize: "16px", fontWeight: 700 }}>{student.nome.charAt(0)}</div><div><p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{student.nome.split(" ").slice(0, 2).join(" ")}</p><p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Mat. {student.matricula}</p></div></div>
                  <span className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: st.bg, color: st.color, fontSize: "11px", fontWeight: 600 }}>{st.icon} {st.label}</span>
                </div>
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex justify-between"><span style={{ color: "var(--muted-foreground)" }}>Programa</span><span style={{ fontWeight: 600, color: "var(--foreground)" }}>{student.programa_id}</span></div>
                  <div className="flex justify-between"><span style={{ color: "var(--muted-foreground)" }}>Prazo</span><span style={{ fontWeight: 600, color: "var(--foreground)" }}>{formatDate(student.prazo_final)}</span></div>
                </div>
                <div className="mb-2 flex justify-between"><span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Progresso</span><span style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{progress}%</span></div>
                <div className="rounded-full overflow-hidden" style={{ height: 6, background: "var(--muted)" }}><div className="h-full rounded-full" style={{ width: `${progress}%`, background: progress > 70 ? "#1F8A70" : progress > 40 ? "#D4A017" : "#dc2626" }} /></div>
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <form onSubmit={handleSubmit} className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)", boxShadow: "0 30px 80px rgba(0,0,0,0.25)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>{editingStudent ? "Editar Aluno" : "Cadastrar Novo Aluno"}</h2>
              <button type="button" onClick={() => { setShowForm(false); setEditingStudent(null); }} style={{ color: "var(--muted-foreground)", fontSize: "20px", lineHeight: 1 }}>x</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nome Completo" className="col-span-2"><input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="E-mail"><input required disabled={Boolean(editingStudent)} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="Matrícula"><input required disabled={Boolean(editingStudent)} value={form.matricula} onChange={(e) => setForm({ ...form, matricula: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="Orientador" className="col-span-2"><select required value={form.orientador_id} onChange={(e) => setForm({ ...form, orientador_id: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle}><option value="">Selecione...</option>{advisors.map((advisor) => <option key={advisor.id} value={advisor.id}>{advisor.nome}</option>)}</select></Field>
              <Field label="Programa"><select required disabled={Boolean(editingStudent) || currentUser?.role === "orientador"} value={form.programa_id} onChange={(e) => setForm({ ...form, programa_id: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle}><option value="">Selecione um programa</option>{availablePrograms.map((program) => <option key={program.id} value={program.id}>{program.nome ?? program.id}</option>)}</select></Field>
              <Field label="Ingresso"><input required disabled={Boolean(editingStudent)} type="date" value={form.data_ingresso} onChange={(e) => setForm({ ...form, data_ingresso: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
            </div>
            <div className="flex gap-3 mt-6">
              <button type="button" onClick={() => { setShowForm(false); setEditingStudent(null); }} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "14px" }}>Cancelar</button>
              <button disabled={saving} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px", opacity: saving ? 0.7 : 1 }}>{saving ? "Salvando..." : editingStudent ? "Salvar" : "Cadastrar"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function Field({ label, className = "", children }: { label: string; className?: string; children: JSX.Element }) {
  return (
    <div className={className}>
      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{label}</label>
      {children}
    </div>
  );
}

const fieldStyle = {
  border: "1px solid var(--border)",
  background: "var(--input-background)",
  fontSize: "13px",
  color: "var(--foreground)",
};

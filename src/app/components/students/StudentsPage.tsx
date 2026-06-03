import { useState } from "react";
import { useApp } from "../../context/AppContext";
import { Search, Filter, Plus, Eye, Edit3, MoreHorizontal, ChevronDown, BookOpen, AlertTriangle, CheckCircle, Clock, GraduationCap } from "lucide-react";

const STUDENTS = [
  { id: "1", name: "Ana Paula Costa", matricula: "2021003", email: "ana.costa@pos.ufx.br", nivel: "Doutorado", orientador: "Prof. Dr. Roberto Almeida", programa: "PPGCC", ingresso: "2021/1", prazo: "2025/12", progresso: 72, status: "regular", creditos: 48, producoes: 6 },
  { id: "2", name: "Carlos Eduardo Lima", matricula: "2022001", email: "carlos.lima@pos.ufx.br", nivel: "Mestrado", orientador: "Profa. Dra. Carla Mendes", programa: "PPGCC", ingresso: "2022/2", prazo: "2025/6", progresso: 45, status: "atencao", creditos: 22, producoes: 2 },
  { id: "3", name: "Fernanda Souza", matricula: "2020002", email: "fernanda.souza@pos.ufx.br", nivel: "Doutorado", orientador: "Prof. Dr. João Batista", programa: "PPGCC", ingresso: "2020/1", prazo: "2025/12", progresso: 88, status: "regular", creditos: 54, producoes: 9 },
  { id: "4", name: "Marcos Oliveira", matricula: "2023001", email: "marcos.oliveira@pos.ufx.br", nivel: "Mestrado", orientador: "Profa. Dra. Carla Mendes", programa: "PPGCC", ingresso: "2023/1", prazo: "2025/6", progresso: 30, status: "critico", creditos: 12, producoes: 0 },
  { id: "5", name: "Juliana Martins", matricula: "2022002", email: "juliana.martins@pos.ufx.br", nivel: "Doutorado", orientador: "Prof. Dr. Roberto Almeida", programa: "PPGCC", ingresso: "2022/1", prazo: "2026/6", progresso: 55, status: "regular", creditos: 36, producoes: 4 },
  { id: "6", name: "Pedro Henrique", matricula: "2021004", email: "pedro.henrique@pos.ufx.br", nivel: "Mestrado", orientador: "Prof. Dr. João Batista", programa: "PPGCC", ingresso: "2021/2", prazo: "2025/3", progresso: 92, status: "regular", creditos: 28, producoes: 3 },
  { id: "7", name: "Beatriz Santos", matricula: "2023002", email: "beatriz.santos@pos.ufx.br", nivel: "Doutorado", orientador: "Profa. Dra. Carla Mendes", programa: "PPGEI", ingresso: "2023/2", prazo: "2027/12", progresso: 18, status: "regular", creditos: 8, producoes: 0 },
  { id: "8", name: "Lucas Ferreira", matricula: "2022003", email: "lucas.ferreira@pos.ufx.br", nivel: "Mestrado", orientador: "Prof. Dr. Roberto Almeida", programa: "PPGEI", ingresso: "2022/2", prazo: "2025/12", progresso: 60, status: "atencao", creditos: 18, producoes: 1 },
];

const STATUS_MAP = {
  regular: { label: "Regular", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle size={12} /> },
  atencao: { label: "Atenção", color: "#D4A017", bg: "#fef9c3", icon: <AlertTriangle size={12} /> },
  critico: { label: "Crítico", color: "#dc2626", bg: "#fee2e2", icon: <AlertTriangle size={12} /> },
  concluido: { label: "Concluído", color: "#3b82f6", bg: "#dbeafe", icon: <CheckCircle size={12} /> },
};

export function StudentsPage() {
  const { setCurrentPage, setSelectedStudentId } = useApp();
  const [search, setSearch] = useState("");
  const [filterNivel, setFilterNivel] = useState("todos");
  const [filterStatus, setFilterStatus] = useState("todos");
  const [viewMode, setViewMode] = useState<"table" | "cards">("table");
  const [showForm, setShowForm] = useState(false);

  const filtered = STUDENTS.filter((s) => {
    const matchSearch = s.name.toLowerCase().includes(search.toLowerCase()) || s.matricula.includes(search);
    const matchNivel = filterNivel === "todos" || s.nivel.toLowerCase() === filterNivel;
    const matchStatus = filterStatus === "todos" || s.status === filterStatus;
    return matchSearch && matchNivel && matchStatus;
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Gerenciamento de Alunos</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{STUDENTS.length} alunos cadastrados · {STUDENTS.filter(s => s.status === "regular").length} regulares</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-xl px-4 py-2.5"
          style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}
        >
          <Plus size={16} />
          Novo Aluno
        </button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6">
        {[
          { label: "Total", value: STUDENTS.length, color: "#123C7A", bg: "#eef3fc" },
          { label: "Regular", value: STUDENTS.filter(s => s.status === "regular").length, color: "#1F8A70", bg: "#dcfce7" },
          { label: "Atenção", value: STUDENTS.filter(s => s.status === "atencao").length, color: "#D4A017", bg: "#fef9c3" },
          { label: "Crítico", value: STUDENTS.filter(s => s.status === "critico").length, color: "#dc2626", bg: "#fee2e2" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl p-3 sm:p-4 flex items-center gap-2 sm:gap-3 min-w-0" style={{ background: stat.bg }}>
            <p className="flex-shrink-0" style={{ fontSize: "22px", fontWeight: 800, color: stat.color, lineHeight: 1.1 }}>{stat.value}</p>
            <p className="truncate min-w-0" style={{ fontSize: "13px", color: stat.color, fontWeight: 600 }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
          <input
            type="text"
            placeholder="Buscar por nome ou matrícula..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl pl-9 pr-4 py-2.5 outline-none"
            style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
          />
        </div>
        <select
          value={filterNivel}
          onChange={(e) => setFilterNivel(e.target.value)}
          className="rounded-xl px-3 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        >
          <option value="todos">Todos os Níveis</option>
          <option value="mestrado">Mestrado</option>
          <option value="doutorado">Doutorado</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="rounded-xl px-3 py-2.5 outline-none"
          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
        >
          <option value="todos">Todos os Status</option>
          <option value="regular">Regular</option>
          <option value="atencao">Atenção</option>
          <option value="critico">Crítico</option>
        </select>
        <div className="flex rounded-xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
          {(["table", "cards"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className="px-3 py-2 transition-colors"
              style={{
                background: viewMode === mode ? "#123C7A" : "var(--card)",
                color: viewMode === mode ? "#fff" : "var(--muted-foreground)",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              {mode === "table" ? "Tabela" : "Cards"}
            </button>
          ))}
        </div>
      </div>

      {viewMode === "table" ? (
        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--muted)" }}>
                {["Aluno", "Nível", "Orientador", "Progresso", "Créditos", "Produções", "Status", "Ações"].map((h) => (
                  <th key={h} className="text-left px-4 py-3" style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((student, i) => {
                const st = STATUS_MAP[student.status as keyof typeof STATUS_MAP];
                return (
                  <tr
                    key={student.id}
                    style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="rounded-full flex items-center justify-center" style={{ width: 34, height: 34, background: "#123C7A", color: "#fff", fontSize: "13px", fontWeight: 700, flexShrink: 0 }}>
                          {student.name.charAt(0)}
                        </div>
                        <div>
                          <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{student.name}</p>
                          <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Mat. {student.matricula}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="px-2 py-0.5 rounded-lg"
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          background: student.nivel === "Doutorado" ? "#eef3fc" : "#f0fdf4",
                          color: student.nivel === "Doutorado" ? "#123C7A" : "#1F8A70",
                        }}
                      >
                        {student.nivel}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p style={{ fontSize: "12px", color: "var(--foreground)" }}>{student.orientador.split(" ").slice(0, 3).join(" ")}</p>
                      <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{student.programa}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="rounded-full overflow-hidden" style={{ width: 60, height: 6, background: "var(--muted)" }}>
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${student.progresso}%`,
                              background: student.progresso > 70 ? "#1F8A70" : student.progresso > 40 ? "#D4A017" : "#dc2626",
                            }}
                          />
                        </div>
                        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)" }}>{student.progresso}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{student.creditos}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{student.producoes}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="flex items-center gap-1 px-2 py-1 rounded-lg w-fit"
                        style={{ background: st.bg, color: st.color, fontSize: "11px", fontWeight: 600 }}
                      >
                        {st.icon} {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => { setSelectedStudentId(student.id); setCurrentPage("aluno-detail"); }}
                          className="p-1.5 rounded-lg transition-colors"
                          style={{ color: "#123C7A" }}
                          title="Ver detalhes"
                          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#eef3fc"; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          className="p-1.5 rounded-lg transition-colors"
                          style={{ color: "#1F8A70" }}
                          title="Editar"
                          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#dcfce7"; }}
                          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                        >
                          <Edit3 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="text-center py-12">
              <GraduationCap size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
              <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Nenhum aluno encontrado</p>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((student) => {
            const st = STATUS_MAP[student.status as keyof typeof STATUS_MAP];
            return (
              <div
                key={student.id}
                className="rounded-2xl p-5 transition-all cursor-pointer"
                style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
                onClick={() => { setSelectedStudentId(student.id); setCurrentPage("aluno-detail"); }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = "0 8px 24px rgba(18,60,122,0.12)"; (e.currentTarget as HTMLElement).style.borderColor = "#123C7A"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = "0 2px 8px rgba(0,0,0,0.04)"; (e.currentTarget as HTMLElement).style.borderColor = "var(--border)"; }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full flex items-center justify-center" style={{ width: 42, height: 42, background: "#123C7A", color: "#fff", fontSize: "16px", fontWeight: 700 }}>
                      {student.name.charAt(0)}
                    </div>
                    <div>
                      <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{student.name.split(" ").slice(0, 2).join(" ")}</p>
                      <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Mat. {student.matricula}</p>
                    </div>
                  </div>
                  <span className="flex items-center gap-1 px-2 py-1 rounded-lg" style={{ background: st.bg, color: st.color, fontSize: "11px", fontWeight: 600 }}>
                    {st.icon} {st.label}
                  </span>
                </div>
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex justify-between">
                    <span style={{ color: "var(--muted-foreground)" }}>Nível</span>
                    <span style={{ fontWeight: 600, color: "var(--foreground)" }}>{student.nivel}</span>
                  </div>
                  <div className="flex justify-between">
                    <span style={{ color: "var(--muted-foreground)" }}>Programa</span>
                    <span style={{ fontWeight: 600, color: "var(--foreground)" }}>{student.programa}</span>
                  </div>
                  <div className="flex justify-between">
                    <span style={{ color: "var(--muted-foreground)" }}>Prazo</span>
                    <span style={{ fontWeight: 600, color: "var(--foreground)" }}>{student.prazo}</span>
                  </div>
                </div>
                <div className="mb-2 flex justify-between">
                  <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Progresso</span>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{student.progresso}%</span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 6, background: "var(--muted)" }}>
                  <div className="h-full rounded-full" style={{ width: `${student.progresso}%`, background: student.progresso > 70 ? "#1F8A70" : student.progresso > 40 ? "#D4A017" : "#dc2626" }} />
                </div>
                <div className="flex gap-3 mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                  <div className="text-center flex-1">
                    <p style={{ fontSize: "16px", fontWeight: 800, color: "#123C7A" }}>{student.creditos}</p>
                    <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Créditos</p>
                  </div>
                  <div className="text-center flex-1">
                    <p style={{ fontSize: "16px", fontWeight: 800, color: "#1F8A70" }}>{student.producoes}</p>
                    <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Produções</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* New Student Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <div className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)", boxShadow: "0 30px 80px rgba(0,0,0,0.25)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Cadastrar Novo Aluno</h2>
              <button onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)", fontSize: "20px", lineHeight: 1 }}>✕</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "Nome Completo", placeholder: "Nome do aluno", col: "col-span-2" },
                { label: "E-mail", placeholder: "email@pos.ufx.br", col: "" },
                { label: "Matrícula", placeholder: "2024001", col: "" },
                { label: "Orientador", placeholder: "Selecione...", col: "col-span-2" },
                { label: "Programa", placeholder: "PPGCC", col: "" },
                { label: "Ingresso", placeholder: "2024/1", col: "" },
              ].map((field) => (
                <div key={field.label} className={field.col}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{field.label}</label>
                  <input
                    placeholder={field.placeholder}
                    className="w-full rounded-xl px-3 py-2.5 outline-none"
                    style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px", color: "var(--foreground)" }}
                    onFocus={(e) => { e.currentTarget.style.borderColor = "#123C7A"; }}
                    onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
                  />
                </div>
              ))}
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Nível</label>
                <select className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }}>
                  <option>Mestrado</option>
                  <option>Doutorado</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>Prazo</label>
                <input type="month" className="w-full rounded-xl px-3 py-2.5 outline-none" style={{ border: "1px solid var(--border)", background: "var(--input-background)", fontSize: "13px" }} />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600, fontSize: "14px" }}>
                Cancelar
              </button>
              <button onClick={() => setShowForm(false)} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
                Cadastrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

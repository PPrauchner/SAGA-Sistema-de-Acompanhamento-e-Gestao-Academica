import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRightLeft, CheckCircle, RefreshCw, Search, UserCheck } from "lucide-react";

import { getAdvisors, type Advisor } from "@/api/advisorsApi";
import { getStudents, type Student } from "@/api/studentsApi";
import { directTransfer } from "@/api/transfersApi";
import { useApp } from "../../context/AppContext";

const TERMINAL_STATUSES = new Set(["concluido", "desligado"]);

export function TransfersPage() {
  const { token, setCurrentPage, setSelectedStudentId } = useApp();
  const [students, setStudents] = useState<Student[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [studentId, setStudentId] = useState("");
  const [advisorId, setAdvisorId] = useState("");
  const [observacao, setObservacao] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [studentsData, advisorsData] = await Promise.all([
        getStudents(authToken),
        getAdvisors(authToken),
      ]);
      setStudents(studentsData);
      setAdvisors(advisorsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar transferencias");
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
  const selectedStudent = students.find((student) => student.id === studentId) ?? null;
  const originAdvisor = selectedStudent ? advisorById.get(selectedStudent.orientador_id) : null;
  const selectedStudentTerminal = selectedStudent
    ? TERMINAL_STATUSES.has(selectedStudent.situacao_registrada)
    : false;

  const availableAdvisors = selectedStudent
    ? advisors.filter(
        (advisor) =>
          advisor.programa_id === selectedStudent.programa_id &&
          advisor.id !== selectedStudent.orientador_id,
      )
    : [];

  const filteredStudents = students.filter((student) => {
    const query = search.toLowerCase();
    return (
      student.nome.toLowerCase().includes(query) ||
      student.matricula.toLowerCase().includes(query)
    );
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !studentId || !advisorId) return;

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await directTransfer(token, {
        student_id: studentId,
        orientador_destino_id: advisorId,
        observacao: observacao || null,
      });
      setSuccess(result.message);
      setAdvisorId("");
      setObservacao("");
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao transferir aluno");
    } finally {
      setSaving(false);
    }
  }

  function openStudentDetail(): void {
    if (!selectedStudent) return;
    setSelectedStudentId(selectedStudent.id);
    setCurrentPage("aluno-detail");
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 style={{ color: "var(--foreground)", fontSize: "24px", fontWeight: 700 }}>
            Transferências
          </h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            Mova orientandos entre orientadores do mesmo programa.
          </p>
        </div>
        <button
          onClick={() => token && loadData(token)}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}
        >
          <RefreshCw size={16} />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="rounded-lg px-4 py-3" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca" }}>
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg px-4 py-3 flex items-center gap-2" style={{ background: "#dcfce7", color: "#166534", border: "1px solid #bbf7d0" }}>
          <CheckCircle size={16} />
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6">
        <section className="rounded-xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="relative mb-4">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar aluno por nome ou matrícula"
              className="w-full rounded-lg pl-10 pr-3 py-2 outline-none"
              style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
            />
          </div>

          {loading ? (
            <div className="py-16 text-center" style={{ color: "var(--muted-foreground)" }}>Carregando...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ color: "var(--muted-foreground)", fontSize: "12px", textAlign: "left" }}>
                    <th className="px-3 py-2">Aluno</th>
                    <th className="px-3 py-2">Programa</th>
                    <th className="px-3 py-2">Orientador atual</th>
                    <th className="px-3 py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredStudents.map((student) => {
                    const active = student.id === studentId;
                    const advisor = advisorById.get(student.orientador_id);
                    return (
                      <tr
                        key={student.id}
                        onClick={() => {
                          setStudentId(student.id);
                          setAdvisorId("");
                          setSuccess(null);
                        }}
                        className="cursor-pointer"
                        style={{ background: active ? "rgba(18,60,122,0.08)" : "transparent", borderTop: "1px solid var(--border)" }}
                      >
                        <td className="px-3 py-3">
                          <p style={{ color: "var(--foreground)", fontWeight: 600 }}>{student.nome}</p>
                          <p style={{ color: "var(--muted-foreground)", fontSize: "12px" }}>{student.matricula}</p>
                        </td>
                        <td className="px-3 py-3" style={{ color: "var(--foreground)", fontSize: "13px" }}>{student.programa_id}</td>
                        <td className="px-3 py-3" style={{ color: "var(--foreground)", fontSize: "13px" }}>{advisor?.nome ?? student.orientador_id}</td>
                        <td className="px-3 py-3">
                          <span className="rounded-full px-2 py-1" style={{ background: TERMINAL_STATUSES.has(student.situacao_registrada) ? "#fee2e2" : "#eef3fc", color: TERMINAL_STATUSES.has(student.situacao_registrada) ? "#991b1b" : "#123C7A", fontSize: "12px", fontWeight: 600 }}>
                            {student.situacao_registrada}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <form onSubmit={handleSubmit} className="rounded-xl p-5 space-y-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <div className="rounded-lg flex items-center justify-center" style={{ width: 36, height: 36, background: "#123C7A", color: "#fff" }}>
              <ArrowRightLeft size={18} />
            </div>
            <div>
              <h2 style={{ color: "var(--foreground)", fontSize: "16px", fontWeight: 700 }}>Mover direto</h2>
              <p style={{ color: "var(--muted-foreground)", fontSize: "12px" }}>Auto-aprovado pela coordenação</p>
            </div>
          </div>

          <div className="rounded-lg p-3" style={{ background: "var(--input-background)", border: "1px solid var(--border)" }}>
            <p style={{ color: "var(--muted-foreground)", fontSize: "12px" }}>Aluno selecionado</p>
            <p style={{ color: "var(--foreground)", fontWeight: 700 }}>{selectedStudent?.nome ?? "Nenhum aluno selecionado"}</p>
            {selectedStudent && (
              <button type="button" onClick={openStudentDetail} style={{ color: "#123C7A", fontSize: "12px", fontWeight: 700, marginTop: 6 }}>
                Abrir detalhe do aluno
              </button>
            )}
          </div>

          {selectedStudentTerminal && (
            <div className="rounded-lg px-3 py-2" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>
              Aluno em status terminal não pode ser transferido.
            </div>
          )}

          <div>
            <label style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}>Orientador destino</label>
            <select
              value={advisorId}
              onChange={(event) => setAdvisorId(event.target.value)}
              disabled={!selectedStudent}
              className="w-full rounded-lg mt-1 px-3 py-2 outline-none"
              style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
            >
              <option value="">Selecione...</option>
              {availableAdvisors.map((advisor) => (
                <option key={advisor.id} value={advisor.id}>
                  {advisor.nome} ({advisor.orientandos_ativos}/{advisor.limite_orientandos})
                </option>
              ))}
            </select>
          </div>

          <textarea
            value={observacao}
            onChange={(event) => setObservacao(event.target.value)}
            placeholder="Observação opcional"
            rows={4}
            className="w-full rounded-lg px-3 py-2 outline-none resize-none"
            style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
          />

          <button
            type="submit"
            disabled={saving || !selectedStudent || !advisorId || selectedStudentTerminal}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2"
            style={{ background: saving || !selectedStudent || !advisorId ? "var(--muted)" : "#123C7A", color: "#fff", fontSize: "14px", fontWeight: 700, opacity: saving ? 0.7 : 1 }}
          >
            <UserCheck size={16} />
            {saving ? "Transferindo..." : "Confirmar transferência"}
          </button>

          {originAdvisor && (
            <p style={{ color: "var(--muted-foreground)", fontSize: "12px" }}>
              Origem atual: {originAdvisor.nome}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

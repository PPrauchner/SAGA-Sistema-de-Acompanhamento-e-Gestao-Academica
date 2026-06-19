import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ArrowRightLeft,
  CheckCircle,
  RefreshCw,
  Send,
  UserCheck,
  XCircle,
} from "lucide-react";

import { getAdvisors, type Advisor } from "@/api/advisorsApi";
import { getStudents, type Student } from "@/api/studentsApi";
import {
  approveTransferRequest,
  cancelTransferRequest,
  createTransferRequest,
  directTransfer,
  getTransfers,
  rejectTransferRequest,
  type TransferRequest,
} from "@/api/transfersApi";
import { useApp } from "../../context/AppContext";

const TERMINAL_STATUSES = new Set(["concluido", "desligado"]);

function statusLabel(status: TransferRequest["status"]): string {
  const labels: Record<TransferRequest["status"], string> = {
    pendente: "Pendente",
    aprovada: "Aprovada",
    rejeitada: "Rejeitada",
    cancelada: "Cancelada",
  };
  return labels[status];
}

export function TransfersPage() {
  const { currentUser, token, setCurrentPage, setSelectedStudentId } = useApp();
  const [students, setStudents] = useState<Student[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [transfers, setTransfers] = useState<TransferRequest[]>([]);
  const [studentId, setStudentId] = useState("");
  const [advisorId, setAdvisorId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const isCoord = currentUser?.role === "coordenacao";
  const isAdvisor = currentUser?.role === "orientador";

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [studentsData, advisorsData, transfersData] = await Promise.all([
        getStudents(authToken),
        getAdvisors(authToken),
        getTransfers(authToken),
      ]);
      setStudents(studentsData);
      setAdvisors(advisorsData);
      setTransfers(transfersData);
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
  const studentById = useMemo(
    () => new Map(students.map((student) => [student.id, student])),
    [students],
  );
  const selectedStudent = students.find((student) => student.id === studentId) ?? null;
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
  const pendingTransfers = transfers.filter((transfer) => transfer.status === "pendente");

  async function runAction(action: () => Promise<{ message: string }>): Promise<void> {
    if (!token) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await action();
      setSuccess(result.message);
      setStudentId("");
      setAdvisorId("");
      setMotivo("");
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha na operacao");
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token || !studentId || !advisorId) return;

    await runAction(() =>
      isCoord
        ? directTransfer(token, {
            student_id: studentId,
            orientador_destino_id: advisorId,
            observacao: motivo || null,
          })
        : createTransferRequest(token, {
            student_id: studentId,
            orientador_destino_id: advisorId,
            motivo: motivo || null,
          }),
    );
  }

  function openStudentDetail(student: Student): void {
    setSelectedStudentId(student.id);
    setCurrentPage("aluno-detail");
  }

  if (!isCoord && !isAdvisor) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 style={{ color: "var(--foreground)", fontSize: "24px", fontWeight: 700 }}>
            Transferências
          </h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            {isCoord
              ? "Aprove solicitações e mova orientandos diretamente."
              : "Solicite transferência dos seus orientandos para outro orientador."}
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
          <h2 style={{ color: "var(--foreground)", fontSize: "16px", fontWeight: 700, marginBottom: 12 }}>
            Solicitações
          </h2>
          {loading ? (
            <div className="py-16 text-center" style={{ color: "var(--muted-foreground)" }}>Carregando...</div>
          ) : pendingTransfers.length === 0 ? (
            <div className="py-16 text-center" style={{ color: "var(--muted-foreground)" }}>Nenhuma solicitação pendente.</div>
          ) : (
            <div className="space-y-3">
              {pendingTransfers.map((transfer) => {
                const student = studentById.get(transfer.student_id);
                const origin = transfer.orientador_origem_id ? advisorById.get(transfer.orientador_origem_id) : null;
                const destination = advisorById.get(transfer.orientador_destino_id);
                return (
                  <div key={transfer.id} className="rounded-lg p-4" style={{ background: "var(--input-background)", border: "1px solid var(--border)" }}>
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                      <div>
                        <p style={{ color: "var(--foreground)", fontWeight: 700 }}>{student?.nome ?? transfer.student_id}</p>
                        <p style={{ color: "var(--muted-foreground)", fontSize: "13px" }}>
                          {origin?.nome ?? transfer.orientador_origem_id} → {destination?.nome ?? transfer.orientador_destino_id}
                        </p>
                        <span className="inline-block rounded-full px-2 py-1 mt-2" style={{ background: "#fef9c3", color: "#854d0e", fontSize: "12px", fontWeight: 700 }}>
                          {statusLabel(transfer.status)}
                        </span>
                      </div>
                      {isCoord ? (
                        <div className="flex flex-col gap-2 md:min-w-[260px]">
                          <input
                            value={rejectReason[transfer.id] ?? ""}
                            onChange={(event) => setRejectReason((prev) => ({ ...prev, [transfer.id]: event.target.value }))}
                            placeholder="Motivo para rejeitar"
                            className="rounded-lg px-3 py-2 outline-none"
                            style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "13px" }}
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              disabled={saving}
                              onClick={() => token && runAction(() => approveTransferRequest(token, transfer.id))}
                              className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg px-3 py-2"
                              style={{ background: "#123C7A", color: "#fff", fontSize: "13px", fontWeight: 700 }}
                            >
                              <UserCheck size={14} />
                              Aprovar
                            </button>
                            <button
                              type="button"
                              disabled={saving}
                              onClick={() => token && runAction(() => rejectTransferRequest(token, transfer.id, rejectReason[transfer.id] ?? ""))}
                              className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg px-3 py-2"
                              style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px", fontWeight: 700 }}
                            >
                              <XCircle size={14} />
                              Rejeitar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          type="button"
                          disabled={saving}
                          onClick={() => token && runAction(() => cancelTransferRequest(token, transfer.id))}
                          className="inline-flex items-center justify-center gap-1 rounded-lg px-3 py-2"
                          style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px", fontWeight: 700 }}
                        >
                          <XCircle size={14} />
                          Cancelar
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <form onSubmit={handleSubmit} className="rounded-xl p-5 space-y-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <div className="rounded-lg flex items-center justify-center" style={{ width: 36, height: 36, background: "#123C7A", color: "#fff" }}>
              <ArrowRightLeft size={18} />
            </div>
            <div>
              <h2 style={{ color: "var(--foreground)", fontSize: "16px", fontWeight: 700 }}>
                {isCoord ? "Mover direto" : "Solicitar transferência"}
              </h2>
              <p style={{ color: "var(--muted-foreground)", fontSize: "12px" }}>
                {isCoord ? "Auto-aprovado pela coordenação" : "Enviado para aprovação da coordenação"}
              </p>
            </div>
          </div>

          <div>
            <label style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}>Aluno</label>
            <select
              value={studentId}
              onChange={(event) => {
                setStudentId(event.target.value);
                setAdvisorId("");
              }}
              className="w-full rounded-lg mt-1 px-3 py-2 outline-none"
              style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
            >
              <option value="">Selecione...</option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.nome} ({student.matricula})
                </option>
              ))}
            </select>
            {selectedStudent && (
              <button type="button" onClick={() => openStudentDetail(selectedStudent)} style={{ color: "#123C7A", fontSize: "12px", fontWeight: 700, marginTop: 6 }}>
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
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            placeholder={isCoord ? "Observação opcional" : "Justificativa opcional"}
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
            {isCoord ? <UserCheck size={16} /> : <Send size={16} />}
            {saving ? "Salvando..." : isCoord ? "Confirmar transferência" : "Enviar solicitação"}
          </button>
        </form>
      </div>
    </div>
  );
}

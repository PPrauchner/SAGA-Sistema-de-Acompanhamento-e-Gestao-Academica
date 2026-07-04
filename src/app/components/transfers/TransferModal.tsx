import { useState, useEffect } from "react";
import { useApp } from "@/app/context/AppContext";
import { ArrowRightLeft, UserCheck, Send, X } from "lucide-react";
import { createTransferRequest, directTransfer } from "@/api/transfersApi";
import { getStudents, Student } from "@/api/studentsApi";
import { getAdvisors, Advisor } from "@/api/advisorsApi";

export function TransferModal({ onClose, onSuccess, initialStudentId }: { onClose: () => void, onSuccess: () => void, initialStudentId?: string }) {
  const { token, currentUser, activeView } = useApp();
  const [students, setStudents] = useState<Student[]>([]);
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  
  const [studentId, setStudentId] = useState(initialStudentId || "");
  const [advisorId, setAdvisorId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  const isCoord = currentUser?.role === "coordenacao" && activeView === "coordenador";

  useEffect(() => {
    async function loadData() {
      if (!token) return;
      try {
        const [studs, advs] = await Promise.all([
          getStudents(token),
          getAdvisors(token)
        ]);
        // Se for orientador, só pode transferir os seus orientandos
        if (currentUser?.role === "orientador") {
           // Encontrar o advisor logado
           const me = advs.find(a => a.uid === currentUser.id);
           if (me) {
             setStudents(studs.filter(s => s.orientador_id === me.id));
           }
        } else {
           setStudents(studs);
        }
        setAdvisors(advs);
      } catch (err: any) {
        alert("Erro ao carregar dados: " + err.message);
      } finally {
        setFetching(false);
      }
    }
    loadData();
  }, [token, currentUser, activeView]);

  const selectedStudent = students.find(s => s.id === studentId);
  const selectedStudentTerminal = selectedStudent?.situacao_registrada === "concluido" || selectedStudent?.situacao_registrada === "desligado";
  const selectedAdvisor = advisors.find(a => a.id === advisorId);
  const selectedAdvisorHasCapacity = selectedAdvisor ? (selectedAdvisor.orientandos_ativos < selectedAdvisor.limite_orientandos) : false;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !studentId || !advisorId) return;

    setLoading(true);
    try {
      if (isCoord) {
        await directTransfer(token, { student_id: studentId, orientador_destino_id: advisorId, observacao: motivo });
      } else {
        await createTransferRequest(token, { student_id: studentId, orientador_destino_id: advisorId, motivo });
      }
      onSuccess();
    } catch (err: any) {
      alert("Erro ao solicitar transferência: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2">
            <div className="rounded-lg flex items-center justify-center w-8 h-8" style={{ background: "#123C7A", color: "#fff" }}>
              <ArrowRightLeft size={16} />
            </div>
            <h2 className="text-lg font-bold" style={{ color: "var(--foreground)" }}>
              {isCoord ? "Transferência Direta" : "Solicitar Transferência"}
            </h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-black/5 text-gray-500">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {fetching ? (
            <div className="text-center text-sm py-4">Carregando dados...</div>
          ) : (
            <>
              <div>
                <label style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}>Aluno</label>
                <select
                  value={studentId}
                  onChange={(e) => { setStudentId(e.target.value); setAdvisorId(""); }}
                  className="w-full rounded-lg mt-1 px-3 py-2 outline-none"
                  style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
                  required
                >
                  <option value="">Selecione...</option>
                  {students.map(s => (
                    <option key={s.id} value={s.id}>{s.nome} ({s.matricula})</option>
                  ))}
                </select>
                {selectedStudentTerminal && (
                  <p className="mt-1 text-xs text-red-600">Aluno em status terminal não pode ser transferido.</p>
                )}
              </div>

              <div>
                <label style={{ color: "var(--foreground)", fontSize: "13px", fontWeight: 600 }}>Orientador destino</label>
                <select
                  value={advisorId}
                  onChange={(e) => setAdvisorId(e.target.value)}
                  disabled={!studentId}
                  className="w-full rounded-lg mt-1 px-3 py-2 outline-none"
                  style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
                  required
                >
                  <option value="">Selecione...</option>
                  {advisors.map(a => {
                    const full = a.orientandos_ativos >= a.limite_orientandos;
                    return (
                      <option key={a.id} value={a.id} disabled={full || a.id === selectedStudent?.orientador_id}>
                        {a.nome} ({a.orientandos_ativos}/{a.limite_orientandos}) {full ? "- Sem vagas" : ""}
                      </option>
                    )
                  })}
                </select>
              </div>

              <textarea
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                placeholder={isCoord ? "Observação opcional" : "Justificativa obrigatória"}
                rows={3}
                required={!isCoord}
                className="w-full rounded-lg px-3 py-2 outline-none resize-none"
                style={{ background: "var(--input-background)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: "14px" }}
              />

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={loading || !studentId || !advisorId || selectedStudentTerminal || !selectedAdvisorHasCapacity}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 transition-opacity"
                  style={{ 
                    background: "#123C7A", 
                    color: "#fff", 
                    fontSize: "14px", 
                    fontWeight: 700, 
                    opacity: (loading || !studentId || !advisorId || selectedStudentTerminal || !selectedAdvisorHasCapacity) ? 0.5 : 1 
                  }}
                >
                  {isCoord ? <UserCheck size={16} /> : <Send size={16} />}
                  {loading ? "Processando..." : (isCoord ? "Confirmar Transferência" : "Enviar Solicitação")}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  );
}

import { FormEvent, useEffect, useState } from "react";
import { BookOpen, Eye, Plus, Search, Users } from "lucide-react";

import {
  createAdvisor,
  getAdvisors,
  type Advisor,
  type AdvisorCreatePayload,
  updateAdvisor,
} from "@/api/advisorsApi";
import { programsApi, type Program } from "@/api/programsApi";
import { useAuth } from "@/hooks/useAuth";

const emptyForm: AdvisorCreatePayload = {
  uid: null,
  nome: "",
  email: "",
  departamento: "",
  lattes: "",
  programa_id: "",
  limite_orientandos: 5,
};

const fieldStyle = {
  border: "1px solid var(--border)",
  background: "var(--input-background)",
  fontSize: "13px",
  color: "var(--foreground)",
};

export function AdvisorsPage() {
  const { token, role } = useAuth();
  const [advisors, setAdvisors] = useState<Advisor[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<AdvisorCreatePayload>(emptyForm);
  const [editingAdvisor, setEditingAdvisor] = useState<Advisor | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [advisorsData, programsData] = await Promise.all([
        getAdvisors(authToken),
        programsApi.getPrograms(authToken),
      ]);
      setAdvisors(advisorsData);
      setPrograms(programsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar orientadores");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) void loadData(token);
  }, [token]);

  const filtered = advisors.filter((advisor) => {
    const term = search.toLowerCase();
    return (
      advisor.nome.toLowerCase().includes(term) ||
      advisor.departamento.toLowerCase().includes(term) ||
      advisor.email.toLowerCase().includes(term)
    );
  });

  function openCreateForm(): void {
    setEditingAdvisor(null);
    setForm({ ...emptyForm, programa_id: programs[0]?.id ?? "" });
    setInviteToken(null);
    setShowForm(true);
  }

  function openEditForm(advisor: Advisor): void {
    setEditingAdvisor(advisor);
    setForm({
      uid: advisor.uid ?? null,
      nome: advisor.nome,
      email: advisor.email,
      departamento: advisor.departamento,
      lattes: advisor.lattes ?? "",
      programa_id: advisor.programa_id,
      limite_orientandos: advisor.limite_orientandos,
    });
    setInviteToken(null);
    setShowForm(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) return;
    if (!editingAdvisor && !form.programa_id) {
      setError("Selecione um programa para cadastrar o orientador");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editingAdvisor) {
        await updateAdvisor(token, editingAdvisor.id, {
          nome: form.nome,
          departamento: form.departamento,
          lattes: form.lattes,
          limite_orientandos: form.limite_orientandos,
        });
        setShowForm(false);
      } else {
        const result = await createAdvisor(token, form);
        setInviteToken(result.invite_token);
        setShowForm(false);
      }
      setForm(emptyForm);
      setEditingAdvisor(null);
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao cadastrar orientador");
    } finally {
      setSaving(false);
    }
  }

  const activeCount = advisors.length;
  const studentCount = advisors.reduce((sum, advisor) => sum + advisor.orientandos_ativos, 0);
  const capacity = advisors.reduce((sum, advisor) => sum + advisor.limite_orientandos, 0);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Orientadores</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{advisors.length} orientadores cadastrados</p>
        </div>
        <button onClick={openCreateForm} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> Novo Orientador
        </button>
      </div>

      {error && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>{error}</div>}
      {inviteToken && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#dcfce7", color: "#166534", fontSize: "13px" }}>Convite criado: {inviteToken}</div>}

      <div className="grid grid-cols-3 gap-4 mb-6">
        <Stat label="Ativos" value={activeCount} color="#123C7A" />
        <Stat label="Orientandos" value={studentCount} color="#1F8A70" />
        <Stat label="Capacidade" value={capacity} color="#D4A017" />
      </div>

      <div className="relative mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
        <input placeholder="Buscar orientador..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full max-w-sm rounded-xl pl-9 pr-4 py-2.5 outline-none" style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }} />
      </div>

      {loading ? (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>Carregando orientadores...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filtered.map((advisor) => {
            const usage = advisor.limite_orientandos > 0 ? advisor.orientandos_ativos / advisor.limite_orientandos : 0;
            const statusColor = usage >= 1 ? "#dc2626" : usage >= 0.8 ? "#D4A017" : "#1F8A70";
            const isPendingInvite = !advisor.uid;
            return (
              <div key={advisor.id} className="rounded-2xl p-5 transition-all" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
                <div className="flex items-start gap-4 mb-4">
                  <div className="rounded-2xl flex items-center justify-center flex-shrink-0" style={{ width: 52, height: 52, background: "#eef3fc" }}>
                    <span style={{ color: "#123C7A", fontSize: "20px", fontWeight: 800 }}>{advisor.nome.charAt(0)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>{advisor.nome}</p>
                          {role === "coordenacao" && isPendingInvite && (
                            <span className="px-2 py-0.5 rounded-lg" style={{ background: "#fef3c7", color: "#92400e", fontSize: "11px", fontWeight: 700 }}>
                              Convite Pendente
                            </span>
                          )}
                        </div>
                        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{advisor.departamento}</p>
                        <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{advisor.email}</p>
                      </div>
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: statusColor }} title="Capacidade de orientação" />
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap mb-4">
                  <span className="px-2 py-1 rounded-lg" style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "11px" }}>{advisor.programa_id}</span>
                  {advisor.lattes && <a href={advisor.lattes} target="_blank" rel="noreferrer" className="px-2 py-1 rounded-lg" style={{ background: "#eef3fc", color: "#123C7A", fontSize: "11px" }}>Lattes</a>}
                </div>

                <div className="grid grid-cols-3 gap-3 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                  <Metric icon={<Users size={13} />} label="Orientandos" value={`${advisor.orientandos_ativos}/${advisor.limite_orientandos}`} color="#123C7A" />
                  <Metric icon={<BookOpen size={13} />} label="Programa" value={advisor.programa_id} color="#1F8A70" />
                  <div className="text-center">
                    <button onClick={() => openEditForm(advisor)} className="flex items-center justify-center gap-1 mx-auto px-3 py-1.5 rounded-lg transition-colors" style={{ background: "#eef3fc", color: "#123C7A", fontSize: "12px", fontWeight: 600 }}>
                      <Eye size={13} /> Editar
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>Nenhum orientador encontrado</div>}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <form onSubmit={handleSubmit} className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>{editingAdvisor ? "Editar Orientador" : "Cadastrar Orientador"}</h2>
              <button type="button" onClick={() => { setShowForm(false); setEditingAdvisor(null); }} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>x</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nome Completo" className="col-span-2"><input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="E-mail"><input required disabled={Boolean(editingAdvisor)} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="Departamento"><input required value={form.departamento} onChange={(e) => setForm({ ...form, departamento: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="Programa"><select required disabled={Boolean(editingAdvisor)} value={form.programa_id} onChange={(e) => setForm({ ...form, programa_id: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle}><option value="">Selecione um programa</option>{programs.map((program) => <option key={program.id} value={program.id}>{program.nome ?? program.id}</option>)}</select></Field>
              <Field label="Limite"><input required type="number" min={1} value={form.limite_orientandos} onChange={(e) => setForm({ ...form, limite_orientandos: Number(e.target.value) })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
              <Field label="Lattes URL" className="col-span-2"><input value={form.lattes ?? ""} onChange={(e) => setForm({ ...form, lattes: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} /></Field>
            </div>
            <div className="flex gap-3 mt-6">
              <button type="button" onClick={() => { setShowForm(false); setEditingAdvisor(null); }} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button disabled={saving} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, opacity: saving ? 0.7 : 1 }}>{saving ? "Salvando..." : editingAdvisor ? "Salvar" : "Cadastrar"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: "28px", fontWeight: 800, color }}>{value}</p>
      <p style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>{label}</p>
    </div>
  );
}

function Metric({ icon, label, value, color }: { icon: JSX.Element; label: string; value: string; color: string }) {
  return (
    <div className="text-center">
      <div className="flex items-center justify-center gap-1 mb-1" style={{ color }}>
        {icon}
        <p style={{ fontSize: "16px", fontWeight: 800 }}>{value}</p>
      </div>
      <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{label}</p>
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

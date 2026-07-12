import { FormEvent, useEffect, useState } from "react";
import { Building2, Pencil, Plus, Search, Trash2 } from "lucide-react";

import {
  createDepartment,
  deleteDepartment,
  getDepartments,
  updateDepartment,
  type Department,
  type DepartmentCreatePayload,
} from "@/api/departmentsApi";
import { useAuth } from "@/hooks/useAuth";
import { useEscapeClose } from "@/hooks/useEscapeClose";

const emptyForm: DepartmentCreatePayload = {
  nome: "",
  instituicao: "",
};

const fieldStyle = {
  border: "1px solid var(--border)",
  background: "var(--input-background)",
  fontSize: "13px",
  color: "var(--foreground)",
};

export function DepartmentsPage() {
  const { token } = useAuth();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<DepartmentCreatePayload>(emptyForm);
  const [editingDepartment, setEditingDepartment] = useState<Department | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Department | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEscapeClose(showForm, () => { setShowForm(false); setEditingDepartment(null); setError(null); });
  useEscapeClose(Boolean(confirmDelete), () => setConfirmDelete(null));

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      setDepartments(await getDepartments(authToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar departamentos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) void loadData(token);
  }, [token]);

  const filtered = departments.filter((department) =>
    department.nome.toLowerCase().includes(search.toLowerCase()),
  );

  function openCreateForm(): void {
    setEditingDepartment(null);
    setForm(emptyForm);
    setError(null);
    setShowForm(true);
  }

  function openEditForm(department: Department): void {
    setEditingDepartment(department);
    setForm({ nome: department.nome, instituicao: department.instituicao ?? "" });
    setError(null);
    setShowForm(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      if (editingDepartment) {
        await updateDepartment(token, editingDepartment.id, form);
      } else {
        await createDepartment(token, form);
      }
      setShowForm(false);
      setForm(emptyForm);
      setEditingDepartment(null);
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : editingDepartment ? "Falha ao editar departamento" : "Falha ao cadastrar departamento");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(): Promise<void> {
    if (!token || !confirmDelete) return;
    setSaving(true);
    setError(null);
    try {
      await deleteDepartment(token, confirmDelete.id);
      setConfirmDelete(null);
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao excluir departamento");
      setConfirmDelete(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Departamentos</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>{departments.length} departamentos cadastrados</p>
        </div>
        <button onClick={openCreateForm} className="flex items-center gap-2 rounded-xl px-4 py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}>
          <Plus size={16} /> Novo Departamento
        </button>
      </div>

      {error && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>{error}</div>}

      <div className="relative mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted-foreground)" }} />
        <input placeholder="Buscar departamento..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full max-w-sm rounded-xl pl-9 pr-4 py-2.5 outline-none" style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }} />
      </div>

      {loading ? (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>Carregando departamentos...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filtered.map((department) => (
            <div key={department.id} className="rounded-2xl p-5 transition-all" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
              <div className="flex items-start gap-4 mb-4">
                <div className="rounded-2xl flex items-center justify-center flex-shrink-0" style={{ width: 52, height: 52, background: "#eef3fc" }}>
                  <Building2 size={22} style={{ color: "#123C7A" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>{department.nome}</p>
                  <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{department.instituicao || "—"}</p>
                </div>
              </div>

              <div className="flex gap-2 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
                <button onClick={() => openEditForm(department)} className="flex flex-1 items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors" style={{ background: "#eef3fc", color: "#123C7A", fontSize: "12px", fontWeight: 600 }}>
                  <Pencil size={13} /> Editar
                </button>
                <button onClick={() => setConfirmDelete(department)} className="flex flex-1 items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "12px", fontWeight: 600 }}>
                  <Trash2 size={13} /> Excluir
                </button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>Nenhum departamento encontrado</div>}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <form onSubmit={handleSubmit} className="rounded-2xl p-6 w-full max-w-lg mx-4" style={{ background: "var(--card)" }}>
            <div className="flex justify-between items-center mb-6">
              <h2 style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>{editingDepartment ? "Editar Departamento" : "Cadastrar Departamento"}</h2>
              <button type="button" onClick={() => { setShowForm(false); setEditingDepartment(null); setError(null); }} style={{ color: "var(--muted-foreground)", fontSize: "20px" }}>x</button>
            </div>
            {error && <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>{error}</div>}
            <div className="grid grid-cols-1 gap-4">
              <Field label="Nome">
                <input required value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} />
              </Field>
              <Field label="Instituição">
                <input value={form.instituicao ?? ""} onChange={(e) => setForm({ ...form, instituicao: e.target.value })} className="w-full rounded-xl px-3 py-2.5 outline-none" style={fieldStyle} />
              </Field>
            </div>
            <div className="flex gap-3 mt-6">
              <button type="button" onClick={() => { setShowForm(false); setEditingDepartment(null); setError(null); }} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button disabled={saving} className="flex-1 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontWeight: 600, opacity: saving ? 0.7 : 1 }}>{saving ? "Salvando..." : editingDepartment ? "Salvar" : "Cadastrar"}</button>
            </div>
          </form>
        </div>
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.4)" }}>
          <div className="rounded-2xl p-6 w-full max-w-sm mx-4" style={{ background: "var(--card)" }}>
            <h2 className="mb-4" style={{ fontSize: "18px", fontWeight: 700, color: "var(--foreground)" }}>Confirmar Exclusão</h2>
            <p className="mb-6" style={{ fontSize: "14px", color: "var(--muted-foreground)" }}>
              Tem certeza que deseja excluir o departamento <strong>{confirmDelete.nome}</strong>? Departamentos com programas vinculados não podem ser excluídos.
            </p>
            <div className="flex gap-3">
              <button type="button" onClick={() => setConfirmDelete(null)} className="flex-1 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 600 }}>Cancelar</button>
              <button onClick={handleDelete} disabled={saving} className="flex-1 rounded-xl py-2.5" style={{ background: "#dc2626", color: "#fff", fontWeight: 600, opacity: saving ? 0.7 : 1 }}>{saving ? "Excluindo..." : "Confirmar Exclusão"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: JSX.Element }) {
  return (
    <div>
      <label style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)", display: "block", marginBottom: "6px" }}>{label}</label>
      {children}
    </div>
  );
}

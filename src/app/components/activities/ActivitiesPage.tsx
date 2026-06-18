import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Plus,
  X,
  Upload,
  FileText,
  Paperclip,
  CheckCircle2,
  XCircle,
  Clock,
  Circle,
  Award,
} from "lucide-react";

import { useApp } from "../../context/AppContext";
import { useAuth } from "@/hooks/useAuth";
import {
  createActivity,
  getActivities,
  getActivityTypes,
  uploadComprovante,
  type Activity,
  type ActivityCreateStatus,
  type ActivityType,
} from "@/api/activitiesApi";

// ─── Config de apresentação ─────────────────────────────────────────────────

interface StatusConfig {
  label: string;
  color: string;
  bg: string;
  icon: React.ReactNode;
}

const STATUS_CFG: Record<string, StatusConfig> = {
  rascunho: { label: "Rascunho", color: "#64748b", bg: "#f1f5f9", icon: <Circle size={11} /> },
  enviado: { label: "Enviado", color: "#0891b2", bg: "#e0f7fa", icon: <Clock size={11} /> },
  aprovado: { label: "Aprovado", color: "#1F8A70", bg: "#dcfce7", icon: <CheckCircle2 size={11} /> },
  rejeitado: { label: "Rejeitado", color: "#dc2626", bg: "#fee2e2", icon: <XCircle size={11} /> },
};

const CATEGORIA_LABEL: Record<string, string> = {
  basico: "Básico",
  especifico: "Específico",
  tecnologico: "Tecnológico",
};

function statusCfg(status: string): StatusConfig {
  return STATUS_CFG[status] ?? STATUS_CFG.rascunho;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("pt-BR");
}

interface FormState {
  tipo_id: string;
  descricao: string;
  data_realizacao: string;
  status: ActivityCreateStatus;
  file: File | null;
}

const EMPTY_FORM: FormState = {
  tipo_id: "",
  descricao: "",
  data_realizacao: "",
  status: "enviado",
  file: null,
};

// ─── Página ──────────────────────────────────────────────────────────────────

export function ActivitiesPage() {
  const { currentUser } = useApp();
  const { token, role } = useAuth();

  const [activities, setActivities] = useState<Activity[]>([]);
  const [types, setTypes] = useState<ActivityType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const canRegister = role === "aluno";

  async function loadData(authToken: string): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [activityList, typeList] = await Promise.all([
        getActivities(authToken),
        getActivityTypes(authToken),
      ]);
      setActivities(activityList);
      setTypes(typeList.filter((type) => type.ativo));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar atividades");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token) void loadData(token);
  }, [token]);

  const selectedType = useMemo(
    () => types.find((type) => type.id === form.tipo_id) ?? null,
    [types, form.tipo_id],
  );

  function openForm(): void {
    setForm(EMPTY_FORM);
    setFeedback(null);
    setShowForm(true);
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (!token) return;
    if (!form.tipo_id || !form.descricao || !form.data_realizacao) {
      setError("Preencha tipo, descrição e data de realização.");
      return;
    }
    if (selectedType?.exige_comprovante && !form.file) {
      setError("Este tipo de atividade exige o envio de um comprovante.");
      return;
    }

    setSaving(true);
    setError(null);
    setFeedback(null);
    try {
      const result = await createActivity(token, {
        tipo_id: form.tipo_id,
        descricao: form.descricao,
        data_realizacao: form.data_realizacao,
        comprovante_url: null,
        status: form.status,
      });

      if (form.file) {
        await uploadComprovante(token, result.id, form.file);
      }

      // A elegibilidade preliminar (RL04) é calculada no POST /activities, antes do upload
      // do comprovante — por isso não a afirmamos quando um arquivo foi anexado nesta
      // submissão (o comprovante recém-enviado pode alterar o resultado).
      setFeedback(
        form.file
          ? "Atividade registrada e comprovante enviado."
          : result.elegibilidade_preliminar
            ? "Atividade registrada. Elegibilidade preliminar (RL04): elegível."
            : "Atividade registrada. Elegibilidade preliminar (RL04): ainda não elegível.",
      );
      setShowForm(false);
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao registrar atividade");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: "4px" }}>Atividades Creditáveis</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>
            {activities.length} atividade(s) registrada(s)
            {currentUser?.name ? ` · ${currentUser.name}` : ""}
          </p>
        </div>
        {canRegister && (
          <button
            onClick={openForm}
            className="flex items-center gap-2 rounded-xl px-4 py-2.5"
            style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}
          >
            <Plus size={16} />
            Nova Atividade
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#fee2e2", color: "#991b1b", fontSize: "13px" }}>
          {error}
        </div>
      )}
      {feedback && (
        <div className="rounded-xl px-4 py-3 mb-4" style={{ background: "#dcfce7", color: "#166534", fontSize: "13px" }}>
          {feedback}
        </div>
      )}

      {showForm && canRegister && (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl p-5 mb-6"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--foreground)" }}>Nova atividade</h2>
            <button type="button" onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)" }}>
              <X size={18} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Tipo de atividade</span>
              <select
                value={form.tipo_id}
                onChange={(e) => setForm((f) => ({ ...f, tipo_id: e.target.value }))}
                className="rounded-xl px-3 py-2.5 outline-none"
                style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
              >
                <option value="">Selecione…</option>
                {types.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.nome} ({CATEGORIA_LABEL[type.categoria] ?? type.categoria})
                  </option>
                ))}
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Data de realização</span>
              <input
                type="date"
                value={form.data_realizacao}
                onChange={(e) => setForm((f) => ({ ...f, data_realizacao: e.target.value }))}
                className="rounded-xl px-3 py-2.5 outline-none"
                style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
              />
            </label>

            <label className="flex flex-col gap-1 sm:col-span-2">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Descrição</span>
              <textarea
                value={form.descricao}
                onChange={(e) => setForm((f) => ({ ...f, descricao: e.target.value }))}
                rows={3}
                className="rounded-xl px-3 py-2.5 outline-none resize-none"
                style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Situação inicial</span>
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as ActivityCreateStatus }))}
                className="rounded-xl px-3 py-2.5 outline-none"
                style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
              >
                <option value="enviado">Enviar para validação</option>
                <option value="rascunho">Salvar como rascunho</option>
              </select>
            </label>

            <label className="flex flex-col gap-1">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>
                Comprovante {selectedType?.exige_comprovante ? "(obrigatório)" : "(opcional)"}
              </span>
              <div
                className="flex items-center gap-2 rounded-xl px-3 py-2.5"
                style={{ background: "var(--card)", border: "1px dashed var(--border)" }}
              >
                <Paperclip size={15} style={{ color: "var(--muted-foreground)" }} />
                <input
                  type="file"
                  accept="application/pdf,image/png,image/jpeg"
                  onChange={(e) => setForm((f) => ({ ...f, file: e.target.files?.[0] ?? null }))}
                  style={{ fontSize: "12px", color: "var(--foreground)" }}
                />
              </div>
            </label>
          </div>

          <div className="flex justify-end gap-2 mt-5">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-xl px-4 py-2.5"
              style={{ border: "1px solid var(--border)", color: "var(--muted-foreground)", fontSize: "14px", fontWeight: 600 }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-xl px-4 py-2.5"
              style={{ background: "#1F8A70", color: "#fff", fontSize: "14px", fontWeight: 600, opacity: saving ? 0.6 : 1 }}
            >
              <Upload size={15} />
              {saving ? "Registrando…" : "Registrar"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="rounded-2xl p-8 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)" }}>
          Carregando atividades…
        </div>
      ) : activities.length === 0 ? (
        <div className="rounded-2xl py-12 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <Award size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
          <p style={{ color: "var(--muted-foreground)", fontSize: "14px" }}>Nenhuma atividade registrada</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activities.map((activity) => {
            const st = statusCfg(activity.status);
            return (
              <div
                key={activity.id}
                className="rounded-2xl p-5"
                style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}
              >
                <div className="flex items-start justify-between mb-3 gap-2">
                  <div>
                    <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>
                      {activity.tipo_nome ?? "Atividade"}
                    </p>
                    {activity.categoria && (
                      <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                        {CATEGORIA_LABEL[activity.categoria] ?? activity.categoria}
                      </p>
                    )}
                  </div>
                  <span
                    className="flex items-center gap-1 px-2 py-1 rounded-lg flex-shrink-0"
                    style={{ background: st.bg, color: st.color, fontSize: "11px", fontWeight: 600 }}
                  >
                    {st.icon} {st.label}
                  </span>
                </div>

                <p style={{ fontSize: "13px", color: "var(--foreground)", marginBottom: "12px" }}>{activity.descricao}</p>

                <div className="space-y-1.5" style={{ fontSize: "12px" }}>
                  <div className="flex justify-between">
                    <span style={{ color: "var(--muted-foreground)" }}>Data</span>
                    <span style={{ color: "var(--foreground)", fontWeight: 600 }}>{formatDate(activity.data_realizacao)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span style={{ color: "var(--muted-foreground)" }}>Créditos</span>
                    <span style={{ color: "var(--foreground)", fontWeight: 600 }}>{activity.creditos_gerados}</span>
                  </div>
                  {typeof activity.elegivel === "boolean" && (
                    <div className="flex justify-between">
                      <span style={{ color: "var(--muted-foreground)" }}>Elegível (RL04)</span>
                      <span style={{ color: activity.elegivel ? "#1F8A70" : "#dc2626", fontWeight: 600 }}>
                        {activity.elegivel ? "Sim" : "Não"}
                      </span>
                    </div>
                  )}
                </div>

                {activity.comprovante_url && (
                  <a
                    href={activity.comprovante_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 mt-3"
                    style={{ fontSize: "12px", color: "#123C7A", fontWeight: 600 }}
                  >
                    <FileText size={13} /> Ver comprovante
                  </a>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

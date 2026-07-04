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
  MessageSquare,
  Send,
} from "lucide-react";

import { useApp } from "../../context/AppContext";
import { useAuth } from "@/hooks/useAuth";
import { useChecklistStudent } from "@/hooks/useChecklistStudent";
import {
  createActivity,
  createActivityForOrientando,
  emitirParecer,
  getActivities,
  getActivityTypes,
  uploadComprovante,
  validarAtividade,
  type Activity,
  type ActivityCreateStatus,
  type ActivityType,
  type ValidateAction,
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
  // data_realizacao e uma data de calendario armazenada a meia-noite UTC; formata em UTC
  // para nao deslocar um dia em fusos negativos (bug #268).
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("pt-BR", { timeZone: "UTC" });
}

interface FormState {
  tipo_id: string;
  descricao: string;
  data_realizacao: string;
  status: ActivityCreateStatus;
  file: File | null;
  // Usados apenas quando o orientador cria para um orientando (issue #263).
  aluno_id: string;
  parecer: string;
}

const EMPTY_FORM: FormState = {
  tipo_id: "",
  descricao: "",
  data_realizacao: "",
  status: "enviado",
  file: null,
  aluno_id: "",
  parecer: "",
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

  const [parecerTarget, setParecerTarget] = useState<Activity | null>(null);
  const [parecerText, setParecerText] = useState("");
  const [parecerSaving, setParecerSaving] = useState(false);

  const [validateTarget, setValidateTarget] = useState<Activity | null>(null);
  const [validateObs, setValidateObs] = useState("");
  const [validateCreditos, setValidateCreditos] = useState("");
  const [validateSaving, setValidateSaving] = useState(false);

  const canRegister = role === "aluno";
  const canCreateForOrientando = role === "orientador";
  const canCreate = canRegister || canCreateForOrientando;
  const canDarParecer = role === "orientador";
  const canValidar = role === "coordenacao";

  // Lista de orientandos para o seletor do formulário do orientador (mesma fonte do
  // checklist/plano de trabalho). Para o aluno, o hook retorna students=null.
  const { students } = useChecklistStudent();

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

    // Fluxo do orientador: cria para um orientando, com parecer, direto para a coordenação.
    if (canCreateForOrientando) {
      if (!form.aluno_id || !form.tipo_id || !form.descricao || !form.data_realizacao || !form.parecer.trim()) {
        setError("Selecione o orientando e preencha tipo, descrição, data e parecer.");
        return;
      }
      setSaving(true);
      setError(null);
      setFeedback(null);
      try {
        await createActivityForOrientando(token, {
          aluno_id: form.aluno_id,
          tipo_id: form.tipo_id,
          descricao: form.descricao,
          // Meia-noite UTC explicita, consistente com a submissao do aluno (bug #268).
          data_realizacao: `${form.data_realizacao}T00:00:00Z`,
          comprovante_url: null,
          parecer: form.parecer.trim(),
        });
        setFeedback("Atividade criada e enviada para a coordenação.");
        setShowForm(false);
        await loadData(token);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Falha ao criar atividade");
      } finally {
        setSaving(false);
      }
      return;
    }

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
        // Envia a data como meia-noite UTC explicita para nao depender da interpretacao
        // de datetime naive no backend (bug #268).
        data_realizacao: `${form.data_realizacao}T00:00:00Z`,
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

  function openParecer(activity: Activity): void {
    setParecerTarget(activity);
    setParecerText(activity.parecer_orientador ?? "");
    setError(null);
    setFeedback(null);
  }

  async function handleEmitirParecer(): Promise<void> {
    if (!token || !parecerTarget) return;
    if (!parecerText.trim()) {
      setError("Escreva o parecer antes de enviar.");
      return;
    }

    setParecerSaving(true);
    setError(null);
    setFeedback(null);
    try {
      await emitirParecer(token, parecerTarget.id, parecerText.trim());
      setFeedback("Parecer registrado.");
      setParecerTarget(null);
      setParecerText("");
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao registrar parecer");
    } finally {
      setParecerSaving(false);
    }
  }

  function openValidate(activity: Activity): void {
    setValidateTarget(activity);
    setValidateObs(activity.observacao_coordenacao ?? "");
    setValidateCreditos(String(activity.creditos_gerados ?? ""));
    setError(null);
    setFeedback(null);
  }

  async function handleValidar(activity: Activity, acao: ValidateAction): Promise<void> {
    if (!token) return;

    setValidateSaving(true);
    setError(null);
    setFeedback(null);
    try {
      const creditos =
        acao === "aprovar" && validateCreditos.trim() !== "" ? Number(validateCreditos) : null;
      const result = await validarAtividade(token, activity.id, {
        acao,
        observacao: validateObs.trim() || null,
        creditos_concedidos: creditos,
      });
      const label = acao === "aprovar" ? "aprovada" : "rejeitada";
      setFeedback(
        result.motor_inferencia_executado
          ? `Atividade ${label}. O motor reavaliou a situação do aluno.`
          : `Atividade ${label}.`,
      );
      setValidateTarget(null);
      setValidateObs("");
      setValidateCreditos("");
      await loadData(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao validar atividade");
    } finally {
      setValidateSaving(false);
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
        {canCreate && (
          <button
            onClick={openForm}
            className="flex items-center gap-2 rounded-xl px-4 py-2.5"
            style={{ background: "#123C7A", color: "#fff", fontWeight: 600, fontSize: "14px" }}
          >
            <Plus size={16} />
            {canCreateForOrientando ? "Nova atividade para orientando" : "Nova Atividade"}
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

      {showForm && canCreate && (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl p-5 mb-6"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 style={{ fontSize: "16px", fontWeight: 700, color: "var(--foreground)" }}>
              {canCreateForOrientando ? "Nova atividade para orientando" : "Nova atividade"}
            </h2>
            <button type="button" onClick={() => setShowForm(false)} style={{ color: "var(--muted-foreground)" }}>
              <X size={18} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {canCreateForOrientando && (
              <label className="flex flex-col gap-1 sm:col-span-2">
                <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Orientando</span>
                <select
                  value={form.aluno_id}
                  onChange={(e) => setForm((f) => ({ ...f, aluno_id: e.target.value }))}
                  className="rounded-xl px-3 py-2.5 outline-none"
                  style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
                >
                  <option value="">Selecione o orientando…</option>
                  {students?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
            )}

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

            {canCreateForOrientando && (
              <label className="flex flex-col gap-1 sm:col-span-2">
                <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted-foreground)" }}>Parecer do orientador</span>
                <textarea
                  value={form.parecer}
                  onChange={(e) => setForm((f) => ({ ...f, parecer: e.target.value }))}
                  rows={3}
                  placeholder="Endosso da atividade — vai direto para a fila da coordenação."
                  className="rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "13px", color: "var(--foreground)" }}
                />
              </label>
            )}

            {canRegister && (
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
            )}

            {canRegister && (
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
            )}
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

                {activity.parecer_orientador && (
                  <div
                    className="mt-3 rounded-xl px-3 py-2.5"
                    style={{ background: "#f1f5f9", border: "1px solid var(--border)" }}
                  >
                    <p
                      className="flex items-center gap-1.5 mb-1"
                      style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)" }}
                    >
                      <MessageSquare size={12} /> Parecer do orientador
                    </p>
                    <p style={{ fontSize: "12px", color: "var(--foreground)", whiteSpace: "pre-wrap" }}>
                      {activity.parecer_orientador}
                    </p>
                  </div>
                )}

                {activity.observacao_coordenacao && (
                  <div
                    className="mt-3 rounded-xl px-3 py-2.5"
                    style={{ background: "#f1f5f9", border: "1px solid var(--border)" }}
                  >
                    <p
                      className="flex items-center gap-1.5 mb-1"
                      style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)" }}
                    >
                      <MessageSquare size={12} /> Observação da coordenação
                    </p>
                    <p style={{ fontSize: "12px", color: "var(--foreground)", whiteSpace: "pre-wrap" }}>
                      {activity.observacao_coordenacao}
                    </p>
                  </div>
                )}

                {canDarParecer && activity.status === "enviado" && (
                  parecerTarget?.id === activity.id ? (
                    <div className="mt-3">
                      <textarea
                        value={parecerText}
                        onChange={(e) => setParecerText(e.target.value)}
                        rows={3}
                        placeholder="Escreva seu parecer…"
                        className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                        style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "12px", color: "var(--foreground)" }}
                      />
                      <div className="flex justify-end gap-2 mt-2">
                        <button
                          type="button"
                          onClick={() => setParecerTarget(null)}
                          className="rounded-lg px-3 py-1.5"
                          style={{ border: "1px solid var(--border)", color: "var(--muted-foreground)", fontSize: "12px", fontWeight: 600 }}
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          onClick={handleEmitirParecer}
                          disabled={parecerSaving}
                          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5"
                          style={{ background: "#123C7A", color: "#fff", fontSize: "12px", fontWeight: 600, opacity: parecerSaving ? 0.6 : 1 }}
                        >
                          <Send size={12} />
                          {parecerSaving ? "Enviando…" : "Enviar parecer"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => openParecer(activity)}
                      className="flex items-center gap-1.5 mt-3"
                      style={{ fontSize: "12px", color: "#123C7A", fontWeight: 600 }}
                    >
                      <MessageSquare size={13} />
                      {activity.parecer_orientador ? "Editar parecer" : "Dar parecer"}
                    </button>
                  )
                )}

                {canValidar && activity.status === "enviado" && (
                  validateTarget?.id === activity.id ? (
                    <div className="mt-3 space-y-2">
                      <textarea
                        value={validateObs}
                        onChange={(e) => setValidateObs(e.target.value)}
                        rows={2}
                        placeholder="Observação (opcional)…"
                        className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                        style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "12px", color: "var(--foreground)" }}
                      />
                      <label className="flex items-center justify-between gap-2">
                        <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                          Créditos concedidos
                        </span>
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          value={validateCreditos}
                          onChange={(e) => setValidateCreditos(e.target.value)}
                          className="w-24 rounded-lg px-2 py-1.5 outline-none text-right"
                          style={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: "12px", color: "var(--foreground)" }}
                        />
                      </label>
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setValidateTarget(null)}
                          className="rounded-lg px-3 py-1.5"
                          style={{ border: "1px solid var(--border)", color: "var(--muted-foreground)", fontSize: "12px", fontWeight: 600 }}
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleValidar(activity, "rejeitar")}
                          disabled={validateSaving}
                          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5"
                          style={{ background: "#dc2626", color: "#fff", fontSize: "12px", fontWeight: 600, opacity: validateSaving ? 0.6 : 1 }}
                        >
                          <XCircle size={12} />
                          Rejeitar
                        </button>
                        <button
                          type="button"
                          onClick={() => handleValidar(activity, "aprovar")}
                          disabled={validateSaving}
                          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5"
                          style={{ background: "#1F8A70", color: "#fff", fontSize: "12px", fontWeight: 600, opacity: validateSaving ? 0.6 : 1 }}
                        >
                          <CheckCircle2 size={12} />
                          Aprovar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => openValidate(activity)}
                      className="flex items-center gap-1.5 mt-3"
                      style={{ fontSize: "12px", color: "#123C7A", fontWeight: 600 }}
                    >
                      <CheckCircle2 size={13} />
                      Validar atividade
                    </button>
                  )
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

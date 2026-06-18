import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Calendar, CheckCircle2, Circle, Clock3, Loader2, Plus, Send, X } from "lucide-react";

import {
  addProgressUpdate,
  createTask,
  getWorkPlan,
  updateTaskStatus,
  type TaskPriority,
  type TaskStatus,
  type WorkPlan,
  type WorkPlanStage,
  type WorkPlanTask,
} from "@/api/workPlanApi";
import { useApp } from "@/app/context/AppContext";
import { useAuth } from "@/hooks/useAuth";

type Modal =
  | { kind: "task"; stage: WorkPlanStage }
  | { kind: "progress"; task: WorkPlanTask }
  | null;

const STATUS_COLUMNS: { id: TaskStatus; label: string; icon: JSX.Element }[] = [
  { id: "pendente", label: "Pendente", icon: <Circle size={14} /> },
  { id: "em_andamento", label: "Em andamento", icon: <Clock3 size={14} /> },
  { id: "atrasada", label: "Atrasada", icon: <AlertCircle size={14} /> },
  { id: "concluida", label: "Concluida", icon: <CheckCircle2 size={14} /> },
];

const STATUS_LABEL: Record<TaskStatus, string> = {
  pendente: "Pendente",
  em_andamento: "Em andamento",
  atrasada: "Atrasada",
  concluida: "Concluida",
};

const PRIORITY_LABEL: Record<TaskPriority, string> = {
  baixa: "Baixa",
  media: "Media",
  alta: "Alta",
};

export function WorkPlanPage() {
  const { currentUser, selectedStudentId } = useApp();
  const { token, studentId } = useAuth();
  const [plan, setPlan] = useState<WorkPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<Modal>(null);

  const targetStudentId = selectedStudentId ?? studentId ?? "aluno_regular";
  const isAdvisor = currentUser?.role === "orientador" || currentUser?.role === "coordenacao" || !currentUser;
  const isStudent = currentUser?.role === "aluno" || !currentUser;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPlan(await getWorkPlan(targetStudentId, token ?? undefined));
    } catch {
      setError("Nao foi possivel carregar o plano de trabalho.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [targetStudentId, token]);

  const tasks = useMemo(() => plan?.stages.flatMap((stage) => stage.tasks.map((task) => ({ ...task, stage }))) ?? [], [plan]);
  const concludedStages = plan?.stages.filter((stage) => stage.status === "concluida").length ?? 0;

  async function changeStatus(taskId: string, status: TaskStatus) {
    setSaving(true);
    try {
      await updateTaskStatus(taskId, status, token ?? undefined);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateTask(stage: WorkPlanStage, data: { titulo: string; descricao: string; prazo: string; prioridade: TaskPriority }) {
    setSaving(true);
    try {
      await createTask(
        stage.stage_id,
        { ...data, prazo: `${data.prazo}T00:00:00Z` },
        token ?? undefined,
      );
      setModal(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleProgress(task: WorkPlanTask, data: { conteudo: string; percentual: number }) {
    setSaving(true);
    try {
      await addProgressUpdate(task.task_id, data, token ?? undefined);
      setModal(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[360px] items-center justify-center">
        <Loader2 className="animate-spin" size={26} style={{ color: "var(--muted-foreground)" }} />
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--foreground)", fontWeight: 700 }}>{error ?? "Plano nao encontrado."}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-lg p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p style={{ fontSize: 12, color: "var(--muted-foreground)", fontWeight: 700 }}>
              {plan.student_id} · {concludedStages}/{plan.stages.length} etapas concluidas
            </p>
            <h1 style={{ fontSize: 22, lineHeight: 1.2, fontWeight: 800, color: "var(--foreground)", marginTop: 4 }}>
              {plan.titulo}
            </h1>
            <p style={{ fontSize: 13, color: "var(--muted-foreground)", marginTop: 8, maxWidth: 760 }}>
              {plan.descricao ?? "Plano de trabalho do discente com etapas, tarefas e atualizacoes de progresso."}
            </p>
          </div>
          <div className="min-w-[220px]">
            <div className="flex items-center justify-between" style={{ fontSize: 12, color: "var(--muted-foreground)", fontWeight: 700 }}>
              <span>Progresso geral</span>
              <span>{Math.round(plan.progresso_percentual)}%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full" style={{ background: "var(--muted)" }}>
              <div className="h-full rounded-full" style={{ width: `${plan.progresso_percentual}%`, background: "#1F8A70" }} />
            </div>
            {plan.fato_plano_concluido && (
              <p className="mt-2 flex items-center gap-1.5" style={{ fontSize: 12, color: "#047857", fontWeight: 700 }}>
                <CheckCircle2 size={14} /> {plan.fato_plano_concluido}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {STATUS_COLUMNS.map((column) => {
          const columnTasks = tasks.filter((item) => item.status === column.id);
          return (
            <div key={column.id} className="min-h-[420px] rounded-lg p-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="flex items-center gap-2" style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)" }}>
                  {column.icon} {column.label}
                </h2>
                <span style={{ fontSize: 12, color: "var(--muted-foreground)", fontWeight: 700 }}>{columnTasks.length}</span>
              </div>
              <div className="space-y-3">
                {columnTasks.map(({ stage, ...task }) => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    stage={stage}
                    disabled={saving}
                    canUpdateStatus={isAdvisor}
                    canAddProgress={isStudent}
                    onStatus={changeStatus}
                    onProgress={() => setModal({ kind: "progress", task })}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </section>

      <section className="rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="mb-3 flex items-center justify-between">
          <h2 style={{ fontSize: 14, fontWeight: 800, color: "var(--foreground)" }}>Etapas</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {plan.stages.map((stage) => (
            <div key={stage.stage_id} className="rounded-lg p-3" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)" }}>{stage.nome}</p>
                  <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 4 }}>
                    {formatDate(stage.data_inicio)} ate {formatDate(stage.data_fim)}
                  </p>
                </div>
                {isAdvisor && (
                  <button
                    type="button"
                    onClick={() => setModal({ kind: "task", stage })}
                    className="flex h-8 w-8 items-center justify-center rounded-md"
                    style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)" }}
                    aria-label="Criar task"
                  >
                    <Plus size={15} />
                  </button>
                )}
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full" style={{ background: "var(--border)" }}>
                <div className="h-full rounded-full" style={{ width: `${stage.progresso_percentual}%`, background: "#123C7A" }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {modal?.kind === "task" && (
        <TaskModal stage={modal.stage} saving={saving} onClose={() => setModal(null)} onSave={(data) => handleCreateTask(modal.stage, data)} />
      )}
      {modal?.kind === "progress" && (
        <ProgressModal task={modal.task} saving={saving} onClose={() => setModal(null)} onSave={(data) => handleProgress(modal.task, data)} />
      )}
    </div>
  );
}

function TaskCard({
  task,
  stage,
  disabled,
  canUpdateStatus,
  canAddProgress,
  onStatus,
  onProgress,
}: {
  task: WorkPlanTask;
  stage: WorkPlanStage;
  disabled: boolean;
  canUpdateStatus: boolean;
  canAddProgress: boolean;
  onStatus: (taskId: string, status: TaskStatus) => Promise<void>;
  onProgress: () => void;
}) {
  return (
    <article className="rounded-lg p-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)", lineHeight: 1.35 }}>{task.titulo}</p>
          <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 4 }}>{stage.nome}</p>
        </div>
        <span className="rounded-md px-2 py-1" style={{ fontSize: 10, fontWeight: 800, color: "#123C7A", background: "#eef3fc" }}>
          {PRIORITY_LABEL[task.prioridade]}
        </span>
      </div>
      {task.descricao && <p style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 8, lineHeight: 1.45 }}>{task.descricao}</p>}
      <div className="mt-3 flex items-center justify-between" style={{ fontSize: 11, color: "var(--muted-foreground)" }}>
        <span className="flex items-center gap-1.5"><Calendar size={12} /> {formatDate(task.prazo)}</span>
        <span>{Math.round(task.progresso_percentual)}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ background: "var(--muted)" }}>
        <div className="h-full rounded-full" style={{ width: `${task.progresso_percentual}%`, background: task.status === "atrasada" ? "#dc2626" : "#1F8A70" }} />
      </div>
      {task.ultima_atualizacao && (
        <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 8 }}>
          Ultimo update: {task.ultima_atualizacao.conteudo}
        </p>
      )}
      <div className="mt-3 flex gap-2">
        {canUpdateStatus && (
          <select
            value={task.status}
            disabled={disabled}
            onChange={(event) => void onStatus(task.task_id, event.target.value as TaskStatus)}
            className="min-w-0 flex-1 rounded-md px-2 py-2"
            style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: 12 }}
          >
            {STATUS_COLUMNS.map((status) => <option key={status.id} value={status.id}>{STATUS_LABEL[status.id]}</option>)}
          </select>
        )}
        {canAddProgress && (
          <button
            type="button"
            disabled={disabled}
            onClick={onProgress}
            className="flex items-center gap-1.5 rounded-md px-2.5 py-2"
            style={{ background: "#123C7A", color: "#fff", fontSize: 12, fontWeight: 800 }}
          >
            <Send size={13} /> Progresso
          </button>
        )}
      </div>
    </article>
  );
}

function TaskModal({
  stage,
  saving,
  onClose,
  onSave,
}: {
  stage: WorkPlanStage;
  saving: boolean;
  onClose: () => void;
  onSave: (data: { titulo: string; descricao: string; prazo: string; prioridade: TaskPriority }) => void;
}) {
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [prazo, setPrazo] = useState("");
  const [prioridade, setPrioridade] = useState<TaskPriority>("media");

  return (
    <ModalShell title={`Nova task em ${stage.nome}`} onClose={onClose}>
      <div className="space-y-3">
        <Input label="Titulo" value={titulo} onChange={setTitulo} />
        <Textarea label="Descricao" value={descricao} onChange={setDescricao} />
        <Input label="Prazo" type="date" value={prazo} onChange={setPrazo} />
        <Select label="Prioridade" value={prioridade} onChange={(value) => setPrioridade(value as TaskPriority)}>
          <option value="baixa">Baixa</option>
          <option value="media">Media</option>
          <option value="alta">Alta</option>
        </Select>
        <button
          type="button"
          disabled={saving || !titulo || !prazo}
          onClick={() => onSave({ titulo, descricao, prazo, prioridade })}
          className="w-full rounded-md py-2.5"
          style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 800, opacity: saving || !titulo || !prazo ? 0.6 : 1 }}
        >
          Criar task
        </button>
      </div>
    </ModalShell>
  );
}

function ProgressModal({
  task,
  saving,
  onClose,
  onSave,
}: {
  task: WorkPlanTask;
  saving: boolean;
  onClose: () => void;
  onSave: (data: { conteudo: string; percentual: number }) => void;
}) {
  const [conteudo, setConteudo] = useState("");
  const [percentual, setPercentual] = useState(task.progresso_percentual);

  return (
    <ModalShell title="Registrar progresso" onClose={onClose}>
      <div className="space-y-3">
        <p style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)" }}>{task.titulo}</p>
        <Textarea label="Atualizacao" value={conteudo} onChange={setConteudo} />
        <div>
          <label style={labelStyle}>Percentual: {Math.round(percentual)}%</label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={percentual}
            onChange={(event) => setPercentual(Number(event.target.value))}
            style={{ width: "100%", accentColor: "#123C7A" }}
          />
        </div>
        <button
          type="button"
          disabled={saving || !conteudo}
          onClick={() => onSave({ conteudo, percentual })}
          className="w-full rounded-md py-2.5"
          style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 800, opacity: saving || !conteudo ? 0.6 : 1 }}
        >
          Enviar progresso
        </button>
      </div>
    </ModalShell>
  );
}

function ModalShell({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(15,23,42,0.45)" }}>
      <div className="w-full max-w-md rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 24px 70px rgba(0,0,0,0.25)" }}>
        <div className="mb-4 flex items-center justify-between">
          <h2 style={{ fontSize: 16, fontWeight: 800, color: "var(--foreground)" }}>{title}</h2>
          <button type="button" onClick={onClose} className="flex h-8 w-8 items-center justify-center rounded-md" style={{ background: "var(--muted)" }}>
            <X size={16} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  marginBottom: 5,
  fontSize: 11,
  fontWeight: 800,
  color: "var(--muted-foreground)",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "var(--background)",
  color: "var(--foreground)",
  padding: "9px 10px",
  fontSize: 13,
};

function Input({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input type={type} value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle} />
    </div>
  );
}

function Textarea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} style={{ ...inputStyle, minHeight: 86, resize: "vertical" }} />
    </div>
  );
}

function Select({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
        {children}
      </select>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(value));
}

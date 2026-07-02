import { useEffect, useMemo, useState } from "react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { AlertCircle, Calendar, CheckCircle2, Circle, Clock3, Loader2, Plus, Send, Trash2, X } from "lucide-react";

import {
  addProgressUpdate,
  createStage,
  createTask,
  createWorkPlan,
  deleteTask,
  getWorkPlan,
  updateTaskStatus,
  type TaskPriority,
  type TaskStatus,
  type WorkPlan,
  type WorkPlanStage,
  type WorkPlanTask,
} from "@/api/workPlanApi";
import { ApiError } from "@/api/http";
import { useApp } from "@/app/context/AppContext";
import { useAuth } from "@/hooks/useAuth";

type Modal =
  | { kind: "task"; stage: WorkPlanStage }
  | { kind: "progress"; task: WorkPlanTask }
  | { kind: "plan" }
  | { kind: "stage" }
  | { kind: "confirmDelete"; task: WorkPlanTask }
  | null;

const TASK_DND_TYPE = "work-plan-task";

// As 3 colunas movieis do quadro. "Atrasado" nao e coluna: virou badge derivado.
const STATUS_COLUMNS: { id: TaskStatus; label: string; icon: JSX.Element }[] = [
  { id: "pendente", label: "Pendente", icon: <Circle size={14} /> },
  { id: "em_andamento", label: "Em andamento", icon: <Clock3 size={14} /> },
  { id: "concluido", label: "Concluido", icon: <CheckCircle2 size={14} /> },
];

const PRIORITY_LABEL: Record<TaskPriority, string> = {
  baixa: "Baixa",
  media: "Media",
  alta: "Alta",
};

// "Atrasado" e derivado (overlay A04): task vencida e nao-concluida. Nao e um
// status que o usuario seta nem uma coluna do quadro.
function isTaskOverdue(task: WorkPlanTask): boolean {
  if (task.status === "concluido") return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(task.prazo) < today;
}

// O backend ainda emite o status legado "atrasado"; mapeamos para a coluna
// "em andamento" ja que as colunas movieis sao pendente/em_andamento/concluido.
function columnStatusOf(status: TaskStatus): TaskStatus {
  return status === "atrasado" ? "em_andamento" : status;
}

// Update otimista: substitui o status de uma task no plano em memoria, sem
// recarregar do servidor.
function applyTaskStatus(plan: WorkPlan, taskId: string, status: TaskStatus): WorkPlan {
  return {
    ...plan,
    stages: plan.stages.map((stage) => ({
      ...stage,
      tasks: stage.tasks.map((task) => (task.task_id === taskId ? { ...task, status } : task)),
    })),
  };
}

export function WorkPlanPage() {
  const { currentUser, selectedStudentId, activeView } = useApp();
  const { token, studentId } = useAuth();
  const [plan, setPlan] = useState<WorkPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [modal, setModal] = useState<Modal>(null);

  const targetStudentId = selectedStudentId ?? studentId ?? "aluno_regular";
  const isAdvisor = currentUser?.role === "orientador" || currentUser?.role === "coordenacao" || !currentUser;
  const isStudent = currentUser?.role === "aluno" || !currentUser;
  // Aluno dono e orientador/coorientador podem mover (backend autoriza via
  // ownership "status"); coordenacao-pura e revertida pelo 403 do backend.
  const canMove = isAdvisor || isStudent;
  // Excluir task e edicao do kanban: so quem age como orientador. ADR-0002 trata o
  // toggle de visao como filtro de UX; coordenacao-pura fica presa em "coordenador"
  // (kanban read-only, issue #248) e nao ve o botao. O backend ainda garante ownership.
  const canEdit = activeView === "orientador";

  async function load() {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      setPlan(await getWorkPlan(targetStudentId, token ?? undefined));
    } catch (err) {
      setPlan(null);
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else {
        setError("Nao foi possivel carregar o plano de trabalho.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Aguarda o token resolver antes de chamar a API: sem ele o header
    // Authorization nao e enviado e o backend rejeita na validacao (422).
    if (!token) return;
    void load();
  }, [targetStudentId, token]);

  const tasks = useMemo(() => plan?.stages.flatMap((stage) => stage.tasks.map((task) => ({ ...task, stage }))) ?? [], [plan]);
  const concludedStages = plan?.stages.filter((stage) => stage.status === "concluido").length ?? 0;

  function changeStatus(taskId: string, status: TaskStatus) {
    if (!plan) return;
    const previous = plan;
    // Aplica a mudanca na hora (sem reload); reverte se o backend recusar.
    setPlan(applyTaskStatus(plan, taskId, status));
    setSaving(true);
    setError(null);
    void updateTaskStatus(taskId, status, token ?? undefined)
      .catch(() => {
        setPlan(previous);
        setError("Nao foi possivel mover a task. Tente novamente.");
      })
      .finally(() => setSaving(false));
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

  async function handleDeleteTask(task: WorkPlanTask) {
    setSaving(true);
    setError(null);
    try {
      await deleteTask(task.task_id, token ?? undefined);
      setModal(null);
      // Recarrega para a barra de progresso da etapa/plano refletir o recalculo.
      await load();
    } catch {
      setError("Nao foi possivel excluir a task. Tente novamente.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreatePlan(data: { titulo: string; dataInicio: string; dataFim: string; etapaNome: string }) {
    setSaving(true);
    try {
      const { plan_id } = await createWorkPlan(
        targetStudentId,
        { titulo: data.titulo, data_inicio: `${data.dataInicio}T00:00:00Z`, data_fim_prevista: `${data.dataFim}T00:00:00Z` },
        token ?? undefined,
      );
      if (data.etapaNome) {
        await createStage(
          plan_id,
          { nome: data.etapaNome, ordem: 1, data_inicio: `${data.dataInicio}T00:00:00Z`, data_fim: `${data.dataFim}T00:00:00Z` },
          token ?? undefined,
        );
      }
      setModal(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateStage(data: { nome: string; dataInicio: string; dataFim: string }) {
    if (!plan) return;
    setSaving(true);
    try {
      await createStage(
        plan.plan_id,
        { nome: data.nome, ordem: plan.stages.length + 1, data_inicio: `${data.dataInicio}T00:00:00Z`, data_fim: `${data.dataFim}T00:00:00Z` },
        token ?? undefined,
      );
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

  if (!plan) {
    if (notFound && isAdvisor) {
      return (
        <>
          <div className="rounded-lg p-6 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <Calendar className="mx-auto" size={28} style={{ color: "var(--muted-foreground)" }} />
            <p style={{ color: "var(--foreground)", fontWeight: 800, marginTop: 12 }}>Nenhum plano de trabalho ainda</p>
            <p style={{ color: "var(--muted-foreground)", fontSize: 13, marginTop: 6 }}>
              Este discente ainda nao possui um plano de trabalho. Crie o primeiro para comecar a acompanhar etapas e tarefas.
            </p>
            <button
              type="button"
              onClick={() => setModal({ kind: "plan" })}
              className="mt-4 inline-flex items-center gap-1.5 rounded-md px-3.5 py-2"
              style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 800 }}
            >
              <Plus size={15} /> Criar plano de trabalho
            </button>
          </div>
          {modal?.kind === "plan" && <PlanModal saving={saving} onClose={() => setModal(null)} onSave={handleCreatePlan} />}
        </>
      );
    }
    return (
      <div className="rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ color: "var(--foreground)", fontWeight: 700 }}>
          {error ?? (notFound ? "Nenhum plano de trabalho cadastrado para este discente." : "Plano nao encontrado.")}
        </p>
      </div>
    );
  }

  return (
    <DndProvider backend={HTML5Backend}>
    <div className="space-y-5">
      {error && (
        <div className="rounded-lg p-3" style={{ background: "#fef2f2", border: "1px solid #fecaca" }}>
          <p style={{ color: "#b91c1c", fontSize: 13, fontWeight: 700 }}>{error}</p>
        </div>
      )}
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

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {STATUS_COLUMNS.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            tasks={tasks.filter((item) => columnStatusOf(item.status) === column.id)}
            saving={saving}
            canMove={canMove}
            canAddProgress={isStudent}
            canDelete={canEdit}
            onDropTask={changeStatus}
            onProgress={(task) => setModal({ kind: "progress", task })}
            onDelete={(task) => setModal({ kind: "confirmDelete", task })}
          />
        ))}
      </section>

      <section className="rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="mb-3 flex items-center justify-between">
          <h2 style={{ fontSize: 14, fontWeight: 800, color: "var(--foreground)" }}>Etapas</h2>
          {canEdit && (
            <button
              type="button"
              onClick={() => setModal({ kind: "stage" })}
              className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5"
              style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)", fontSize: 12, fontWeight: 800 }}
            >
              <Plus size={14} /> Nova etapa
            </button>
          )}
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
                {canEdit && (
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
      {modal?.kind === "plan" && <PlanModal saving={saving} onClose={() => setModal(null)} onSave={handleCreatePlan} />}
      {modal?.kind === "stage" && <StageModal saving={saving} onClose={() => setModal(null)} onSave={handleCreateStage} />}
      {modal?.kind === "confirmDelete" && (
        <ConfirmDeleteModal task={modal.task} saving={saving} onClose={() => setModal(null)} onConfirm={() => handleDeleteTask(modal.task)} />
      )}
    </div>
    </DndProvider>
  );
}

function KanbanColumn({
  column,
  tasks,
  saving,
  canMove,
  canAddProgress,
  canDelete,
  onDropTask,
  onProgress,
  onDelete,
}: {
  column: { id: TaskStatus; label: string; icon: JSX.Element };
  tasks: (WorkPlanTask & { stage: WorkPlanStage })[];
  saving: boolean;
  canMove: boolean;
  canAddProgress: boolean;
  canDelete: boolean;
  onDropTask: (taskId: string, status: TaskStatus) => void;
  onProgress: (task: WorkPlanTask) => void;
  onDelete: (task: WorkPlanTask) => void;
}) {
  const [{ isOver, canDrop }, dropRef] = useDrop(
    () => ({
      accept: TASK_DND_TYPE,
      drop: (item: { taskId: string; fromStatus: TaskStatus }) => {
        if (columnStatusOf(item.fromStatus) !== column.id) onDropTask(item.taskId, column.id);
      },
      collect: (monitor) => ({ isOver: monitor.isOver(), canDrop: monitor.canDrop() }),
    }),
    [column.id, onDropTask],
  );
  const active = isOver && canDrop;

  return (
    <div
      ref={(node) => { dropRef(node); }}
      className="flex max-h-[560px] min-h-[420px] flex-col rounded-lg p-3"
      style={{
        background: "var(--card)",
        border: `1px solid ${active ? "#123C7A" : "var(--border)"}`,
        boxShadow: active ? "0 0 0 2px rgba(18,60,122,0.18)" : "none",
      }}
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2" style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)" }}>
          {column.icon} {column.label}
        </h2>
        <span style={{ fontSize: 12, color: "var(--muted-foreground)", fontWeight: 700 }}>{tasks.length}</span>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {tasks.map(({ stage, ...task }) => (
          <TaskCard
            key={task.task_id}
            task={task}
            stage={stage}
            draggable={canMove}
            disabled={saving}
            canAddProgress={canAddProgress}
            canDelete={canDelete}
            onProgress={() => onProgress(task)}
            onDelete={() => onDelete(task)}
          />
        ))}
      </div>
    </div>
  );
}

function TaskCard({
  task,
  stage,
  draggable,
  disabled,
  canAddProgress,
  canDelete,
  onProgress,
  onDelete,
}: {
  task: WorkPlanTask;
  stage: WorkPlanStage;
  draggable: boolean;
  disabled: boolean;
  canAddProgress: boolean;
  canDelete: boolean;
  onProgress: () => void;
  onDelete: () => void;
}) {
  const [{ isDragging }, dragRef] = useDrag(
    () => ({
      type: TASK_DND_TYPE,
      item: { taskId: task.task_id, fromStatus: task.status },
      canDrag: draggable && !disabled,
      collect: (monitor) => ({ isDragging: monitor.isDragging() }),
    }),
    [task.task_id, task.status, draggable, disabled],
  );
  const overdue = isTaskOverdue(task);

  return (
    <article
      ref={(node) => { dragRef(node); }}
      className="rounded-lg p-3"
      style={{
        background: "var(--background)",
        border: "1px solid var(--border)",
        cursor: draggable ? "grab" : "default",
        opacity: isDragging ? 0.5 : 1,
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p style={{ fontSize: 13, fontWeight: 800, color: "var(--foreground)", lineHeight: 1.35 }}>{task.titulo}</p>
          <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 4 }}>{stage.nome}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md px-2 py-1" style={{ fontSize: 10, fontWeight: 800, color: "#123C7A", background: "#eef3fc" }}>
            {PRIORITY_LABEL[task.prioridade]}
          </span>
          {canDelete && (
            <button
              type="button"
              disabled={disabled}
              onClick={onDelete}
              className="flex h-7 w-7 items-center justify-center rounded-md"
              style={{ background: "var(--card)", border: "1px solid var(--border)", color: "#dc2626" }}
              aria-label="Excluir task"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>
      {task.descricao && <p style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 8, lineHeight: 1.45 }}>{task.descricao}</p>}
      <div className="mt-3 flex items-center justify-between" style={{ fontSize: 11, color: "var(--muted-foreground)" }}>
        <span className="flex items-center gap-1.5"><Calendar size={12} /> {formatDate(task.prazo)}</span>
        <span>{Math.round(task.progresso_percentual)}%</span>
      </div>
      {overdue && (
        <span className="mt-2 inline-flex items-center gap-1 rounded-md px-2 py-1" style={{ fontSize: 10, fontWeight: 800, color: "#dc2626", background: "#fef2f2" }}>
          <AlertCircle size={11} /> Atrasado
        </span>
      )}
      <div className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ background: "var(--muted)" }}>
        <div className="h-full rounded-full" style={{ width: `${task.progresso_percentual}%`, background: overdue ? "#dc2626" : "#1F8A70" }} />
      </div>
      {task.ultima_atualizacao && (
        <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 8 }}>
          Ultimo update: {task.ultima_atualizacao.conteudo}
        </p>
      )}
      {canAddProgress && (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            disabled={disabled}
            onClick={onProgress}
            className="flex items-center gap-1.5 rounded-md px-2.5 py-2"
            style={{ background: "#123C7A", color: "#fff", fontSize: 12, fontWeight: 800 }}
          >
            <Send size={13} /> Progresso
          </button>
        </div>
      )}
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

function PlanModal({
  saving,
  onClose,
  onSave,
}: {
  saving: boolean;
  onClose: () => void;
  onSave: (data: { titulo: string; dataInicio: string; dataFim: string; etapaNome: string }) => void;
}) {
  const [titulo, setTitulo] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [etapaNome, setEtapaNome] = useState("");

  const disabled = saving || !titulo || !dataInicio || !dataFim;

  return (
    <ModalShell title="Criar plano de trabalho" onClose={onClose}>
      <div className="space-y-3">
        <Input label="Titulo do plano" value={titulo} onChange={setTitulo} />
        <Input label="Data de inicio" type="date" value={dataInicio} onChange={setDataInicio} />
        <Input label="Data fim prevista" type="date" value={dataFim} onChange={setDataFim} />
        <Input label="Primeira etapa (opcional)" value={etapaNome} onChange={setEtapaNome} />
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSave({ titulo, dataInicio, dataFim, etapaNome })}
          className="w-full rounded-md py-2.5"
          style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 800, opacity: disabled ? 0.6 : 1 }}
        >
          Criar plano
        </button>
      </div>
    </ModalShell>
  );
}

function StageModal({
  saving,
  onClose,
  onSave,
}: {
  saving: boolean;
  onClose: () => void;
  onSave: (data: { nome: string; dataInicio: string; dataFim: string }) => void;
}) {
  const [nome, setNome] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");

  const disabled = saving || !nome || !dataInicio || !dataFim;

  return (
    <ModalShell title="Nova etapa" onClose={onClose}>
      <div className="space-y-3">
        <Input label="Nome da etapa" value={nome} onChange={setNome} />
        <Input label="Data de inicio" type="date" value={dataInicio} onChange={setDataInicio} />
        <Input label="Data fim" type="date" value={dataFim} onChange={setDataFim} />
        <button
          type="button"
          disabled={disabled}
          onClick={() => onSave({ nome, dataInicio, dataFim })}
          className="w-full rounded-md py-2.5"
          style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 800, opacity: disabled ? 0.6 : 1 }}
        >
          Criar etapa
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

function ConfirmDeleteModal({
  task,
  saving,
  onClose,
  onConfirm,
}: {
  task: WorkPlanTask;
  saving: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <ModalShell title="Excluir task" onClose={onClose}>
      <div className="space-y-4">
        <p style={{ fontSize: 13, color: "var(--foreground)", lineHeight: 1.5 }}>
          Excluir <strong>{task.titulo}</strong>? Esta acao nao pode ser desfeita.
        </p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            disabled={saving}
            onClick={onClose}
            className="rounded-md px-3.5 py-2"
            style={{ background: "var(--muted)", color: "var(--foreground)", fontSize: 13, fontWeight: 800 }}
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={onConfirm}
            className="rounded-md px-3.5 py-2"
            style={{ background: "#dc2626", color: "#fff", fontSize: 13, fontWeight: 800, opacity: saving ? 0.6 : 1 }}
          >
            Excluir
          </button>
        </div>
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

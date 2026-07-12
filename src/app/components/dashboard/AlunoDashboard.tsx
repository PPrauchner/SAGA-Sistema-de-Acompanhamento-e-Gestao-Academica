import { useEffect, useState, useRef, type ReactNode } from "react";
import { useApp } from "../../context/AppContext";
import { useAlunoDashboard } from "@/hooks/useDashboard";
import { useNotifications, type Notification as ApiNotification } from "@/hooks/useNotifications";
import { useAuth } from "@/hooks/useAuth";
import { useEscapeClose } from "@/hooks/useEscapeClose";
import { getChecklist, type ChecklistResponse, type RequisitoStatus } from "@/api/checklistApi";
import { getWorkPlan, type WorkPlan, type StageStatus } from "@/api/workPlanApi";
import { ApiError } from "@/api/http";
import { ChartExportMenu } from "@/app/components/export/ChartExportMenu";
import {
  CheckCircle2, X, Calendar, ChevronRight, AlertTriangle,
  Bell, Clock,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

// ─── TYPES ────────────────────────────────────────────────────────────────────
type AcademicStatus = "regular" | "em-risco" | "qualificado" | "em-prorrogacao" | "fase-defesa";
interface ChecklistItem { id: string; label: string; icon: string; required: number; completed: number; unit: string; details: string; status: RequisitoStatus; }
interface WorkPhase { id: number; label: string; start: number; duration: number; color: string; progress: number; status: StageStatus; }
interface PendingTask { id: number; title: string; deadline: string; priority: "alta" | "media" | "baixa"; type: string; done: boolean; detail: string; }
interface Deadline { id: number; label: string; date: string; days: number; type: "urgente" | "importante" | "normal" | "critico"; icon: string; }
interface Notif { id: string; title: string; body: string; type: "alerta" | "orientacao" | "sucesso" | "info" | "lembrete"; time: string; read: boolean; }
type ModalData =
  | { type: "checklist"; item: ChecklistItem }
  | { type: "task"; task: PendingTask }
  | { type: "notif"; notif: Notif }
  | { type: "deadline"; deadline: Deadline }
  | null;

// ─── CONSTANTS ───────────────────────────────────────────────────────────────
const STATUS_CFG: Record<AcademicStatus, { label: string; color: string; bg: string; border: string; desc: string; emoji: string }> = {
  regular: { label: "Regular", color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)", border: "var(--tint-teal-border)", desc: "Todos os requisitos em dia. Continue assim!", emoji: "✓" },
  "em-risco": { label: "Em Risco", color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)", border: "var(--tint-gold-border)", desc: "Atenção: produções científicas abaixo do esperado para este período.", emoji: "⚠" },
  qualificado: { label: "Qualificado", color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)", border: "var(--tint-blue-border)", desc: "Qualificação aprovada. Foco total na pesquisa e escrita da tese.", emoji: "★" },
  "em-prorrogacao": { label: "Em Prorrogação", color: "var(--tint-orange-text)", bg: "var(--tint-orange-bg)", border: "var(--tint-orange-border)", desc: "Prazo regular encerrado. Prorrogação ativa até Junho/2027.", emoji: "↻" },
  "fase-defesa": { label: "Fase de Defesa", color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)", border: "var(--tint-violet-border)", desc: "Tese aprovada para defesa. Banca em fase de marcação.", emoji: "🎓" },
};
// CURRENT_STATUS agora vem dos dados da API (props.dashData.situacao_inferida)

// ─── DATA ────────────────────────────────────────────────────────────────────

// Converte a resposta real de GET /checklist/{student_id} nos itens consumidos pela
// ChecklistSection e pelo Modal. Um item "cumprido" quando completed >= required
// vale como concluído; a cor final, porém, é dirigida pelo status real (ver
// ChecklistSection) — incluindo "em_risco", que reaproveita o estado de atenção.
function buildChecklistItems(data: ChecklistResponse): ChecklistItem[] {
  const r = data.requisitos;
  const bool = (status: RequisitoStatus): number => (status === "cumprido" ? 1 : 0);
  return [
    { id: "creditos_minimos", label: "Créditos mínimos", icon: "📚", required: r.creditos_minimos.minimo, completed: r.creditos_minimos.obtidos, unit: "créditos", status: r.creditos_minimos.status, details: `${r.creditos_minimos.descricao}. Obtidos ${r.creditos_minimos.obtidos} de ${r.creditos_minimos.minimo} créditos.` },
    { id: "creditos_grupo_basico", label: "Créditos básicos", icon: "📗", required: r.creditos_grupo_basico.minimo, completed: r.creditos_grupo_basico.obtidos, unit: "créditos", status: r.creditos_grupo_basico.status, details: `${r.creditos_grupo_basico.descricao}. Obtidos ${r.creditos_grupo_basico.obtidos} de ${r.creditos_grupo_basico.minimo} créditos.` },
    { id: "creditos_grupo_especifico", label: "Créditos específicos", icon: "📘", required: r.creditos_grupo_especifico.minimo, completed: r.creditos_grupo_especifico.obtidos, unit: "créditos", status: r.creditos_grupo_especifico.status, details: `${r.creditos_grupo_especifico.descricao}. Obtidos ${r.creditos_grupo_especifico.obtidos} de ${r.creditos_grupo_especifico.minimo} créditos.` },
    { id: "creditos_grupo_tecnologico", label: "Créditos tecnológicos", icon: "🔧", required: r.creditos_grupo_tecnologico.maximo, completed: r.creditos_grupo_tecnologico.obtidos, unit: "créditos (máx)", status: r.creditos_grupo_tecnologico.status, details: `${r.creditos_grupo_tecnologico.descricao}. Obtidos ${r.creditos_grupo_tecnologico.obtidos} de no máximo ${r.creditos_grupo_tecnologico.maximo} créditos.` },
    { id: "proficiencia", label: "Proficiência", icon: "🌐", required: 1, completed: bool(r.proficiencia.status), unit: "exame", status: r.proficiencia.status, details: r.proficiencia.data_comprovacao ? `Proficiência comprovada em ${r.proficiencia.data_comprovacao}.` : "Proficiência em língua estrangeira ainda não comprovada." },
    { id: "qualificacao", label: "Qualificação", icon: "🎓", required: 1, completed: bool(r.qualificacao.status), unit: "exame", status: r.qualificacao.status, details: r.qualificacao.data_aprovacao ? `Qualificação aprovada em ${r.qualificacao.data_aprovacao}.` : "Exame de qualificação ainda não aprovado." },
    { id: "producao_validada", label: "Produção validada", icon: "📄", required: 1, completed: r.producao_validada.quantidade_aprovadas, unit: "produção", status: r.producao_validada.status, details: `${r.producao_validada.quantidade_aprovadas} produção(ões) bibliográfica(s) validada(s). Ao menos 1 é exigida para a defesa.` },
    { id: "plano_concluido", label: "Plano de trabalho", icon: "📋", required: r.plano_concluido.tasks_total_nao_defesa, completed: r.plano_concluido.tasks_concluidas, unit: "etapas", status: r.plano_concluido.status, details: `${r.plano_concluido.tasks_concluidas} de ${r.plano_concluido.tasks_total_nao_defesa} etapas (não-defesa) concluídas.` },
  ];
}

// Rótulo e cor de cada etapa canônica (stages.nome); etapas fora do enum caem no fallback.
const STAGE_META: Record<string, { label: string; color: string }> = {
  revisao_bibliografica: { label: "Revisão Bibliográfica", color: "#123C7A" },
  definicao_problema: { label: "Definição do Problema", color: "#1F8A70" },
  desenvolvimento: { label: "Desenvolvimento", color: "#8b5cf6" },
  experimentos: { label: "Experimentos", color: "#D4A017" },
  escrita: { label: "Escrita da Tese", color: "#f97316" },
  qualificacao: { label: "Qualificação", color: "#dc2626" },
  defesa: { label: "Defesa", color: "#0ea5e9" },
};
const STAGE_FALLBACK_COLOR = "#64748b";

// Rótulo e cor do indicador de status de uma etapa, refletindo o status real
// (inclui "atrasado", que o percentual sozinho não expressa).
function phaseStatusDisplay(status: StageStatus, progress: number): { label: string; color: string } {
  switch (status) {
    case "concluido": return { label: "✓ Concluído", color: "#1F8A70" };
    case "atrasado": return { label: "Atrasado", color: "#dc2626" };
    case "em_andamento": return { label: `${progress}%`, color: "#D4A017" };
    default: return { label: "Pendente", color: "var(--muted-foreground)" };
  }
}

// Meses inteiros de calendário entre duas datas (to - from). Negativo se to < from.
function monthSpan(from: Date, to: Date): number {
  return (to.getFullYear() - from.getFullYear()) * 12 + (to.getMonth() - from.getMonth());
}

// Total de meses do plano (início → fim previsto), base do eixo do Gantt. Mínimo 1.
function planTotalMonths(plan: WorkPlan): number {
  return Math.max(1, monthSpan(new Date(plan.data_inicio), new Date(plan.data_fim_prevista)) + 1);
}

// Mês atual (1-indexado) relativo ao início do plano — marcador "posição atual".
function planCurrentMonth(plan: WorkPlan): number {
  return Math.max(1, monthSpan(new Date(plan.data_inicio), new Date()) + 1);
}

// Deriva as barras do Gantt das etapas reais: posição/duração em meses a partir das
// datas ISO de cada etapa, relativas ao início do plano; cor e rótulo por nome canônico.
function phasesFromPlan(plan: WorkPlan): WorkPhase[] {
  const start = new Date(plan.data_inicio);
  return [...plan.stages]
    .sort((a, b) => a.ordem - b.ordem)
    .map((stage, index) => {
      const meta = STAGE_META[stage.nome];
      return {
        id: index,
        label: meta?.label ?? stage.nome,
        start: Math.max(1, monthSpan(start, new Date(stage.data_inicio)) + 1),
        duration: Math.max(1, monthSpan(new Date(stage.data_inicio), new Date(stage.data_fim)) + 1),
        color: meta?.color ?? STAGE_FALLBACK_COLOR,
        progress: Math.round(stage.progresso_percentual),
        status: stage.status,
      };
    });
}

// Achata as tasks de todas as etapas em cartões da lista de pendências, ordenados por prazo.
function tasksFromPlan(plan: WorkPlan): PendingTask[] {
  return plan.stages
    .flatMap((stage) => stage.tasks.map((task) => ({ task, stageNome: stage.nome })))
    .sort((a, b) => new Date(a.task.prazo).getTime() - new Date(b.task.prazo).getTime())
    .map(({ task, stageNome }, index) => ({
      id: index + 1,
      title: task.titulo,
      deadline: new Date(task.prazo).toLocaleDateString("pt-BR"),
      priority: task.prioridade,
      type: stageNome,
      done: task.status === "concluido",
      detail: task.descricao || "Sem descrição.",
    }));
}

const DEADLINES: Deadline[] = [
  { id: 1, label: "Relatório Anual", date: "15/06/2026", days: 13, type: "urgente", icon: "📋" },
  { id: 2, label: "Revisão c/ Orientadora", date: "20/06/2026", days: 18, type: "importante", icon: "👩‍🏫" },
  { id: 3, label: "Submissão SBES 2026", date: "30/06/2026", days: 28, type: "urgente", icon: "📄" },
  { id: 4, label: "Plano de Trabalho 2026/2", date: "01/07/2026", days: 29, type: "normal", icon: "📅" },
  { id: 5, label: "Inscrição Disciplina 2026/2", date: "05/07/2026", days: 33, type: "normal", icon: "📚" },
  { id: 6, label: "Prazo Máximo do Curso", date: "31/07/2026", days: 59, type: "critico", icon: "⏰" },
];

const GRAPH_DATA = [
  { sem: "1/22", atual: 10, esperado: 7.5 },
  { sem: "2/22", atual: 18, esperado: 15 },
  { sem: "1/23", atual: 28, esperado: 22.5 },
  { sem: "2/23", atual: 34, esperado: 30 },
  { sem: "1/24", atual: 42, esperado: 37.5 },
  { sem: "2/24", atual: 42, esperado: 45 },
  { sem: "1/25", atual: null, esperado: 52.5 },
  { sem: "2/25", atual: null, esperado: 60 },
];

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function Ring({ value, max, color, size = 52, stroke = 6 }: {
  value: number; max: number; color: string; size?: number; stroke?: number;
}) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - Math.min(value / max, 1));
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)", flexShrink: 0 }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
        strokeWidth={stroke} strokeDasharray={circ} strokeDashoffset={fill} strokeLinecap="round" />
    </svg>
  );
}

function SecHead({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>{title}</h3>
        {sub && <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{sub}</p>}
      </div>
      {right}
    </div>
  );
}

function PBadge({ p }: { p: "alta" | "media" | "baixa" }) {
  const c = p === "alta" ? { color: "#dc2626", bg: "#fef2f2", label: "Alta" }
    : p === "media" ? { color: "#D4A017", bg: "#fffbeb", label: "Média" }
    : { color: "#1F8A70", bg: "#f0fdf4", label: "Baixa" };
  return <span className="rounded-full px-2 py-0.5" style={{ fontSize: "10px", fontWeight: 700, color: c.color, background: c.bg }}>{c.label}</span>;
}

// ─── SWIPEABLE TASK CARD ─────────────────────────────────────────────────────

function SwipeableTaskCard({ task, onOpen, onDone }: { task: PendingTask; onOpen: (t: PendingTask) => void; onDone: (id: number) => void }) {
  const startX = useRef(0);
  const currentX = useRef(0);
  const cardRef = useRef<HTMLDivElement>(null);
  const [swiped, setSwiped] = useState<"left" | "right" | null>(null);
  const [offset, setOffset] = useState(0);

  const onTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
    currentX.current = e.touches[0].clientX;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    const dx = e.touches[0].clientX - startX.current;
    currentX.current = e.touches[0].clientX;
    if (Math.abs(dx) > 5) setOffset(Math.max(-80, Math.min(0, dx)));
  };

  const onTouchEnd = () => {
    if (offset < -50) {
      setSwiped("left");
      setOffset(-80);
    } else {
      setOffset(0);
    }
  };

  const priorityColor = task.priority === "alta" ? "#dc2626" : task.priority === "media" ? "#D4A017" : "#1F8A70";

  return (
    <div className="relative overflow-hidden rounded-xl" style={{ marginBottom: "8px" }}>
      {/* Swipe action background */}
      <div className="absolute inset-y-0 right-0 flex items-center justify-end px-4 rounded-xl"
        style={{ background: task.done ? "#1F8A70" : "#dc2626", minWidth: 80 }}>
        {task.done
          ? <CheckCircle2 size={20} color="#fff" />
          : <X size={20} color="#fff" />
        }
      </div>

      {/* Card */}
      <div
        ref={cardRef}
        style={{ transform: `translateX(${offset}px)`, transition: offset === 0 && swiped === null ? "transform 0.2s ease" : offset === -80 ? "transform 0.2s ease" : "none" }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onClick={() => { if (swiped === "left") { onDone(task.id); setSwiped(null); setOffset(0); } else { onOpen(task); } }}
      >
        <div
          className="flex items-start gap-3 p-3 rounded-xl"
          style={{
            background: task.done ? "var(--muted)" : task.priority === "alta" ? "#fff8f8" : "var(--muted)",
            border: `1px solid ${task.done ? "transparent" : task.priority === "alta" ? "#fecaca" : "transparent"}`,
            opacity: task.done ? 0.65 : 1,
            borderLeft: `3px solid ${priorityColor}`,
          }}
        >
          <div className="flex-shrink-0 mt-0.5">
            {task.done
              ? <CheckCircle2 size={16} style={{ color: "#1F8A70" }} />
              : <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: priorityColor }} />
            }
          </div>
          <div className="flex-1 min-w-0">
            <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--foreground)", lineHeight: 1.4, textDecoration: task.done ? "line-through" : "none" }}>
              {task.title}
            </p>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <PBadge p={task.priority} />
              <span style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                <Clock size={9} className="inline mr-0.5" />{task.deadline}
              </span>
            </div>
          </div>
          <ChevronRight size={14} style={{ color: "var(--muted-foreground)", flexShrink: 0, marginTop: 2 }} />
        </div>
      </div>
    </div>
  );
}

// ─── MODAL ────────────────────────────────────────────────────────────────────

function MHead({ title, onClose, bg, color }: { title: string; onClose: () => void; bg: string; color: string }) {
  return (
    <div className="flex items-center justify-between p-5 rounded-t-2xl" style={{ background: bg }}>
      <h3 style={{ fontSize: "16px", fontWeight: 700, color }}>{title}</h3>
      <button onClick={onClose} className="rounded-xl p-1.5" style={{ minWidth: 36, minHeight: 36, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <X size={18} style={{ color }} />
      </button>
    </div>
  );
}

function Modal({ data, onClose }: { data: ModalData; onClose: () => void }) {
  useEscapeClose(true, onClose);
  if (!data) return null;

  const renderBody = () => {
    if (data.type === "checklist") {
      const { item } = data;
      const pct = item.required > 0 ? Math.min(Math.round((item.completed / item.required) * 100), 100) : 0;
      const cfg = item.status === "cumprido" ? { color: "#1F8A70", bg: "#dcfce7", label: "Concluído" }
        : item.status === "em_risco" ? { color: "#D4A017", bg: "#fef9c3", label: "Em risco" }
        : { color: "#94a3b8", bg: "#f1f5f9", label: "Pendente" };
      return (
        <>
          <MHead title={item.label} onClose={onClose} bg={cfg.bg} color={cfg.color} />
          <div className="p-5 space-y-4">
            <div className="flex items-center gap-4">
              <span style={{ fontSize: "38px" }}>{item.icon}</span>
              <div>
                <span className="rounded-full px-2.5 py-1 inline-block" style={{ fontSize: "11px", fontWeight: 700, color: cfg.color, background: cfg.bg }}>{cfg.label}</span>
                <p style={{ fontSize: "16px", fontWeight: 800, color: "var(--foreground)", marginTop: "6px" }}>
                  {item.completed} / {item.required} {item.unit}
                </p>
              </div>
            </div>
            {item.required > 1 && (
              <div>
                <div className="flex justify-between mb-2">
                  <span style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Progresso</span>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: cfg.color }}>{pct}%</span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 10, background: "#e2e8f0" }}>
                  <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: cfg.color }} />
                </div>
              </div>
            )}
            <div className="rounded-xl p-4" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
              <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.7 }}>{item.details}</p>
            </div>
          </div>
        </>
      );
    }

    if (data.type === "task") {
      const { task } = data;
      const color = task.priority === "alta" ? "#dc2626" : task.priority === "media" ? "#D4A017" : "#1F8A70";
      const bg = task.priority === "alta" ? "#fef2f2" : task.priority === "media" ? "#fffbeb" : "#f0fdf4";
      return (
        <>
          <MHead title="Detalhe da Tarefa" onClose={onClose} bg={bg} color={color} />
          <div className="p-5 space-y-4">
            <div>
              <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)", lineHeight: 1.4 }}>{task.title}</p>
              <div className="flex items-center gap-2 mt-2">
                <PBadge p={task.priority} />
                {task.done && <span className="rounded-full px-2 py-0.5" style={{ fontSize: "10px", fontWeight: 700, color: "#1F8A70", background: "#dcfce7" }}>Concluída ✓</span>}
              </div>
            </div>
            <div className="flex items-center gap-2.5 rounded-xl p-3" style={{ background: "var(--muted)" }}>
              <Calendar size={14} style={{ color, flexShrink: 0 }} />
              <span style={{ fontSize: "13px", color: "var(--foreground)" }}>Prazo: <strong>{task.deadline}</strong></span>
            </div>
            <div className="rounded-xl p-4" style={{ background: "var(--muted)" }}>
              <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.7 }}>{task.detail}</p>
            </div>
          </div>
        </>
      );
    }

    if (data.type === "notif") {
      const { notif } = data;
      const tc: Record<string, { color: string; bg: string; label: string }> = {
        alerta: { color: "#dc2626", bg: "#fef2f2", label: "Alerta" },
        orientacao: { color: "#123C7A", bg: "#eef3fc", label: "Orientação" },
        sucesso: { color: "#1F8A70", bg: "#dcfce7", label: "Sucesso" },
        info: { color: "#0ea5e9", bg: "#f0f9ff", label: "Informação" },
        lembrete: { color: "#8b5cf6", bg: "#f5f3ff", label: "Lembrete" },
      };
      const cfg = tc[notif.type];
      return (
        <>
          <MHead title={cfg.label} onClose={onClose} bg={cfg.bg} color={cfg.color} />
          <div className="p-5 space-y-4">
            <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>{notif.title}</p>
            <div className="rounded-xl p-4" style={{ background: "var(--muted)" }}>
              <p style={{ fontSize: "13px", color: "var(--foreground)", lineHeight: 1.7 }}>{notif.body}</p>
            </div>
            <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{notif.time}</p>
          </div>
        </>
      );
    }

    if (data.type === "deadline") {
      const { deadline } = data;
      const tc = {
        urgente: { color: "#dc2626", bg: "#fef2f2", label: "Urgente" },
        importante: { color: "#D4A017", bg: "#fffbeb", label: "Importante" },
        normal: { color: "#123C7A", bg: "#eef3fc", label: "Normal" },
        critico: { color: "#7c3aed", bg: "#f5f3ff", label: "Crítico" },
      }[deadline.type];
      return (
        <>
          <MHead title="Prazo" onClose={onClose} bg={tc.bg} color={tc.color} />
          <div className="p-5 space-y-4">
            <div className="flex items-center gap-4">
              <span style={{ fontSize: "38px" }}>{deadline.icon}</span>
              <p style={{ fontSize: "16px", fontWeight: 700, color: "var(--foreground)" }}>{deadline.label}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl p-3" style={{ background: "var(--muted)" }}>
                <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginBottom: "3px" }}>Data do Prazo</p>
                <p style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)" }}>{deadline.date}</p>
              </div>
              <div className="rounded-xl p-3" style={{ background: tc.bg }}>
                <p style={{ fontSize: "11px", color: tc.color, marginBottom: "3px" }}>Dias Restantes</p>
                <p style={{ fontSize: "22px", fontWeight: 800, color: tc.color }}>{deadline.days}d</p>
              </div>
            </div>
          </div>
        </>
      );
    }
    return null;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4"
      style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
      onClick={onClose}>
      {/* Mobile: sheet from bottom. Desktop: centered dialog */}
      <div
        className="w-full md:max-w-md md:rounded-2xl rounded-t-2xl overflow-y-auto"
        style={{ background: "var(--card)", boxShadow: "0 -8px 40px rgba(0,0,0,0.2)", maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Mobile drag handle */}
        <div className="md:hidden flex justify-center pt-3 pb-1">
          <div style={{ width: 36, height: 4, borderRadius: 2, background: "var(--border)" }} />
        </div>
        {renderBody()}
      </div>
    </div>
  );
}

// ─── MOBILE KPI CAROUSEL ──────────────────────────────────────────────────────

interface KpiProps {
  situacao: AcademicStatus;
  creditos: number;
  minCreditos: number;
  progressoPct: number;
  producoes: number;
  diasRestantes: number;
}

function MobileKpiCarousel({ situacao, creditos, minCreditos, progressoPct, producoes, diasRestantes }: KpiProps) {
  const s = STATUS_CFG[situacao];
  const creditPct = Math.min(100, Math.round((creditos / Math.max(1, minCreditos)) * 100));
  const mesesRestantes = Math.max(0, Math.round(diasRestantes / 30));

  const cards = [
    {
      title: "Situação Acadêmica",
      content: (
        <div className="flex items-center gap-3 mt-2">
          <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: s.color, fontSize: "18px", color: "#fff" }}>{s.emoji}</div>
          <div>
            <p style={{ fontSize: "17px", fontWeight: 800, color: s.color }}>{s.label}</p>
            <p style={{ fontSize: "11px", color: s.color, opacity: 0.75 }}>Toque para detalhes</p>
          </div>
        </div>
      ),
      accent: s.color,
      bg: s.bg,
      border: s.border,
    },
    {
      title: "Créditos",
      content: (
        <div className="flex items-center gap-3 mt-2">
          <div className="relative" style={{ width: 52, height: 52, flexShrink: 0 }}>
            <Ring value={creditos} max={minCreditos} color="#123C7A" size={52} stroke={6} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#123C7A" }}>{creditPct}%</span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: "26px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }}>{creditos}/{minCreditos}</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>créditos obtidos</p>
          </div>
        </div>
      ),
      accent: "#123C7A",
      bg: "var(--card)",
      border: "var(--border)",
    },
    {
      title: "Produções",
      content: (
        <div className="flex items-center gap-3 mt-2">
          <div className="relative" style={{ width: 52, height: 52, flexShrink: 0 }}>
            <Ring value={producoes} max={3} color="#D4A017" size={52} stroke={6} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#D4A017" }}>{Math.round((producoes / 3) * 100)}%</span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: "26px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }}>{producoes}/3</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>artigos Qualis</p>
          </div>
        </div>
      ),
      accent: "#D4A017",
      bg: "var(--card)",
      border: "var(--border)",
    },
    {
      title: "Prazo Restante",
      content: (
        <div className="mt-2">
          <p style={{ fontSize: "34px", fontWeight: 800, color: "#8b5cf6", lineHeight: 1 }}>{mesesRestantes}</p>
          <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: 2 }}>meses restantes</p>
          <div className="rounded-full overflow-hidden mt-3" style={{ height: 6, background: "#e2e8f0" }}>
            <div style={{ height: "100%", width: `${progressoPct}%`, background: "#8b5cf6", borderRadius: 999 }} />
          </div>
          <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: 3 }}>Progresso do plano: {progressoPct}%</p>
        </div>
      ),
      accent: "#8b5cf6",
      bg: "var(--card)",
      border: "var(--border)",
    },
  ];

  const [idx, setIdx] = useState(0);
  const touchStartX = useRef(0);

  const onTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX; };
  const onTouchEnd = (e: React.TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    if (dx < -40 && idx < cards.length - 1) setIdx(i => i + 1);
    if (dx > 40 && idx > 0) setIdx(i => i - 1);
  };

  const card = cards[idx];

  return (
    <div className="md:hidden">
      <div
        className="rounded-2xl p-4 select-none"
        style={{ background: card.bg, border: `2px solid ${card.border}`, minHeight: 130 }}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        <div className="flex items-center justify-between mb-1">
          <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            {card.title}
          </p>
          <div className="flex items-center gap-1">
            {cards.map((_, i) => (
              <button key={i} onClick={() => setIdx(i)}
                style={{ width: i === idx ? 16 : 6, height: 6, borderRadius: 3, background: i === idx ? card.accent : "#e2e8f0", transition: "all 0.2s" }}
              />
            ))}
          </div>
        </div>
        {card.content}
      </div>
      <p style={{ fontSize: "10px", color: "var(--muted-foreground)", textAlign: "center", marginTop: 6 }}>
        Deslize para ver mais indicadores
      </p>
    </div>
  );
}

// ─── DESKTOP KPI GRID ─────────────────────────────────────────────────────────

function DesktopKpiCards({ situacao, creditos, minCreditos, progressoPct, producoes, diasRestantes }: KpiProps) {
  const s = STATUS_CFG[situacao];
  const creditPct = Math.min(100, Math.round((creditos / Math.max(1, minCreditos)) * 100));
  const mesesRestantes = Math.max(0, Math.round(diasRestantes / 30));

  return (
    <div className="hidden md:grid grid-cols-2 lg:grid-cols-5 gap-3">
      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: `2px solid ${s.border}`, gridColumn: "1 / -1" }}>
        <div className="flex flex-wrap items-start gap-4">
          <div>
            <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "6px" }}>Situação Acadêmica</p>
            <div className="inline-flex items-center gap-2 rounded-xl px-3 py-1.5" style={{ background: s.bg }}>
              <span style={{ fontSize: "16px" }}>{s.emoji}</span>
              <span style={{ fontSize: "15px", fontWeight: 800, color: s.color }}>{s.label}</span>
            </div>
          </div>
          <p style={{ fontSize: "12px", color: s.color, lineHeight: 1.55, maxWidth: 380, paddingTop: "2px" }}>{s.desc}</p>
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>Créditos Obtidos</p>
        <div className="flex items-center gap-3">
          <div className="relative" style={{ width: 52, height: 52, flexShrink: 0 }}>
            <Ring value={creditos} max={minCreditos} color="#123C7A" size={52} stroke={6} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#123C7A" }}>{creditPct}%</span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: "24px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }}>{creditos}</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>de {minCreditos} créditos</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>Créditos Necessários</p>
        <p style={{ fontSize: "32px", fontWeight: 800, color: "#dc2626", lineHeight: 1 }}>{Math.max(0, minCreditos - creditos)}</p>
        <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "3px" }}>para concluir</p>
        <div className="rounded-full overflow-hidden mt-3" style={{ height: 5, background: "#e2e8f0" }}>
          <div style={{ height: "100%", width: `${creditPct}%`, background: "linear-gradient(90deg,#123C7A,#1a4f9a)", borderRadius: 999 }} />
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>Produções Validadas</p>
        <div className="flex items-center gap-3">
          <div className="relative" style={{ width: 52, height: 52, flexShrink: 0 }}>
            <Ring value={producoes} max={3} color="#D4A017" size={52} stroke={6} />
            <div className="absolute inset-0 flex items-center justify-center">
              <span style={{ fontSize: "10px", fontWeight: 800, color: "#D4A017" }}>{Math.round((producoes / 3) * 100)}%</span>
            </div>
          </div>
          <div>
            <p style={{ fontSize: "24px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }}>{producoes}/3</p>
            <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>artigos Qualis</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: "10px" }}>Prazo Restante</p>
        <p style={{ fontSize: "32px", fontWeight: 800, color: "#8b5cf6", lineHeight: 1 }}>{mesesRestantes}</p>
        <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "3px" }}>meses restantes</p>
        <div className="rounded-full overflow-hidden mt-3" style={{ height: 5, background: "#e2e8f0" }}>
          <div style={{ height: "100%", width: `${progressoPct}%`, background: "#8b5cf6", borderRadius: 999 }} />
        </div>
        <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "3px" }}>Progresso do plano: {progressoPct}%</p>
      </div>
    </div>
  );
}

// ─── ACADEMIC STATUS CARD ─────────────────────────────────────────────────────

function AcademicStatusCard({ situacao, conflito }: { situacao: AcademicStatus; conflito: boolean }) {
  const cfg = STATUS_CFG[situacao];
  const factors = [
    { label: "Créditos integralizados (70%)", ok: true },
    { label: "Proficiência em língua estrangeira", ok: true },
    { label: "Qualificação aprovada", ok: true },
    { label: "Produções científicas ⚠ abaixo da meta", ok: situacao !== "em-risco" },
    { label: conflito ? "Sistema constata conflito com registro oficial" : "Situação alinhada com registro oficial", ok: !conflito },
  ];

  return (
    <div className="rounded-2xl p-4 md:p-5 h-full" style={{ background: "var(--card)", border: `2px solid ${cfg.border}` }}>
      <SecHead title="Situação Acadêmica" sub="Avaliação automática pelo SAGA" />

      <div className="rounded-2xl p-4 mb-4" style={{ background: cfg.bg }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: cfg.color, fontSize: "18px", color: "#fff" }}>{cfg.emoji}</div>
          <div>
            <p style={{ fontSize: "17px", fontWeight: 800, color: cfg.color }}>{cfg.label}</p>
            <p style={{ fontSize: "11px", color: cfg.color, opacity: 0.75 }}>Situação atual</p>
          </div>
        </div>
        <p style={{ fontSize: "13px", color: cfg.color, lineHeight: 1.6 }}>{cfg.desc}</p>
      </div>

      <p style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "10px" }}>
        Fatores Avaliados
      </p>
      <div className="space-y-2">
        {factors.map((f, i) => (
          <div key={i} className="flex items-start gap-2.5 rounded-lg p-2.5"
            style={{ background: f.ok ? "transparent" : "var(--tint-danger-bg)", border: f.ok ? "none" : "1px solid var(--tint-danger-border)", minHeight: "40px" }}>
            <div className="rounded-full flex-shrink-0 mt-1" style={{ width: 7, height: 7, background: f.ok ? "var(--status-active)" : "var(--destructive)" }} />
            <span style={{ fontSize: "12px", color: f.ok ? "var(--foreground)" : "var(--tint-danger-text)", fontWeight: f.ok ? 400 : 600, lineHeight: 1.4 }}>{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── CHECKLIST SECTION ────────────────────────────────────────────────────────

function ChecklistSection({ items, loading, error, onOpen }: { items: ChecklistItem[]; loading: boolean; error: string | null; onOpen: (item: ChecklistItem) => void }) {
  const done = items.filter(i => i.status === "cumprido").length;

  if (loading) {
    return (
      <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <SecHead title="Checklist de Conclusão" sub="Requisitos para obtenção do título" />
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando checklist…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <SecHead title="Checklist de Conclusão" sub="Requisitos para obtenção do título" />
        <p style={{ fontSize: "12px", color: "var(--tint-danger-text)" }}>{error}</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Checklist de Conclusão"
        sub="Requisitos para obtenção do título"
        right={
          <span className="rounded-full px-2 py-0.5" style={{ fontSize: "11px", fontWeight: 700, color: "var(--tint-blue-text)", background: "var(--tint-blue-bg)" }}>
            {done}/{items.length}
          </span>
        }
      />
      <div className="space-y-2">
        {items.map((item) => {
          const isDone = item.status === "cumprido";
          const isPartial = item.status === "em_risco";
          const pct = item.required > 0 ? Math.min(Math.round((item.completed / item.required) * 100), 100) : 0;
          const statusColor = isDone ? "var(--tint-teal-text)" : isPartial ? "var(--tint-gold-text)" : "var(--muted-foreground)";
          const statusBg = isDone ? "var(--tint-teal-bg)" : isPartial ? "var(--tint-gold-bg)" : "var(--muted)";
          const statusBorder = isDone ? "var(--tint-teal-border)" : isPartial ? "var(--tint-gold-border)" : "transparent";

          return (
            <button key={item.id} onClick={() => onOpen(item)}
              className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all"
              style={{ background: statusBg, border: `1px solid ${statusBorder}`, minHeight: "52px" }}>
              <div className="flex-shrink-0">
                {isDone ? (
                  <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: "#1F8A70" }}>
                    <CheckCircle2 size={15} style={{ color: "#fff" }} />
                  </div>
                ) : isPartial ? (
                  <div className="relative" style={{ width: 28, height: 28 }}>
                    <Ring value={item.completed} max={item.required} color="#D4A017" size={28} stroke={4} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span style={{ fontSize: "7px", fontWeight: 800, color: "#D4A017" }}>{pct}%</span>
                    </div>
                  </div>
                ) : (
                  <div className="w-7 h-7 rounded-full border-2 flex items-center justify-center"
                    style={{ borderColor: "#cbd5e1", background: "var(--background)" }}>
                    <div className="w-2 h-2 rounded-full" style={{ background: "#e2e8f0" }} />
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span style={{ fontSize: "13px" }}>{item.icon}</span>
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{item.label}</span>
                </div>
                <span style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                  {item.completed}/{item.required} {item.unit}
                </span>
              </div>
              <ChevronRight size={14} style={{ color: statusColor, flexShrink: 0 }} />
            </button>
          );
        })}
      </div>
      <div className="mt-4 rounded-xl p-3" style={{ background: "#eef3fc", border: "1px solid #c7d9f5" }}>
        <div className="flex justify-between mb-1.5">
          <span style={{ fontSize: "12px", fontWeight: 600, color: "#123C7A" }}>Progresso Geral</span>
          <span style={{ fontSize: "12px", fontWeight: 800, color: "#123C7A" }}>{done}/{items.length}</span>
        </div>
        <div className="rounded-full overflow-hidden" style={{ height: 6, background: "#c7d9f5" }}>
          <div style={{ height: "100%", width: `${items.length > 0 ? (done / items.length) * 100 : 0}%`, background: "#123C7A", borderRadius: 999 }} />
        </div>
      </div>
    </div>
  );
}

// ─── PROGRESS GRAPH ───────────────────────────────────────────────────────────

function ProgressGraph() {
  const chartRef = useRef<HTMLDivElement>(null);
  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Evolução dos Créditos"
        sub="Créditos acumulados vs. meta por semestre"
        right={
          <div className="flex flex-wrap items-center gap-2 justify-end">
            <div className="flex items-center gap-1.5 rounded-lg px-2.5 py-1" style={{ background: "#fef9c3", border: "1px solid #fde68a" }}>
              <AlertTriangle size={12} style={{ color: "#D4A017" }} />
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#D4A017" }}>Plateou no Sem 2/24</span>
            </div>
            <ChartExportMenu
              title="Evolucao dos Creditos"
              fileName="evolucao-creditos"
              chartRef={chartRef}
              data={GRAPH_DATA}
              columns={[
                { key: "sem", label: "Semestre" },
                { key: "atual", label: "Creditos obtidos" },
                { key: "esperado", label: "Meta esperada" },
              ]}
            />
          </div>
        }
      />
      <div ref={chartRef}>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={GRAPH_DATA} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="gradEsp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#123C7A" stopOpacity={0.12} key="aluno-stop-esp-5" />
              <stop offset="95%" stopColor="#123C7A" stopOpacity={0} key="aluno-stop-esp-95" />
            </linearGradient>
            <linearGradient id="gradAt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1F8A70" stopOpacity={0.2} key="aluno-stop-at-5" />
              <stop offset="95%" stopColor="#1F8A70" stopOpacity={0} key="aluno-stop-at-95" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="sem" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <YAxis domain={[0, 65]} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} width={28} />
          <Tooltip
            contentStyle={{ borderRadius: 10, fontSize: 12, border: "1px solid var(--border)", background: "var(--card)" }}
            formatter={(val, name) => val != null ? [`${val} cr`, name === "atual" ? "Obtidos" : "Meta"] : ["—", String(name)]}
          />
          <ReferenceLine y={60} stroke="#dc2626" strokeDasharray="4 4" key="aluno-ref-60" />
          <Area type="monotone" dataKey="esperado" stroke="#123C7A" fill="url(#gradEsp)" strokeWidth={2} strokeDasharray="5 5" dot={false} connectNulls isAnimationActive={false} />
          <Area type="monotone" dataKey="atual" stroke="#1F8A70" fill="url(#gradAt)" strokeWidth={2.5} connectNulls={false} isAnimationActive={false}
            dot={(props: { cx?: number; cy?: number; index?: number; payload?: { atual: number | null } }) => {
              const { cx = 0, cy = 0, index = 0, payload } = props;
              if (!payload || payload.atual === null) return <g key={`dot-null-${index}`} />;
              return <circle key={`dot-${index}`} cx={cx} cy={cy} r={3} fill="#1F8A70" />;
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap items-center gap-3 mt-3 justify-center">
        {[
          { color: "#1F8A70", label: "Créditos Obtidos" },
          { color: "#123C7A", label: "Meta Esperada", dash: true },
          { color: "#dc2626", label: "Meta Final (60 cr)", dash: true },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div style={{ width: 16, height: 2, background: l.color, borderRadius: 1 }} />
            <span style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── TASKS SECTION ────────────────────────────────────────────────────────────

function TasksSection({ tasks, loading, error, onOpen, onDone }: { tasks: PendingTask[]; loading: boolean; error: string | null; onOpen: (t: PendingTask) => void; onDone: (id: number) => void }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? tasks : tasks.slice(0, 4);
  const openCount = tasks.filter(t => !t.done).length;
  const urgentCount = tasks.filter(t => !t.done && t.priority === "alta").length;

  if (loading || error || tasks.length === 0) {
    return (
      <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <SecHead title="Tarefas Pendentes" sub="Tarefas do plano de trabalho" />
        <p style={{ fontSize: "12px", color: error ? "var(--tint-danger-text)" : "var(--muted-foreground)" }}>
          {loading ? "Carregando tarefas…" : error ?? "Nenhuma tarefa no plano de trabalho."}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Tarefas Pendentes"
        sub={`${openCount} tarefas em aberto`}
        right={urgentCount > 0 && (
          <span className="rounded-full px-2 py-0.5" style={{ fontSize: "11px", fontWeight: 700, color: "var(--tint-danger-text)", background: "var(--tint-danger-bg)" }}>
            {urgentCount} urgentes
          </span>
        )}
      />
      {/* Mobile: swipeable cards. Desktop: regular buttons */}
      <div className="md:hidden">
        {shown.map((task) => (
          <SwipeableTaskCard key={task.id} task={task} onOpen={onOpen} onDone={onDone} />
        ))}
        {tasks.length > 1 && (
          <p style={{ fontSize: "10px", color: "var(--muted-foreground)", textAlign: "center", marginTop: 6 }}>
            ← Deslize para ação rápida
          </p>
        )}
      </div>
      <div className="hidden md:block space-y-2">
        {shown.map((task) => (
          <button key={task.id} onClick={() => onOpen(task)}
            className="w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all hover:shadow-sm"
            style={{
              background: task.done ? "var(--muted)" : task.priority === "alta" ? "var(--tint-danger-bg)" : "var(--muted)",
              border: `1px solid ${task.done ? "transparent" : task.priority === "alta" ? "var(--tint-danger-border)" : "transparent"}`,
              opacity: task.done ? 0.65 : 1,
            }}>
            <div className="flex-shrink-0 mt-0.5">
              {task.done
                ? <CheckCircle2 size={16} style={{ color: "var(--status-active)" }} />
                : <div className="w-4 h-4 rounded-full border-2" style={{ borderColor: task.priority === "alta" ? "var(--destructive)" : "var(--muted-foreground)" }} />
              }
            </div>
            <div className="flex-1 min-w-0">
              <p style={{ fontSize: "13px", fontWeight: 500, color: "var(--foreground)", lineHeight: 1.4, textDecoration: task.done ? "line-through" : "none" }}>
                {task.title}
              </p>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <PBadge p={task.priority} />
                <span style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                  <Clock size={9} className="inline mr-0.5" />{task.deadline}
                </span>
              </div>
            </div>
            <ChevronRight size={14} style={{ color: "var(--muted-foreground)", flexShrink: 0, marginTop: 2 }} />
          </button>
        ))}
      </div>

      {tasks.length > 4 && (
        <button onClick={() => setShowAll(!showAll)}
          className="w-full mt-3 py-2.5 rounded-xl transition-colors"
          style={{ background: "var(--tint-blue-bg)", color: "var(--tint-blue-text)", fontSize: "12px", fontWeight: 600 }}>
          {showAll ? "Mostrar menos" : `Ver mais ${tasks.length - 4} tarefas`}
        </button>
      )}
    </div>
  );
}

// ─── DEADLINES SECTION ────────────────────────────────────────────────────────

function DeadlinesSection({ onOpen }: { onOpen: (d: Deadline) => void }) {
  const typeColor: Record<string, string> = {
    urgente: "var(--tint-danger-text)", importante: "var(--tint-gold-text)", normal: "var(--tint-blue-text)", critico: "var(--tint-violet-text)",
  };
  const typeBg: Record<string, string> = {
    urgente: "var(--tint-danger-bg)", importante: "var(--tint-gold-bg)", normal: "var(--tint-blue-bg)", critico: "var(--tint-violet-bg)",
  };

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead title="Próximos Prazos" sub="Ordenados por proximidade" />
      <div className="space-y-2">
        {DEADLINES.map((d) => {
          const color = typeColor[d.type];
          const bg = typeBg[d.type];
          return (
            <button key={d.id} onClick={() => onOpen(d)}
              className="w-full flex items-center gap-3 p-3 rounded-xl text-left transition-all"
              style={{ background: d.days <= 20 ? bg : "var(--muted)", border: `1px solid ${d.days <= 20 ? "var(--border)" : "transparent"}`, minHeight: "52px" }}>
              <span style={{ fontSize: "18px", flexShrink: 0 }}>{d.icon}</span>
              <div className="flex-1 min-w-0">
                <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{d.label}</p>
                <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{d.date}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <p style={{ fontSize: "15px", fontWeight: 800, color }}>{d.days}d</p>
                <span className="rounded-full px-1.5 py-0.5" style={{ fontSize: "9px", fontWeight: 700, color, background: bg }}>
                  {d.type}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── NOTIFICATIONS SECTION ────────────────────────────────────────────────────

// Mapeia o tipo da notificação (A05) para a categoria visual do painel. Default: "info".
const NOTIF_TIPO_MAP: Record<string, Notif["type"]> = {
  prazo_critico: "alerta",
  atividade_validada: "sucesso",
  prorrogacao_aprovada: "sucesso",
  atividade_submetida: "info",
  progresso_task: "orientacao",
  transferencia_orientador: "orientacao",
  transferencia_coordenacao: "info",
};

// Adapta a notificação real (useNotifications) ao formato Notif consumido pela UI e pelo modal.
function toNotif(n: ApiNotification): Notif {
  return {
    id: n.id,
    title: n.titulo,
    body: n.mensagem,
    type: NOTIF_TIPO_MAP[n.tipo] ?? "info",
    time: n.timestamp ? n.timestamp.toLocaleDateString("pt-BR") : "",
    // useNotifications retorna apenas não-lidas (lida == false).
    read: n.lida,
  };
}

function NotificationsSection({ onOpen }: { onOpen: (n: Notif) => void }) {
  const { notifications, loading } = useNotifications();
  const items = notifications.map(toNotif);
  const unread = items.filter(n => !n.read).length;
  const typeMap: Record<string, { color: string; bg: string; icon: string }> = {
    alerta: { color: "#dc2626", bg: "#fef2f2", icon: "⚠️" },
    orientacao: { color: "#123C7A", bg: "#eef3fc", icon: "👩‍🏫" },
    sucesso: { color: "#1F8A70", bg: "#dcfce7", icon: "✅" },
    info: { color: "#0ea5e9", bg: "#f0f9ff", icon: "ℹ️" },
    lembrete: { color: "#8b5cf6", bg: "#f5f3ff", icon: "🔔" },
  };

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Notificações"
        sub={loading ? "Carregando…" : `${unread} não lidas`}
        right={unread > 0 && (
          <div className="flex items-center gap-1 rounded-full px-2 py-0.5" style={{ background: "#fef2f2" }}>
            <Bell size={11} style={{ color: "#dc2626" }} />
            <span style={{ fontSize: "11px", fontWeight: 700, color: "#dc2626" }}>{unread}</span>
          </div>
        )}
      />
      {loading ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando notificações…</p>
      ) : items.length === 0 ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Sem notificações.</p>
      ) : (
        <div className="space-y-2">
          {items.map((n) => {
            const tm = typeMap[n.type];
            return (
              <button key={n.id} onClick={() => onOpen(n)}
                className="w-full flex items-start gap-3 p-3 rounded-xl text-left transition-all"
                style={{
                  background: n.read ? "var(--muted)" : `${tm.color}08`,
                  border: `1px solid ${n.read ? "transparent" : `${tm.color}25`}`,
                  minHeight: "52px",
                }}>
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-sm"
                  style={{ background: n.read ? "var(--muted)" : tm.bg }}>
                  {tm.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-1.5">
                    <p style={{ fontSize: "12px", fontWeight: n.read ? 400 : 700, color: "var(--foreground)", lineHeight: 1.35, flex: 1 }}>
                      {n.title}
                    </p>
                    {!n.read && <div className="w-2 h-2 rounded-full flex-shrink-0 mt-1" style={{ background: tm.color }} />}
                  </div>
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "2px" }}>{n.time}</p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── GANTT (desktop only) ─────────────────────────────────────────────────────

function GanttTimeline({ phases, totalMonths, currentMonth, loading, error }: { phases: WorkPhase[]; totalMonths: number; currentMonth: number; loading: boolean; error: string | null }) {
  if (loading || error || phases.length === 0) {
    return (
      <div className="hidden md:block rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <SecHead title="Cronograma do Plano de Trabalho" sub="Etapas do plano de trabalho" />
        <p style={{ fontSize: "12px", color: error ? "var(--tint-danger-text)" : "var(--muted-foreground)" }}>
          {loading ? "Carregando cronograma…" : error ?? "Nenhuma etapa cadastrada no plano de trabalho."}
        </p>
      </div>
    );
  }
  const months = Array.from({ length: totalMonths }, (_, i) => i + 1);
  return (
    <div className="hidden md:block rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Cronograma do Plano de Trabalho"
        sub={`Plano de pesquisa de ${totalMonths} meses · Posição atual: Mês ${currentMonth}`}
      />
      <div className="overflow-x-auto">
        <div style={{ minWidth: 560 }}>
          <div className="flex mb-1.5" style={{ paddingLeft: 150 }}>
            {months.map((m) => (
              <div key={m} className="flex-1 text-center" style={{ minWidth: 0 }}>
                {(m === 1 || m % 4 === 0) && (
                  <span style={{ fontSize: "9px", fontWeight: m === currentMonth ? 800 : 400, color: m === currentMonth ? "#123C7A" : "var(--muted-foreground)" }}>
                    M{m}
                  </span>
                )}
              </div>
            ))}
          </div>
          {phases.map((phase) => (
            <div key={phase.id} className="flex items-center mb-2.5">
              <div style={{ width: 150, flexShrink: 0, paddingRight: 10 }}>
                <div className="flex items-center gap-1.5">
                  <div className="rounded-sm flex-shrink-0" style={{ width: 9, height: 9, background: phase.color }} />
                  <p style={{ fontSize: "11px", color: "var(--foreground)", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 130 }}>
                    {phase.label}
                  </p>
                </div>
                <div className="flex items-center gap-1 mt-0.5" style={{ paddingLeft: 14 }}>
                  <span style={{ fontSize: "9px", color: "var(--muted-foreground)" }}>M{phase.start}–M{phase.start + phase.duration - 1}</span>
                  <span style={{ fontSize: "8px", color: phaseStatusDisplay(phase.status, phase.progress).color, fontWeight: 700 }}>
                    {phaseStatusDisplay(phase.status, phase.progress).label}
                  </span>
                </div>
              </div>
              <div className="flex-1 relative" style={{ height: 22 }}>
                <div className="absolute inset-0 flex pointer-events-none">
                  {months.map((m) => (
                    <div key={m} className="flex-1 h-full" style={{ borderRight: `1px solid ${m === currentMonth ? "#123C7A30" : "var(--border)"}` }} />
                  ))}
                </div>
                <div className="absolute rounded-md overflow-hidden"
                  style={{ left: `${((phase.start - 1) / totalMonths) * 100}%`, width: `${(phase.duration / totalMonths) * 100}%`, top: 3, height: 16, background: `${phase.color}20`, border: `1.5px solid ${phase.color}55` }}>
                  <div style={{ height: "100%", width: `${phase.progress}%`, background: phase.color, opacity: 0.85 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── MOBILE PHASES CARD ───────────────────────────────────────────────────────

function MobilePhasesCard({ phases, totalMonths, currentMonth, loading, error }: { phases: WorkPhase[]; totalMonths: number; currentMonth: number; loading: boolean; error: string | null }) {
  if (loading || error || phases.length === 0) {
    return (
      <div className="md:hidden rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <SecHead title="Plano de Trabalho" sub="Etapas do plano de trabalho" />
        <p style={{ fontSize: "12px", color: error ? "var(--tint-danger-text)" : "var(--muted-foreground)" }}>
          {loading ? "Carregando plano…" : error ?? "Nenhuma etapa cadastrada no plano de trabalho."}
        </p>
      </div>
    );
  }
  return (
    <div className="md:hidden rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead title="Plano de Trabalho" sub={`Mês ${currentMonth} de ${totalMonths}`} />
      <div className="space-y-2.5">
        {phases.map((phase) => (
          <div key={phase.id}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5">
                <div className="rounded-sm flex-shrink-0" style={{ width: 8, height: 8, background: phase.color }} />
                <span style={{ fontSize: "12px", color: "var(--foreground)", fontWeight: 500 }}>{phase.label}</span>
              </div>
              <span style={{ fontSize: "11px", fontWeight: 700, color: phaseStatusDisplay(phase.status, phase.progress).color }}>
                {phaseStatusDisplay(phase.status, phase.progress).label}
              </span>
            </div>
            <div className="rounded-full overflow-hidden" style={{ height: 6, background: "#e2e8f0" }}>
              <div style={{ height: "100%", width: `${phase.progress}%`, background: phase.color, borderRadius: 999 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── MAIN EXPORT ──────────────────────────────────────────────────────────────

export function AlunoDashboard() {
  const { currentUser } = useApp();
  const { studentId, token } = useAuth();
  const { data: dashData, loading, error } = useAlunoDashboard();
  const [modal, setModal] = useState<ModalData>(null);
  const [tasks, setTasks] = useState<PendingTask[]>([]);
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([]);
  const [checklistLoading, setChecklistLoading] = useState(true);
  const [checklistError, setChecklistError] = useState<string | null>(null);
  const [plan, setPlan] = useState<WorkPlan | null>(null);
  const [planLoading, setPlanLoading] = useState(true);
  const [planError, setPlanError] = useState<string | null>(null);

  const openChecklist = (item: ChecklistItem) => setModal({ type: "checklist", item });
  const openTask = (task: PendingTask) => setModal({ type: "task", task });
  const openNotif = (notif: Notif) => setModal({ type: "notif", notif });
  const openDeadline = (deadline: Deadline) => setModal({ type: "deadline", deadline });
  const handleDone = (id: number) => setTasks(prev => prev.map(t => t.id === id ? { ...t, done: true } : t));

  useEffect(() => {
    setTasks(plan ? tasksFromPlan(plan) : []);
  }, [plan]);

  useEffect(() => {
    if (!studentId || !token) return;
    let active = true;
    setChecklistLoading(true);
    setChecklistError(null);
    getChecklist(studentId, token)
      .then((res) => { if (active) setChecklistItems(buildChecklistItems(res)); })
      .catch(() => { if (active) setChecklistError("Não foi possível carregar o checklist."); })
      .finally(() => { if (active) setChecklistLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  useEffect(() => {
    if (!studentId || !token) return;
    let active = true;
    setPlanLoading(true);
    setPlanError(null);
    getWorkPlan(studentId, token)
      .then((res) => { if (active) setPlan(res); })
      .catch((err: unknown) => {
        if (!active) return;
        setPlan(null);
        // 404 = aluno ainda sem plano cadastrado: estado vazio neutro, não erro.
        if (!(err instanceof ApiError && err.status === 404)) {
          setPlanError("Não foi possível carregar o plano de trabalho.");
        }
      })
      .finally(() => { if (active) setPlanLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  const phases = plan ? phasesFromPlan(plan) : [];
  const totalMonths = plan ? planTotalMonths(plan) : 1;
  const currentMonth = plan ? planCurrentMonth(plan) : 1;

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 400 }}>
        <div className="text-center">
          <div className="animate-spin rounded-full border-4 border-t-transparent" style={{ width: 40, height: 40, borderColor: "var(--border)", borderTopColor: "transparent" }} />
          <p style={{ fontSize: "14px", color: "var(--muted-foreground)", marginTop: 16 }}>Carregando dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl p-6 text-center" style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
        <p style={{ fontSize: "15px", fontWeight: 700, color: "var(--tint-danger-text)" }}>Erro ao carregar dashboard</p>
        <p style={{ fontSize: "13px", color: "var(--tint-danger-text)", opacity: 0.75, marginTop: 4 }}>{error}</p>
      </div>
    );
  }

  // Dados da API com fallback para valores default
  const situacaoInferida = (dashData?.situacao_inferida?.replace(/_/g, "-") ?? "regular") as AcademicStatus;
  const creditosTotal = dashData?.creditos?.total ?? 0;
  const creditosMin = dashData?.creditos?.minimo_requerido ?? 24;
  const diasRestantes = dashData?.dias_restantes ?? 0;
  const producoesAprovadas = dashData?.producoes_aprovadas ?? 0;
  const pontuacaoProducoes = dashData?.producoes?.pontuacao_total ?? 0;

  return (
    <div className="space-y-4 md:space-y-5">

      {/* ── Welcome Banner ── */}
      <div className="rounded-2xl p-4 md:p-5 relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #0d2d5e 0%, #123C7A 55%, #1a4f9a 100%)" }}>
        <div className="absolute pointer-events-none" style={{ right: -40, top: -40, width: 200, height: 200, background: "radial-gradient(circle, rgba(212,160,23,0.2), transparent 70%)", borderRadius: "50%" }} />
        <div className="relative z-10">
          <p style={{ color: "rgba(255,255,255,0.6)", fontSize: "12px" }}>Bem-vindo(a) de volta</p>
          <h2 style={{ color: "#fff", fontSize: "18px", fontWeight: 800, marginTop: "2px", marginBottom: "2px" }}>
            {dashData?.nome ?? currentUser?.name?.split(" ").slice(0, 2).join(" ")}
          </h2>
          <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "11px", marginBottom: "12px" }}>{currentUser?.programa}</p>

          {/* Stats row — horizontal scroll on mobile */}
          <div className="flex gap-4 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
            {[
              { label: "Progresso", value: `${dashData?.progresso_plano_percentual ?? 0}%`, color: "#D4A017" },
              { label: "Dias Rest.", value: `${diasRestantes}`, color: "#fff" },
              { label: "Créditos", value: `${creditosTotal}/${creditosMin}`, color: "#fff" },
              { label: "Produções", value: `${pontuacaoProducoes} pts`, color: "#fff" },
            ].map((stat) => (
              <div key={stat.label} className="flex-shrink-0 text-center" style={{ minWidth: 56 }}>
                <p style={{ color: stat.color, fontSize: "18px", fontWeight: 800, lineHeight: 1 }}>{stat.value}</p>
                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "10px", marginTop: "2px" }}>{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Mobile KPI Carousel / Desktop KPI Grid ── */}
      <MobileKpiCarousel
        situacao={situacaoInferida}
        creditos={creditosTotal}
        minCreditos={creditosMin}
        progressoPct={dashData?.progresso_plano_percentual ?? 0}
        producoes={producoesAprovadas}
        diasRestantes={diasRestantes}
      />
      <DesktopKpiCards
        situacao={situacaoInferida}
        creditos={creditosTotal}
        minCreditos={creditosMin}
        progressoPct={dashData?.progresso_plano_percentual ?? 0}
        producoes={producoesAprovadas}
        diasRestantes={diasRestantes}
      />

      {/* ── Academic Status + Gantt (desktop side-by-side) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-5">
        <AcademicStatusCard situacao={situacaoInferida} conflito={dashData?.conflito_situacao ?? false} />
        <div className="lg:col-span-2 space-y-4 md:space-y-5">
          <GanttTimeline phases={phases} totalMonths={totalMonths} currentMonth={currentMonth} loading={planLoading} error={planError} />
          <MobilePhasesCard phases={phases} totalMonths={totalMonths} currentMonth={currentMonth} loading={planLoading} error={planError} />
        </div>
      </div>

      {/* ── Checklist + Progress Graph ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-5">
        <ChecklistSection items={checklistItems} loading={checklistLoading} error={checklistError} onOpen={openChecklist} />
        <div className="lg:col-span-2">
          <ProgressGraph />
        </div>
      </div>

      {/* ── Tasks + Deadlines ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-5">
        <TasksSection tasks={tasks} loading={planLoading} error={planError} onOpen={openTask} onDone={handleDone} />
        <DeadlinesSection onOpen={openDeadline} />
      </div>

      {/* ── Notifications ── */}
      <NotificationsSection onOpen={openNotif} />

      <Modal data={modal} onClose={() => setModal(null)} />
    </div>
  );
}

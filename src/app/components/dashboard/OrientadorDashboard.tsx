import { useState, type ReactNode } from "react";
import { useApp } from "../../context/AppContext";
import { useAuth } from "@/hooks/useAuth";
import { useOrientadorDashboard } from "@/hooks/useDashboard";
import { useValidationQueue, type ValidationQueueItem } from "@/hooks/useValidationQueue";
import { useNotifications } from "@/hooks/useNotifications";
import { useOrientadorUpdates } from "@/hooks/useOrientadorUpdates";
import {
  AlertTriangle, X, Calendar, ChevronRight,
  CheckCircle2, Bell, Plus, RefreshCw, Star, Send,
  Users, Eye, Clock, GraduationCap, AlertCircle,
  ArrowUpRight, Filter, BookOpen,
} from "lucide-react";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

// ─── TYPES ────────────────────────────────────────────────────────────────────
type StudentStatus = "regular" | "em-risco" | "qualificado" | "fase-defesa" | "prorrogacao";
type QA = "task" | "plano" | "producao" | "reuniao" | null;

interface Student {
  id: string; name: string; init: string;
  nivel: "Mestrado" | "Doutorado"; ingresso: string;
  prazo: string; prazoMeses: number;
  progress: number; creditos: number; creditosMax: number;
  producoes: number; producoesMin: number;
  status: StudentStatus; fase: string;
  ultimaAtual: string; proximo: string; bolsa: string;
}

// ─── STATUS CONFIG ────────────────────────────────────────────────────────────
const ST: Record<StudentStatus, { label: string; color: string; bg: string; border: string }> = {
  regular: { label: "Regular", color: "#1F8A70", bg: "#dcfce7", border: "#bbf7d0" },
  "em-risco": { label: "Em Risco", color: "#D4A017", bg: "#fef9c3", border: "#fde68a" },
  qualificado: { label: "Qualificado", color: "#123C7A", bg: "#eef3fc", border: "#c7d9f5" },
  "fase-defesa": { label: "Apto à Defesa", color: "#8b5cf6", bg: "#f5f3ff", border: "#ddd6fe" },
  prorrogacao: { label: "Prorrogação", color: "#f97316", bg: "#fff7ed", border: "#fed7aa" },
};

// ─── DATA ────────────────────────────────────────────────────────────────────
const STUDENTS: Student[] = [
  { id: "1", name: "Ana Paula Costa", init: "AP", nivel: "Doutorado", ingresso: "2021", prazo: "Mar/2026", prazoMeses: 9, progress: 78, creditos: 52, creditosMax: 80, producoes: 4, producoesMin: 3, status: "qualificado", fase: "Escrita da Tese", ultimaAtual: "há 2 dias", proximo: "Entrega cap. 4", bolsa: "CNPq" },
  { id: "2", name: "Carlos Eduardo Lima", init: "CE", nivel: "Mestrado", ingresso: "2023", prazo: "Jul/2025", prazoMeses: 1, progress: 45, creditos: 18, creditosMax: 30, producoes: 0, producoesMin: 1, status: "em-risco", fase: "Desenvolvimento", ultimaAtual: "há 1 semana", proximo: "Relatório semestral", bolsa: "CAPES" },
  { id: "3", name: "Fernanda Souza Gomes", init: "FS", nivel: "Doutorado", ingresso: "2020", prazo: "Dez/2025", prazoMeses: 6, progress: 92, creditos: 72, creditosMax: 80, producoes: 6, producoesMin: 3, status: "fase-defesa", fase: "Defesa", ultimaAtual: "ontem", proximo: "Agendar banca", bolsa: "FAPESP" },
  { id: "4", name: "Marcos Vinícius Oliveira", init: "MV", nivel: "Mestrado", ingresso: "2022", prazo: "Dez/2024", prazoMeses: -6, progress: 30, creditos: 12, creditosMax: 30, producoes: 0, producoesMin: 1, status: "prorrogacao", fase: "Desenvolvimento", ultimaAtual: "há 3 semanas", proximo: "Formalizar prorrogação", bolsa: "Sem bolsa" },
  { id: "5", name: "Juliana Mendes Martins", init: "JM", nivel: "Doutorado", ingresso: "2022", prazo: "Ago/2026", prazoMeses: 14, progress: 55, creditos: 44, creditosMax: 80, producoes: 2, producoesMin: 3, status: "regular", fase: "Experimentos", ultimaAtual: "há 3 dias", proximo: "Submissão artigo SBES", bolsa: "CAPES" },
  { id: "6", name: "Ricardo Alves Santos", init: "RA", nivel: "Mestrado", ingresso: "2024", prazo: "Dez/2026", prazoMeses: 18, progress: 25, creditos: 8, creditosMax: 30, producoes: 0, producoesMin: 1, status: "regular", fase: "Revisão Bibliográfica", ultimaAtual: "há 5 dias", proximo: "Atualizar plano 2026/2", bolsa: "CNPq" },
  { id: "7", name: "Patrícia Lima Farias", init: "PL", nivel: "Doutorado", ingresso: "2021", prazo: "Mar/2027", prazoMeses: 21, progress: 62, creditos: 48, creditosMax: 80, producoes: 3, producoesMin: 3, status: "qualificado", fase: "Experimentos", ultimaAtual: "há 4 dias", proximo: "Relatório anual", bolsa: "CNPq" },
  { id: "8", name: "Bruno Carvalho Neves", init: "BC", nivel: "Doutorado", ingresso: "2022", prazo: "Jul/2026", prazoMeses: 13, progress: 48, creditos: 38, creditosMax: 80, producoes: 1, producoesMin: 3, status: "regular", fase: "Desenvolvimento", ultimaAtual: "há 1 semana", proximo: "Reunião orientação", bolsa: "CAPES" },
];

const DISTRIB_DATA = [
  { name: "Regular", value: 3, color: "#1F8A70" },
  { name: "Em Risco", value: 1, color: "#D4A017" },
  { name: "Prorrogação", value: 1, color: "#f97316" },
  { name: "Qualificado", value: 2, color: "#123C7A" },
  { name: "Apto à Defesa", value: 1, color: "#8b5cf6" },
];

const CREDIT_CHART = STUDENTS.map((s) => ({
  name: s.init,
  fullName: s.name,
  Obtidos: s.creditos,
  Restantes: Math.max(s.creditosMax - s.creditos, 0),
}));

// API prop types for components
interface OrientadorStatsProps {
  total: number;
  emRisco: number;
  qualificados: number;
  defesa: number;
  prorrogacao: number;
  pendentes: number;
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function SBadge({ status }: { status: StudentStatus }) {
  const c = ST[status];
  return (
    <span className="rounded-full px-2 py-0.5 whitespace-nowrap inline-block"
      style={{ fontSize: "10px", fontWeight: 700, color: c.color, background: c.bg }}>
      {c.label}
    </span>
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

function Avt({ init, size = 36, color = "#123C7A" }: { init: string; size?: number; color?: string }) {
  return (
    <div className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, background: color, color: "#fff", fontSize: size * 0.35, fontWeight: 700 }}>
      {init}
    </div>
  );
}

// ─── MODALS ───────────────────────────────────────────────────────────────────

function StudentModal({ student: s, onClose }: { student: Student; onClose: () => void }) {
  const sc = ST[s.status];
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-4"
      style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
      onClick={onClose}>
      <div className="rounded-2xl w-full max-w-lg max-h-[92vh] overflow-y-auto"
        style={{ background: "var(--card)", boxShadow: "0 20px 60px rgba(0,0,0,0.25)" }}
        onClick={(e) => e.stopPropagation()}>

        <div className="p-5 rounded-t-2xl" style={{ background: sc.bg }}>
          <div className="flex justify-between items-start mb-3">
            <span style={{ fontSize: "11px", fontWeight: 700, color: sc.color, textTransform: "uppercase", letterSpacing: "0.07em" }}>
              Perfil do Orientando
            </span>
            <button onClick={onClose} className="hover:opacity-60 transition-opacity">
              <X size={18} style={{ color: sc.color }} />
            </button>
          </div>
          <div className="flex items-center gap-3">
            <Avt init={s.init} size={50} color={sc.color} />
            <div>
              <p style={{ fontSize: "18px", fontWeight: 800, color: sc.color }}>{s.name}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="rounded-full px-2 py-0.5" style={{ fontSize: "10px", fontWeight: 700, color: sc.color, background: "rgba(255,255,255,0.6)" }}>
                  {s.nivel}
                </span>
                <span style={{ fontSize: "12px", color: sc.color, opacity: 0.75 }}>Ingresso: {s.ingresso} · {s.bolsa}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 md:p-5 space-y-3 md:space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="rounded-xl p-3" style={{ background: "var(--muted)" }}>
              <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginBottom: "5px" }}>Situação</p>
              <SBadge status={s.status} />
            </div>
            <div className="rounded-xl p-3" style={{ background: s.prazoMeses < 0 ? "#fef2f2" : s.prazoMeses < 3 ? "#fffbeb" : "var(--muted)" }}>
              <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginBottom: "5px" }}>Prazo</p>
              <p style={{ fontSize: "13px", fontWeight: 700, color: s.prazoMeses < 0 ? "#dc2626" : s.prazoMeses < 3 ? "#D4A017" : "var(--foreground)" }}>
                {s.prazo} {s.prazoMeses < 0 ? `— Vencido há ${Math.abs(s.prazoMeses)}m` : `(${s.prazoMeses} meses)`}
              </p>
            </div>
          </div>

          <div className="rounded-xl p-3" style={{ background: "var(--muted)" }}>
            <div className="flex justify-between mb-2">
              <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>Progresso Geral</span>
              <span style={{ fontSize: "12px", fontWeight: 800, color: "#123C7A" }}>{s.progress}%</span>
            </div>
            <div className="rounded-full overflow-hidden" style={{ height: 10, background: "#e2e8f0" }}>
              <div style={{ height: "100%", width: `${s.progress}%`, background: sc.color, borderRadius: 999 }} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "Créditos", value: `${s.creditos}/${s.creditosMax}`, warn: s.creditos < s.creditosMax * 0.7, color: "#123C7A" },
              { label: "Produções", value: `${s.producoes}/${s.producoesMin}`, warn: s.producoes < s.producoesMin, color: s.producoes >= s.producoesMin ? "#1F8A70" : "#D4A017" },
              { label: "Fase Atual", value: s.fase, warn: false, color: "var(--foreground)" },
            ].map((m) => (
              <div key={m.label} className="rounded-xl p-3 text-center" style={{ background: "var(--muted)" }}>
                <p style={{ fontSize: "13px", fontWeight: 800, color: m.color, lineHeight: 1.3 }}>{m.value}</p>
                <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "3px" }}>{m.label}</p>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-3 rounded-xl p-3" style={{ background: "#eef3fc", border: "1px solid #c7d9f5" }}>
              <Star size={13} style={{ color: "#123C7A", flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: "11px", fontWeight: 600, color: "#123C7A" }}>Próximo Marco</p>
                <p style={{ fontSize: "12px", color: "var(--foreground)" }}>{s.proximo}</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 rounded-xl p-3" style={{ background: "var(--muted)" }}>
              <Clock size={12} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
              <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
                Última atualização: <strong>{s.ultimaAtual}</strong>
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-1">
            {[
              { label: "Criar Tarefa", color: "#123C7A", bg: "#eef3fc" },
              { label: "Solicitar Reunião", color: "#8b5cf6", bg: "#f5f3ff" },
            ].map((btn) => (
              <button key={btn.label} onClick={onClose}
                className="py-2.5 rounded-xl transition-colors"
                style={{ background: btn.bg, color: btn.color, fontSize: "13px", fontWeight: 700 }}>
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickActionModal({ type, onClose }: { type: Exclude<QA, null>; onClose: () => void }) {
  const [done, setDone] = useState(false);
  const names = STUDENTS.map((s) => s.name);

  const cfg = {
    task: { title: "Criar Tarefa para Orientando", color: "#123C7A", bg: "#eef3fc", icon: <Plus size={18} /> },
    plano: { title: "Atualizar Plano de Trabalho", color: "#1F8A70", bg: "#dcfce7", icon: <RefreshCw size={18} /> },
    producao: { title: "Avaliar Produção Científica", color: "#D4A017", bg: "#fffbeb", icon: <Star size={18} /> },
    reuniao: { title: "Solicitar Reunião de Orientação", color: "#8b5cf6", bg: "#f5f3ff", icon: <Send size={18} /> },
  }[type];

  const btnLabel = { task: "Criar Tarefa", plano: "Salvar Atualização", producao: "Registrar Avaliação", reuniao: "Enviar Convite" }[type];

  const inputCls = "w-full rounded-xl px-3 py-2.5 outline-none";
  const inputSt: React.CSSProperties = { border: "2px solid var(--border)", background: "var(--muted)", fontSize: "13px", color: "var(--foreground)" };
  const labelSt: React.CSSProperties = { fontSize: "12px", fontWeight: 600, color: "var(--foreground)", display: "block", marginBottom: "6px" };

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
        onClick={onClose}>
        <div className="rounded-2xl p-8 max-w-sm w-full text-center"
          style={{ background: "var(--card)" }} onClick={(e) => e.stopPropagation()}>
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#dcfce7" }}>
            <CheckCircle2 size={32} style={{ color: "#1F8A70" }} />
          </div>
          <p style={{ fontSize: "17px", fontWeight: 800, color: "var(--foreground)", marginBottom: "8px" }}>Ação Registrada!</p>
          <p style={{ fontSize: "13px", color: "var(--muted-foreground)", marginBottom: "24px" }}>
            A ação foi registrada com sucesso no SAGA e o orientando será notificado.
          </p>
          <button onClick={onClose} className="w-full py-3 rounded-xl"
            style={{ background: "#123C7A", color: "#fff", fontWeight: 700, fontSize: "14px" }}>
            Fechar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-4"
      style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(4px)" }}
      onClick={onClose}>
      <div className="rounded-2xl w-full max-w-md max-h-[92vh] overflow-y-auto"
        style={{ background: "var(--card)", boxShadow: "0 20px 60px rgba(0,0,0,0.25)" }}
        onClick={(e) => e.stopPropagation()}>

        <div className="flex items-center justify-between p-5 rounded-t-2xl" style={{ background: cfg.bg }}>
          <div className="flex items-center gap-2.5">
            <span style={{ color: cfg.color }}>{cfg.icon}</span>
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: cfg.color }}>{cfg.title}</h3>
          </div>
          <button onClick={onClose} className="hover:opacity-60 transition-opacity">
            <X size={18} style={{ color: cfg.color }} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Student selector — shared */}
          <div>
            <label style={labelSt}>Orientando <span style={{ color: "#dc2626" }}>*</span></label>
            <select className={inputCls} style={inputSt}>
              <option value="">Selecionar orientando…</option>
              {names.map((n) => <option key={n}>{n}</option>)}
            </select>
          </div>

          {type === "task" && (
            <>
              <div>
                <label style={labelSt}>Título da Tarefa <span style={{ color: "#dc2626" }}>*</span></label>
                <input type="text" placeholder="Descreva a tarefa…" className={inputCls} style={inputSt} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label style={labelSt}>Prioridade</label>
                  <select className={inputCls} style={inputSt}>
                    <option>Alta</option><option>Média</option><option>Baixa</option>
                  </select>
                </div>
                <div>
                  <label style={labelSt}>Prazo</label>
                  <input type="date" className={inputCls} style={inputSt} />
                </div>
              </div>
              <div>
                <label style={labelSt}>Descrição / Instruções</label>
                <textarea rows={3} placeholder="Detalhes da tarefa para o orientando…" className={inputCls + " resize-none"} style={inputSt} />
              </div>
            </>
          )}

          {type === "plano" && (
            <>
              <div>
                <label style={labelSt}>Fase Atual do Aluno</label>
                <select className={inputCls} style={inputSt}>
                  {["Revisão Bibliográfica", "Definição do Problema", "Desenvolvimento", "Experimentos", "Qualificação", "Escrita da Tese", "Defesa"].map((f) => (
                    <option key={f}>{f}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelSt}>Progresso da Fase Atual (%)</label>
                <div className="flex items-center gap-3">
                  <input type="range" min="0" max="100" defaultValue="50" className="flex-1" />
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "#123C7A", minWidth: 36 }}>50%</span>
                </div>
              </div>
              <div>
                <label style={labelSt}>Próximo Marco Esperado</label>
                <input type="text" placeholder="Ex: Entrega do capítulo 3…" className={inputCls} style={inputSt} />
              </div>
              <div>
                <label style={labelSt}>Observações do Orientador</label>
                <textarea rows={3} placeholder="Comentários sobre o andamento do aluno…" className={inputCls + " resize-none"} style={inputSt} />
              </div>
            </>
          )}

          {type === "producao" && (
            <>
              <div>
                <label style={labelSt}>Título da Produção Científica <span style={{ color: "#dc2626" }}>*</span></label>
                <input type="text" placeholder="Título completo do artigo ou trabalho…" className={inputCls} style={inputSt} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label style={labelSt}>Classificação Qualis</label>
                  <select className={inputCls} style={inputSt}>
                    {["A1", "A2", "B1", "B2", "B3", "B4", "C"].map((q) => <option key={q}>{q}</option>)}
                  </select>
                </div>
                <div>
                  <label style={labelSt}>Tipo de Veículo</label>
                  <select className={inputCls} style={inputSt}>
                    <option>Periódico</option><option>Conferência Nacional</option><option>Conferência Internacional</option><option>Workshop</option>
                  </select>
                </div>
              </div>
              <div>
                <label style={labelSt}>Decisão do Orientador</label>
                <select className={inputCls} style={inputSt}>
                  <option>Aprovado — Validar Créditos</option>
                  <option>Aprovado — Aguardando publicação</option>
                  <option>Revisão Necessária</option>
                  <option>Reprovado</option>
                </select>
              </div>
              <div>
                <label style={labelSt}>Comentários / Parecer</label>
                <textarea rows={3} placeholder="Justificativa e observações…" className={inputCls + " resize-none"} style={inputSt} />
              </div>
            </>
          )}

          {type === "reuniao" && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label style={labelSt}>Data Proposta</label>
                  <input type="date" className={inputCls} style={inputSt} />
                </div>
                <div>
                  <label style={labelSt}>Horário</label>
                  <input type="time" className={inputCls} style={inputSt} />
                </div>
              </div>
              <div>
                <label style={labelSt}>Pauta / Assunto Principal <span style={{ color: "#dc2626" }}>*</span></label>
                <input type="text" placeholder="Ex: Revisão do cap. 3, andamento da pesquisa…" className={inputCls} style={inputSt} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label style={labelSt}>Modalidade</label>
                  <select className={inputCls} style={inputSt}>
                    <option>Presencial</option><option>Online – Google Meet</option><option>Online – Zoom</option>
                  </select>
                </div>
                <div>
                  <label style={labelSt}>Duração Estimada</label>
                  <select className={inputCls} style={inputSt}>
                    <option>30 minutos</option><option>1 hora</option><option>1h30</option><option>2 horas</option>
                  </select>
                </div>
              </div>
            </>
          )}

          <button onClick={() => setDone(true)}
            className="w-full py-3 rounded-xl transition-all"
            style={{ background: cfg.color, color: "#fff", fontSize: "14px", fontWeight: 700 }}>
            {btnLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── SECTIONS ─────────────────────────────────────────────────────────────────

function KpiCards({ total, emRisco, qualificados, defesa, prorrogacao }: OrientadorStatsProps) {
  const atRisk = emRisco + prorrogacao;
  // Doutorado/Mestrado counts are not returned by the API yet, keeping placeholder logic for sub-text
  const dout = Math.round(total * 0.6); 
  const mest = total - dout;

  const cards = [
    { icon: <Users size={20} />, label: "Total de Orientandos", value: total, sub: `${dout} doutorado · ${mest} mestrado`, color: "#123C7A", bg: "#eef3fc" },
    { icon: <AlertTriangle size={20} />, label: "Em Risco / Prorrogação", value: atRisk, sub: "Requerem atenção imediata", color: "#dc2626", bg: "#fef2f2" },
    { icon: <GraduationCap size={20} />, label: "Qualificados", value: qualificados, sub: "Fase avançada de pesquisa", color: "#123C7A", bg: "#eef3fc" },
    { icon: <Star size={20} />, label: "Aptos à Defesa", value: defesa, sub: "Prontos para a banca", color: "#8b5cf6", bg: "#f5f3ff" },
    { icon: <CheckCircle2 size={20} />, label: "Concluídos (histórico)", value: 12, sub: "Total de títulos orientados", color: "#1F8A70", bg: "#dcfce7" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2 md:gap-3">
      {cards.map((c) => (
        <div key={c.label} className="rounded-2xl p-3 md:p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="rounded-xl flex items-center justify-center mb-2 md:mb-3" style={{ width: 32, height: 32, background: c.bg }}>
            <span style={{ color: c.color, fontSize: "14px" }}>{c.icon}</span>
          </div>
          <p style={{ fontSize: "24px", fontWeight: 800, color: c.color, lineHeight: 1 }} className="md:text-3xl">{c.value}</p>
          <p style={{ fontSize: "11px", fontWeight: 600, color: "var(--foreground)", marginTop: "3px" }} className="md:text-xs">{c.label}</p>
          <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "1px" }} className="md:text-[11px]">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}

function QuickBar({ onAction }: { onAction: (t: Exclude<QA, null>) => void }) {
  const actions: { key: Exclude<QA, null>; label: string; icon: ReactNode; color: string; bg: string }[] = [
    { key: "task", label: "Criar Tarefa", icon: <Plus size={15} />, color: "#123C7A", bg: "#eef3fc" },
    { key: "plano", label: "Atualizar Plano", icon: <RefreshCw size={15} />, color: "#1F8A70", bg: "#dcfce7" },
    { key: "producao", label: "Avaliar Produção", icon: <Star size={15} />, color: "#D4A017", bg: "#fffbeb" },
    { key: "reuniao", label: "Solicitar Reunião", icon: <Send size={15} />, color: "#8b5cf6", bg: "#f5f3ff" },
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((a) => (
        <button key={a.key} onClick={() => onAction(a.key)}
          className="flex items-center gap-2 rounded-xl px-4 py-2.5 transition-all"
          style={{ background: a.bg, color: a.color, fontSize: "12px", fontWeight: 700, border: `1px solid ${a.color}25` }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = "translateY(-1px)"; (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 12px rgba(0,0,0,0.12)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = "none"; (e.currentTarget as HTMLElement).style.boxShadow = "none"; }}>
          {a.icon} {a.label}
        </button>
      ))}
    </div>
  );
}

function StudentTable({ onSelect }: { onSelect: (s: Student) => void }) {
  const [sortBy, setSortBy] = useState<"status" | "progress" | "prazo" | "name">("status");
  const [filterStatus, setFilterStatus] = useState<StudentStatus | "todos">("todos");

  const statusOrder: Record<StudentStatus, number> = { prorrogacao: 0, "em-risco": 1, qualificado: 2, "fase-defesa": 3, regular: 4 };

  const sorted = [...STUDENTS]
    .filter((s) => filterStatus === "todos" || s.status === filterStatus)
    .sort((a, b) => {
      if (sortBy === "progress") return b.progress - a.progress;
      if (sortBy === "prazo") return a.prazoMeses - b.prazoMeses;
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return statusOrder[a.status] - statusOrder[b.status];
    });

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Lista de Orientandos"
        sub={`${STUDENTS.length} orientandos ativos`}
        right={
          <div className="flex items-center gap-2 flex-wrap">
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as StudentStatus | "todos")}
              className="rounded-lg px-2.5 py-1.5 outline-none"
              style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: "11px", color: "var(--foreground)" }}>
              <option value="todos">Todas situações</option>
              {(Object.keys(ST) as StudentStatus[]).map((s) => (
                <option key={s} value={s}>{ST[s].label}</option>
              ))}
            </select>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
              className="rounded-lg px-2.5 py-1.5 outline-none"
              style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: "11px", color: "var(--foreground)" }}>
              <option value="status">Situação</option>
              <option value="progress">Progresso</option>
              <option value="prazo">Prazo</option>
              <option value="name">Nome</option>
            </select>
          </div>
        }
      />

      <div className="overflow-x-auto -mx-4 px-4 md:mx-0 md:px-0">
        <table className="w-full" style={{ borderCollapse: "separate", borderSpacing: "0 3px", minWidth: "800px" }}>
          <thead>
            <tr>
              {["Orientando", "Situação", "Progresso", "Créditos", "Produções", "Prazo", "Fase Atual", ""].map((h) => (
                <th key={h} style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.06em", padding: "0 8px 10px", textAlign: "left", whiteSpace: "nowrap" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.id} className="cursor-pointer transition-colors"
                style={{ borderRadius: 12 }}
                onClick={() => onSelect(s)}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--muted)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}>
                <td style={{ padding: "9px 8px", borderRadius: "12px 0 0 12px" }}>
                  <div className="flex items-center gap-2.5">
                    <Avt init={s.init} size={32} color={ST[s.status].color} />
                    <div>
                      <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", whiteSpace: "nowrap" }}>{s.name}</p>
                      <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{s.nivel} · {s.ingresso} · {s.bolsa}</p>
                    </div>
                  </div>
                </td>
                <td style={{ padding: "9px 8px" }}>
                  <SBadge status={s.status} />
                </td>
                <td style={{ padding: "9px 8px", minWidth: 100 }}>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 rounded-full overflow-hidden" style={{ height: 6, background: "#e2e8f0" }}>
                      <div style={{ height: "100%", width: `${s.progress}%`, background: ST[s.status].color, borderRadius: 999 }} />
                    </div>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--foreground)", minWidth: 32, textAlign: "right" }}>{s.progress}%</span>
                  </div>
                </td>
                <td style={{ padding: "9px 8px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{s.creditos}/{s.creditosMax}</span>
                </td>
                <td style={{ padding: "9px 8px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: s.producoes >= s.producoesMin ? "#1F8A70" : "#D4A017" }}>
                    {s.producoes}/{s.producoesMin}
                  </span>
                </td>
                <td style={{ padding: "9px 8px" }}>
                  <p style={{ fontSize: "12px", fontWeight: 600, color: s.prazoMeses < 0 ? "#dc2626" : s.prazoMeses < 3 ? "#D4A017" : "var(--foreground)", whiteSpace: "nowrap" }}>
                    {s.prazo}
                  </p>
                  <p style={{ fontSize: "10px", color: s.prazoMeses < 0 ? "#dc2626" : "var(--muted-foreground)", whiteSpace: "nowrap" }}>
                    {s.prazoMeses < 0 ? `${Math.abs(s.prazoMeses)}m vencido` : `${s.prazoMeses}m restantes`}
                  </p>
                </td>
                <td style={{ padding: "9px 8px" }}>
                  <span style={{ fontSize: "11px", color: "var(--foreground)", whiteSpace: "nowrap" }}>{s.fase}</span>
                </td>
                <td style={{ padding: "9px 8px", borderRadius: "0 12px 12px 0" }}>
                  <button onClick={(e) => { e.stopPropagation(); onSelect(s); }}
                    className="rounded-lg px-2.5 py-1 flex items-center gap-1"
                    style={{ background: "#eef3fc", color: "#123C7A", fontSize: "11px", fontWeight: 600, whiteSpace: "nowrap" }}>
                    <Eye size={11} /> Ver
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SituationChart({ total, emRisco, qualificados, defesa, prorrogacao }: OrientadorStatsProps) {
  const regular = Math.max(0, total - (emRisco + qualificados + defesa + prorrogacao));
  const distribData = [
    { name: "Regular", value: regular, color: "#1F8A70" },
    { name: "Em Risco", value: emRisco, color: "#D4A017" },
    { name: "Prorrogação", value: prorrogacao, color: "#f97316" },
    { name: "Qualificado", value: qualificados, color: "#123C7A" },
    { name: "Apto à Defesa", value: defesa, color: "#8b5cf6" },
  ].filter(d => d.value > 0);

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead title="Distribuição" sub="Situações acadêmicas" />

      <div className="flex justify-center mb-4">
        <div className="relative">
          <PieChart width={160} height={160}>
            <Pie data={distribData} cx={75} cy={75} innerRadius={48} outerRadius={75} paddingAngle={3} dataKey="value" isAnimationActive={false}>
              {distribData.map((entry, i) => <Cell key={`distrib-${i}`} fill={entry.color} />)}
            </Pie>
            <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
          </PieChart>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <p style={{ fontSize: "26px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }}>{total}</p>
            <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>orientandos</p>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {distribData.map((d) => (
          <div key={d.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-full flex-shrink-0" style={{ width: 10, height: 10, background: d.color }} />
              <span style={{ fontSize: "12px", color: "var(--foreground)" }}>{d.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="rounded-full overflow-hidden" style={{ width: 48, height: 5, background: "#e2e8f0" }}>
                <div style={{ height: "100%", width: `${(d.value / Math.max(1, total)) * 100}%`, background: d.color, borderRadius: 999 }} />
              </div>
              <span style={{ fontSize: "13px", fontWeight: 800, color: d.color, minWidth: 14, textAlign: "right" }}>{d.value}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CreditBarChart() {
  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Créditos por Orientando"
        sub="Créditos obtidos vs. restantes para conclusão do programa"
      />
      <ResponsiveContainer width="100%" height={175}>
        <BarChart data={CREDIT_CHART} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid key="cb-grid" strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis key="cb-x" dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis key="cb-y" width={28} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <Tooltip key="cb-tip"
            contentStyle={{ borderRadius: 10, fontSize: 12, border: "1px solid var(--border)", background: "var(--card)" }}
            formatter={(val: number, name: string) => [`${val} cr`, name === "Obtidos" ? "Créditos Obtidos" : "Créditos Restantes"]}
            labelFormatter={(label) => {
              const s = CREDIT_CHART.find((c) => c.name === label);
              return s ? s.fullName : label;
            }}
          />
          <Bar key="cb-b1" dataKey="Obtidos" name="Obtidos" fill="#1F8A70" stackId="a" isAnimationActive={false} />
          <Bar key="cb-b2" dataKey="Restantes" name="Restantes" fill="#e2e8f0" stackId="a" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-5 mt-2">
        {[{ color: "#1F8A70", label: "Créditos Obtidos" }, { color: "#e2e8f0", label: "Créditos Restantes" }].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div style={{ width: 12, height: 12, background: l.color, borderRadius: 3 }} />
            <span style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkPlanMonitoring({ onSelect }: { onSelect: (s: Student) => void }) {
  const phaseColor: Record<string, string> = {
    "Revisão Bibliográfica": "#123C7A", "Definição do Problema": "#1F8A70",
    "Desenvolvimento": "#8b5cf6", "Experimentos": "#D4A017",
    "Escrita da Tese": "#f97316", "Qualificação": "#dc2626", "Defesa": "#0ea5e9",
  };

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Monitoramento dos Planos de Trabalho"
        sub="Fase atual, progresso e próximos marcos de cada orientando"
      />
      <div className="space-y-2.5">
        {STUDENTS.map((s) => {
          const pc = phaseColor[s.fase] || "#94a3b8";
          return (
            <div key={s.id}
              className="flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all hover:shadow-sm"
              style={{ background: "var(--muted)" }}
              onClick={() => onSelect(s)}>

              <Avt init={s.init} size={30} color={ST[s.status].color} />

              <div style={{ minWidth: 130, flexShrink: 0 }}>
                <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 128 }}>
                  {s.name}
                </p>
                <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{s.nivel} · {s.ingresso}</p>
              </div>

              <div className="flex items-center gap-1.5" style={{ minWidth: 130, flexShrink: 0 }}>
                <div className="rounded-sm flex-shrink-0" style={{ width: 8, height: 8, background: pc }} />
                <span style={{ fontSize: "11px", color: "var(--foreground)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 118 }}>
                  {s.fase}
                </span>
              </div>

              <div className="flex-1 flex items-center gap-2">
                <div className="flex-1 rounded-full overflow-hidden" style={{ height: 7, background: "#e2e8f0" }}>
                  <div style={{ height: "100%", width: `${s.progress}%`, background: ST[s.status].color, borderRadius: 999 }} />
                </div>
                <span style={{ fontSize: "11px", fontWeight: 800, color: "var(--foreground)", flexShrink: 0, minWidth: 30, textAlign: "right" }}>
                  {s.progress}%
                </span>
              </div>

              <div style={{ minWidth: 90, flexShrink: 0, textAlign: "right" }}>
                <p style={{ fontSize: "11px", color: "#123C7A", fontWeight: 600 }}>{s.proximo}</p>
                <p style={{ fontSize: "9px", color: "var(--muted-foreground)" }}>Próximo marco</p>
              </div>

              <div style={{ minWidth: 70, flexShrink: 0, textAlign: "right" }}>
                <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{s.ultimaAtual}</p>
                <p style={{ fontSize: "9px", color: "var(--muted-foreground)" }}>último update</p>
              </div>

              <div style={{ flexShrink: 0 }}>
                <SBadge status={s.status} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Formata data ISO (date "AAAA-MM-DD" ou datetime) em "DD/MM/AAAA", sem deslocar por fuso.
function formatDataBR(value?: string | null): string {
  if (!value) return "—";
  const match = value.slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("pt-BR");
}

const REVIEW_TIPO_CFG: Record<ValidationQueueItem["tipo"], { label: string; color: string; icon: ReactNode }> = {
  atividade: { label: "Atividade", color: "var(--tint-gold-text)", icon: <BookOpen size={13} /> },
  producao: { label: "Produção", color: "var(--tint-teal-text)", icon: <Star size={13} /> },
};

function PendingReviews() {
  const { data, loading, error } = useValidationQueue();
  const items = data ?? [];

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Avaliações Pendentes"
        sub={loading ? "Carregando…" : `${items.length} ${items.length === 1 ? "item aguardando" : "itens aguardando"} seu parecer`}
      />

      {error ? (
        <p style={{ fontSize: "12px", color: "var(--tint-danger-text)" }}>Erro ao carregar avaliações pendentes: {error}</p>
      ) : loading ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando avaliações pendentes…</p>
      ) : items.length === 0 ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Nenhum item aguardando seu parecer.</p>
      ) : (
        <div className="space-y-2.5">
          {items.map((item) => {
            const tc = REVIEW_TIPO_CFG[item.tipo];
            return (
              <div key={item.id} className="flex items-start gap-3 p-3 rounded-xl"
                style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: `${tc.color}18`, color: tc.color }}>
                  {tc.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                    <span className="rounded-full px-1.5 py-0.5" style={{ fontSize: "9px", fontWeight: 800, color: tc.color, background: `${tc.color}15` }}>{tc.label}</span>
                  </div>
                  <p style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)" }}>{item.aluno}</p>
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)", lineHeight: 1.4 }}>{item.descricao}</p>
                  <p style={{ fontSize: "10px", fontWeight: 700, color: "var(--muted-foreground)", marginTop: "3px" }}>
                    <Calendar size={9} className="inline mr-1" />Enviado em: {formatDataBR(item.data)}
                  </p>
                </div>
                <button className="px-3 py-1.5 rounded-lg flex-shrink-0 transition-all hover:opacity-90"
                  style={{ background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "11px", fontWeight: 700, whiteSpace: "nowrap" }}>
                  Avaliar
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// Mapeia a operação do audit_log (nome da função Python) para rótulo + emoji da timeline.
const OPERACAO_CFG: Record<string, { label: string; emoji: string; bg: string }> = {
  submit_activity: { label: "Submeteu atividade para validação", emoji: "📋", bg: "var(--tint-blue-bg)" },
  create_activity: { label: "Registrou atividade creditável", emoji: "📋", bg: "var(--tint-blue-bg)" },
  create_production: { label: "Registrou produção científica", emoji: "📄", bg: "var(--tint-teal-bg)" },
};
const OPERACAO_DEFAULT = { emoji: "•", bg: "var(--muted)" };

// Fallback humano para operações sem rótulo dedicado: "update_work_plan" → "update work plan".
function humanizeOperacao(operacao: string | null): string {
  if (!operacao) return "Registrou uma ação no SAGA";
  return operacao.replace(/_/g, " ");
}

function RecentUpdates() {
  const { data, loading, error } = useOrientadorUpdates();
  const items = data ?? [];

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead title="Atualizações Recentes" sub="Atividades recentes dos orientandos no SAGA" />

      {error ? (
        <p style={{ fontSize: "12px", color: "var(--tint-danger-text)" }}>Erro ao carregar atualizações: {error}</p>
      ) : loading ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando atualizações…</p>
      ) : items.length === 0 ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Nenhuma atualização recente.</p>
      ) : (
        <div className="space-y-3.5">
          {items.map((item, i) => {
            const cfg = item.operacao ? OPERACAO_CFG[item.operacao] : undefined;
            const bg = cfg?.bg ?? OPERACAO_DEFAULT.bg;
            const emoji = cfg?.emoji ?? OPERACAO_DEFAULT.emoji;
            const label = cfg?.label ?? humanizeOperacao(item.operacao);
            const isLast = i === items.length - 1;
            return (
              <div key={item.id} className="flex items-start gap-3">
                {/* Timeline line */}
                <div className="flex flex-col items-center flex-shrink-0">
                  <div className="rounded-full flex items-center justify-center" style={{ width: 32, height: 32, background: bg, fontSize: 14 }}>
                    {emoji}
                  </div>
                  {!isLast && <div style={{ width: 2, flex: 1, background: "var(--border)", minHeight: 16, marginTop: 4 }} />}
                </div>
                <div className="flex-1 min-w-0 pb-1">
                  <div className="flex items-start justify-between gap-2 mb-0.5">
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)" }}>{label}</span>
                    <span style={{ fontSize: "10px", color: "var(--muted-foreground)", flexShrink: 0, whiteSpace: "nowrap" }}>{formatDataBR(item.timestamp)}</span>
                  </div>
                  {item.recurso && (
                    <p style={{ fontSize: "11px", color: "var(--muted-foreground)", lineHeight: 1.4, wordBreak: "break-all" }}>{item.recurso}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

type AlertSeverity = "critico" | "atencao" | "info";

// Mapeia o tipo da notificação (A05) para a severidade visual do painel. Default: "info".
const NOTIF_SEVERITY: Record<string, AlertSeverity> = {
  prazo_critico: "critico",
  atividade_submetida: "atencao",
  prorrogacao_aprovada: "atencao",
  transferencia_orientador: "atencao",
  transferencia_coordenacao: "atencao",
  atividade_validada: "info",
  progresso_task: "info",
};

function AcademicAlerts() {
  const { notifications, loading } = useNotifications();
  const alertCfg: Record<AlertSeverity, { color: string; bg: string; border: string; icon: ReactNode; label: string }> = {
    critico: { color: "#dc2626", bg: "#fef2f2", border: "#fecaca", icon: <AlertCircle size={14} />, label: "CRÍTICO" },
    atencao: { color: "#D4A017", bg: "#fffbeb", border: "#fde68a", icon: <AlertTriangle size={14} />, label: "ATENÇÃO" },
    info: { color: "#0ea5e9", bg: "#f0f9ff", border: "#bae6fd", icon: <Bell size={14} />, label: "INFO" },
  };
  const severityOf = (tipo: string): AlertSeverity => NOTIF_SEVERITY[tipo] ?? "info";

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Alertas Acadêmicos"
        sub={loading ? "Carregando…" : "Situações identificadas pelo SAGA"}
        right={
          <span className="rounded-full px-2 py-0.5" style={{ fontSize: "11px", fontWeight: 700, color: "#dc2626", background: "#fef2f2" }}>
            {notifications.filter((n) => severityOf(n.tipo) === "critico").length} críticos
          </span>
        }
      />

      {loading ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando alertas…</p>
      ) : notifications.length === 0 ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Nenhum alerta no momento.</p>
      ) : (
        <div className="space-y-2.5">
          {notifications.map((n) => {
            const ac = alertCfg[severityOf(n.tipo)];
            return (
              <div key={n.id} className="rounded-xl p-3" style={{ background: ac.bg, border: `1px solid ${ac.border}` }}>
                <div className="flex items-start gap-2.5">
                  <span style={{ color: ac.color, flexShrink: 0, marginTop: 1 }}>{ac.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                      <span className="rounded-full px-1.5 py-0.5" style={{ fontSize: "8px", fontWeight: 800, color: "#fff", background: ac.color }}>{ac.label}</span>
                      {n.timestamp && (
                        <span style={{ fontSize: "11px", fontWeight: 700, color: ac.color }}>{n.timestamp.toLocaleDateString("pt-BR")}</span>
                      )}
                    </div>
                    <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)", lineHeight: 1.35 }}>{n.titulo}</p>
                    <p style={{ fontSize: "11px", color: "var(--muted-foreground)", lineHeight: 1.4, marginTop: "3px" }}>{n.mensagem}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AttentionStudents({
  onSelect,
  onAction,
}: {
  onSelect: (s: Student) => void;
  onAction: (t: Exclude<QA, null>) => void;
}) {
  const atRisk = STUDENTS.filter((s) => s.status === "em-risco" || s.status === "prorrogacao");

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SecHead
        title="Orientandos que Requerem Atenção"
        sub={`${atRisk.length} orientandos em situação crítica — ação imediata necessária`}
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {atRisk.map((s) => {
          const sc = ST[s.status];
          return (
            <div key={s.id} className="rounded-2xl p-4" style={{ background: sc.bg, border: `2px solid ${sc.border}` }}>
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <Avt init={s.init} size={40} color={sc.color} />
                  <div>
                    <p style={{ fontSize: "14px", fontWeight: 800, color: sc.color }}>{s.name}</p>
                    <p style={{ fontSize: "11px", color: sc.color, opacity: 0.75 }}>{s.nivel} · Ingresso {s.ingresso} · {s.bolsa}</p>
                  </div>
                </div>
                <SBadge status={s.status} />
              </div>

              {/* Progress bar */}
              <div className="mb-3">
                <div className="flex justify-between items-center mb-1.5">
                  <span style={{ fontSize: "11px", fontWeight: 600, color: sc.color }}>Progresso geral</span>
                  <span style={{ fontSize: "11px", fontWeight: 800, color: sc.color }}>{s.progress}%</span>
                </div>
                <div className="rounded-full overflow-hidden" style={{ height: 8, background: `${sc.color}25` }}>
                  <div style={{ height: "100%", width: `${s.progress}%`, background: sc.color, borderRadius: 999 }} />
                </div>
              </div>

              {/* Metric pills */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                {[
                  { label: "Créditos", value: `${s.creditos}/${s.creditosMax}`, warn: (s.creditos / s.creditosMax) < 0.6 },
                  { label: "Produções", value: `${s.producoes}/${s.producoesMin}`, warn: s.producoes < s.producoesMin },
                  { label: "Prazo", value: s.prazoMeses < 0 ? `${Math.abs(s.prazoMeses)}m venc.` : `${s.prazoMeses}m rest.`, warn: s.prazoMeses < 3 },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg p-2 text-center"
                    style={{ background: m.warn ? `${sc.color}22` : "rgba(255,255,255,0.55)" }}>
                    <p style={{ fontSize: "12px", fontWeight: 800, color: m.warn ? sc.color : "var(--foreground)" }}>{m.value}</p>
                    <p style={{ fontSize: "9px", color: m.warn ? sc.color : "var(--muted-foreground)" }}>{m.label}</p>
                  </div>
                ))}
              </div>

              {/* Situation note */}
              <div className="rounded-lg p-2.5 mb-3" style={{ background: "rgba(255,255,255,0.55)" }}>
                <p style={{ fontSize: "11px", fontWeight: 600, color: sc.color, marginBottom: "2px" }}>Situação:</p>
                <p style={{ fontSize: "11px", color: "var(--foreground)", lineHeight: 1.5 }}>
                  {s.status === "em-risco"
                    ? `Prazo vence em ${s.prazoMeses} meses. ${s.producoes === 0 ? "Nenhuma produção científica publicada." : `${s.producoesMin - s.producoes} produção(ões) em falta.`} Acompanhamento urgente necessário.`
                    : `Prazo vencido há ${Math.abs(s.prazoMeses)} meses. Formalização de prorrogação junto à coordenação é urgente.`}
                </p>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <button onClick={() => onSelect(s)}
                  className="flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  style={{ background: "rgba(255,255,255,0.7)", color: sc.color, fontSize: "11px", fontWeight: 700 }}>
                  <Eye size={11} /> Perfil
                </button>
                <button onClick={() => onAction("reuniao")}
                  className="flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  style={{ background: sc.color, color: "#fff", fontSize: "11px", fontWeight: 700 }}>
                  <Send size={11} /> Reunião
                </button>
                <button onClick={() => onAction("task")}
                  className="flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  style={{ background: "rgba(255,255,255,0.7)", color: sc.color, fontSize: "11px", fontWeight: 700 }}>
                  <Plus size={11} /> Tarefa
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function OrientadorDashboard() {
  const { currentUser } = useApp();
  const { advisorId } = useAuth();
  const { data: dashData, loading, error } = useOrientadorDashboard(
    currentUser?.advisor_id ?? advisorId ?? currentUser?.id,
  );
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [quickAction, setQuickAction] = useState<QA>(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 400 }}>
        <div className="text-center">
          <div className="animate-spin rounded-full border-4 border-t-transparent" style={{ width: 40, height: 40, borderColor: "var(--border)", borderTopColor: "transparent" }} />
          <p style={{ fontSize: "14px", color: "var(--muted-foreground)", marginTop: 16 }}>Carregando dashboard do orientador...</p>
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

  const stats: OrientadorStatsProps = {
    total: dashData?.total_orientandos ?? 0,
    emRisco: dashData?.orientandos_por_status?.em_risco ?? 0,
    qualificados: dashData?.orientandos_por_status?.qualificado ?? 0,
    defesa: dashData?.orientandos_por_status?.fase_defesa ?? 0,
    prorrogacao: dashData?.orientandos_por_status?.em_prorrogacao ?? 0,
    pendentes: dashData?.atividades_aguardando_parecer ?? 0,
  };

  return (
    <div className="space-y-5">
      {/* ── Welcome Banner ── */}
      <div className="rounded-2xl p-5 relative overflow-hidden"
        style={{ background: "linear-gradient(135deg, #0a2540 0%, #123C7A 55%, #1a5090 100%)" }}>
        <div className="absolute pointer-events-none"
          style={{ right: -50, top: -50, width: 240, height: 240, background: "radial-gradient(circle, rgba(31,138,112,0.25), transparent 70%)", borderRadius: "50%" }} />
        <div className="absolute pointer-events-none"
          style={{ left: "35%", bottom: -30, width: 180, height: 180, background: "radial-gradient(circle, rgba(212,160,23,0.15), transparent 70%)", borderRadius: "50%" }} />
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center gap-4">
          <div className="flex-1">
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "12px" }}>Painel do Orientador · SAGA</p>
            <h2 style={{ color: "#fff", fontSize: "20px", fontWeight: 800, marginTop: "2px", marginBottom: "2px" }}>
              {dashData?.nome ?? currentUser?.name}
            </h2>
            <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "12px" }}>
              {currentUser?.departamento} · {currentUser?.programa}
            </p>
            <div className="flex items-center gap-4 mt-3">
              {[
                { v: stats.total, l: "Orientandos" },
                { v: stats.emRisco + stats.prorrogacao, l: "Em Atenção" },
                { v: stats.pendentes, l: "Pendentes" },
              ].map((stat) => (
                <div key={stat.l}>
                  <p style={{ color: "#D4A017", fontSize: "20px", fontWeight: 800, lineHeight: 1 }}>{stat.v}</p>
                  <p style={{ color: "rgba(255,255,255,0.55)", fontSize: "10px", marginTop: "2px" }}>{stat.l}</p>
                </div>
              ))}
            </div>
          </div>
          <QuickBar onAction={(t) => setQuickAction(t)} />
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <KpiCards {...stats} />

      {/* ── Row: Table + Distribution ── */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        <div className="lg:col-span-3">
          <StudentTable onSelect={setSelectedStudent} />
        </div>
        <SituationChart {...stats} />
      </div>

      {/* ── Credit Bar Chart ── */}
      <CreditBarChart />

      {/* ── Work Plan Monitoring ── */}
      <WorkPlanMonitoring onSelect={setSelectedStudent} />

      {/* ── Row: Pending Reviews + Recent Updates ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <PendingReviews />
        <RecentUpdates />
      </div>

      {/* ── Row: Alerts + Attention Students ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <AcademicAlerts />
        <div className="lg:col-span-2">
          <AttentionStudents onSelect={setSelectedStudent} onAction={(t) => setQuickAction(t)} />
        </div>
      </div>

      {/* ── Modals ── */}
      {selectedStudent && (
        <StudentModal student={selectedStudent} onClose={() => setSelectedStudent(null)} />
      )}
      {quickAction && (
        <QuickActionModal type={quickAction} onClose={() => setQuickAction(null)} />
      )}
    </div>
  );
}

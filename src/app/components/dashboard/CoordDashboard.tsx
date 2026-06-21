import React, { useState } from "react";
import { useCoordDashboard } from "@/hooks/useDashboard";
import {
  Users, UserCheck, AlertTriangle, Clock, CheckCircle2, TrendingUp, TrendingDown,
  BookOpen, Award, FileText, Download, X, ChevronRight, Eye,
  BarChart2, Filter, Bell, GraduationCap, Layers, RefreshCw,
  FileSpreadsheet,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
  LineChart, Line, ReferenceLine,
} from "recharts";


type ReportType = "status" | "orientador" | "producao" | "integralizacao" | null;
type ExportFormat = "pdf" | "excel" | "csv";

interface ValidationItem {
  id: string;
  tipo: "relatorio" | "plano" | "producao" | "atividade";
  aluno: string;
  orientador: string;
  descricao: string;
  prazo: string;
  urgencia: "alta" | "media" | "baixa";
  data: string;
}

interface ExtensionRequest {
  id: string;
  aluno: string;
  nivel: "Mestrado" | "Doutorado";
  orientador: string;
  motivo: string;
  prazoPrevisto: string;
  novoPrazo: string;
  status: "pendente" | "em-analise" | "aprovada" | "negada";
  dataProtocolo: string;
}

interface PendingActivity {
  id: string;
  descricao: string;
  responsavel: string;
  tipo: "aprovacao" | "revisao" | "comunicado" | "reuniao";
  prazo: string;
  prioridade: "urgente" | "normal" | "baixa";
}

interface AlertItem {
  id: string;
  nivel: "critico" | "atencao" | "info";
  titulo: string;
  descricao: string;
  afetados: number;
  data: string;
  acao?: string;
}


const INITIAL_STATUS_DATA = [
  { name: "Regular", value: 142, color: "#1F8A70" },
  { name: "Qualificado", value: 38, color: "#123C7A" },
  { name: "Em Risco", value: 24, color: "#D4A017" },
  { name: "Prorrogação", value: 18, color: "#f97316" },
  { name: "Fase de Defesa", value: 16, color: "#8b5cf6" },
];

interface StatusDataProp { name: string; value: number; color: string; }

const ORIENTADOR_DATA = [
  { name: "Carla M.", orientandos: 8, producoes: 14, defesas: 3, risco: 1 },
  { name: "Paulo R.", orientandos: 6, producoes: 9, defesas: 2, risco: 2 },
  { name: "Ana L.", orientandos: 9, producoes: 18, defesas: 4, risco: 0 },
  { name: "João F.", orientandos: 5, producoes: 7, defesas: 1, risco: 2 },
  { name: "Beatriz S.", orientandos: 7, producoes: 11, defesas: 2, risco: 1 },
  { name: "Rafael C.", orientandos: 4, producoes: 5, defesas: 0, risco: 3 },
  { name: "Mariana T.", orientandos: 8, producoes: 16, defesas: 3, risco: 0 },
  { name: "Diego N.", orientandos: 6, producoes: 8, defesas: 1, risco: 2 },
];

const PRODUCAO_DATA = [
  { mes: "Jan", A1: 3, A2: 5, B1: 8, livros: 1, conf: 4 },
  { mes: "Fev", A1: 2, A2: 4, B1: 6, livros: 0, conf: 3 },
  { mes: "Mar", A1: 5, A2: 6, B1: 9, livros: 1, conf: 6 },
  { mes: "Abr", A1: 4, A2: 7, B1: 11, livros: 2, conf: 5 },
  { mes: "Mai", A1: 6, A2: 5, B1: 10, livros: 0, conf: 7 },
  { mes: "Jun", A1: 8, A2: 9, B1: 13, livros: 1, conf: 9 },
  { mes: "Jul", A1: 5, A2: 6, B1: 8, livros: 0, conf: 5 },
  { mes: "Ago", A1: 7, A2: 8, B1: 12, livros: 2, conf: 8 },
  { mes: "Set", A1: 9, A2: 10, B1: 15, livros: 1, conf: 10 },
  { mes: "Out", A1: 11, A2: 12, B1: 17, livros: 3, conf: 11 },
  { mes: "Nov", A1: 8, A2: 9, B1: 14, livros: 1, conf: 9 },
  { mes: "Dez", A1: 6, A2: 7, B1: 11, livros: 0, conf: 7 },
];

const INTEGRALIZACAO_DATA = [
  { ano: "2018", mestrado: 26, doutorado: 50, metaMestrado: 24, metaDoutorado: 48 },
  { ano: "2019", mestrado: 25, doutorado: 52, metaMestrado: 24, metaDoutorado: 48 },
  { ano: "2020", mestrado: 28, doutorado: 54, metaMestrado: 24, metaDoutorado: 48 },
  { ano: "2021", mestrado: 24, doutorado: 49, metaMestrado: 24, metaDoutorado: 48 },
  { ano: "2022", mestrado: 27, doutorado: 51, metaMestrado: 24, metaDoutorado: 48 },
  { ano: "2023", mestrado: 25, doutorado: 48, metaMestrado: 24, metaDoutorado: 48 },
];

const VALIDATIONS: ValidationItem[] = [
  { id: "v1", tipo: "relatorio", aluno: "Carlos Eduardo Lima", orientador: "Profa. Carla Mendes", descricao: "Relatório Semestral 2024-2", prazo: "05/06/2026", urgencia: "alta", data: "28/05/2026" },
  { id: "v2", tipo: "plano", aluno: "Juliana Mendes Martins", orientador: "Prof. Paulo Rodrigues", descricao: "Plano de Trabalho — Fase 3", prazo: "08/06/2026", urgencia: "alta", data: "29/05/2026" },
  { id: "v3", tipo: "producao", aluno: "Ana Paula Costa", orientador: "Profa. Ana Lopes", descricao: "Artigo submetido ao IEEE Access", prazo: "12/06/2026", urgencia: "media", data: "30/05/2026" },
  { id: "v4", tipo: "atividade", aluno: "Ricardo Alves Santos", orientador: "Prof. João Figueiredo", descricao: "Atividade creditável — Workshop IA", prazo: "15/06/2026", urgencia: "media", data: "01/06/2026" },
  { id: "v5", tipo: "relatorio", aluno: "Bruno Carvalho Neves", orientador: "Profa. Beatriz Souza", descricao: "Relatório de Qualificação", prazo: "10/06/2026", urgencia: "alta", data: "01/06/2026" },
  { id: "v6", tipo: "plano", aluno: "Patrícia Lima Farias", orientador: "Prof. Rafael Costa", descricao: "Revisão do Cronograma — Prorrogação", prazo: "20/06/2026", urgencia: "baixa", data: "31/05/2026" },
];

const EXTENSIONS: ExtensionRequest[] = [
  { id: "e1", aluno: "Marcos Vinícius Oliveira", nivel: "Mestrado", orientador: "Profa. Carla Mendes", motivo: "Problemas de saúde documentados", prazoPrevisto: "Dez/2024", novoPrazo: "Jun/2025", status: "em-analise", dataProtocolo: "20/05/2026" },
  { id: "e2", aluno: "Patrícia Lima Farias", nivel: "Doutorado", orientador: "Prof. Rafael Costa", motivo: "Coleta de dados comprometida por pandemia", prazoPrevisto: "Mar/2025", novoPrazo: "Set/2025", status: "pendente", dataProtocolo: "25/05/2026" },
  { id: "e3", aluno: "Diego Almeida Ramos", nivel: "Doutorado", orientador: "Prof. Diego Neri", motivo: "Mudança de escopo aprovada pelo orientador", prazoPrevisto: "Jun/2025", novoPrazo: "Dez/2025", status: "pendente", dataProtocolo: "28/05/2026" },
  { id: "e4", aluno: "Camila Ferreira Luz", nivel: "Mestrado", orientador: "Profa. Mariana Torres", motivo: "Licença maternidade", prazoPrevisto: "Jul/2025", novoPrazo: "Jan/2026", status: "aprovada", dataProtocolo: "10/04/2026" },
];

const PENDING_ACTIVITIES: PendingActivity[] = [
  { id: "p1", descricao: "Aprovar calendário de defesas — 2º semestre 2026", responsavel: "Coordenação", tipo: "aprovacao", prazo: "06/06/2026", prioridade: "urgente" },
  { id: "p2", descricao: "Emitir comunicado sobre prazo de matrículas", responsavel: "Secretaria", tipo: "comunicado", prazo: "07/06/2026", prioridade: "urgente" },
  { id: "p3", descricao: "Revisar regimento interno — Art. 24 e 25", responsavel: "Comissão de Normas", tipo: "revisao", prazo: "15/06/2026", prioridade: "normal" },
  { id: "p4", descricao: "Reunião de colegiado — Pauta: novos orientadores", responsavel: "Todos os docentes", tipo: "reuniao", prazo: "10/06/2026", prioridade: "normal" },
  { id: "p5", descricao: "Aprovar solicitações de bolsas CAPES pendentes (7)", responsavel: "Coordenação", tipo: "aprovacao", prazo: "12/06/2026", prioridade: "urgente" },
  { id: "p6", descricao: "Atualizar Plataforma Sucupira — dados 2025", responsavel: "Secretaria", tipo: "revisao", prazo: "30/06/2026", prioridade: "baixa" },
];

const ALERTS: AlertItem[] = [
  { id: "a1", nivel: "critico", titulo: "Prazos vencidos sem prorrogação aprovada", descricao: "8 alunos ultrapassaram o prazo máximo de integralização sem prorrogação formalizada.", afetados: 8, data: "02/06/2026", acao: "Ver alunos" },
  { id: "a2", nivel: "critico", titulo: "Relatórios semestrais em atraso", descricao: "12 relatórios do período 2024-2 não foram entregues até a data limite.", afetados: 12, data: "01/06/2026", acao: "Notificar alunos" },
  { id: "a3", nivel: "atencao", titulo: "Bolsas com expiração iminente", descricao: "6 bolsas CAPES/CNPq vencem nos próximos 30 dias e precisam de renovação.", afetados: 6, data: "02/06/2026", acao: "Processar renovações" },
  { id: "a4", nivel: "atencao", titulo: "Orientadores com sobrecarga", descricao: "3 orientadores estão acima do limite recomendado de 8 orientandos simultâneos.", afetados: 3, data: "30/05/2026", acao: "Redistribuir orientações" },
  { id: "a5", nivel: "info", titulo: "Avaliação CAPES — Prazo para envio de dados", descricao: "O prazo para envio dos dados da avaliação quadrienal é 30/07/2026.", afetados: 0, data: "28/05/2026" },
  { id: "a6", nivel: "info", titulo: "Novo edital de bolsas produtividade CNPq", descricao: "Edital aberto para bolsas PQ 2026. Prazo de inscrição: 15/07/2026.", afetados: 0, data: "29/05/2026" },
];

const PROGRAM_STATS = [
  { label: "Taxa de Titulação (5 anos)", value: "78%", sub: "Acima da média nacional (71%)", trend: "up", color: "#1F8A70" },
  { label: "Nota CAPES", value: "6", sub: "Mantida na última avaliação (2021-2024)", trend: "stable", color: "#123C7A" },
  { label: "Índice H do Programa", value: "24", sub: "+3 em relação ao triênio anterior", trend: "up", color: "#8b5cf6" },
  { label: "Produção Média / Aluno", value: "1,8", sub: "Artigos Qualis A1/A2 por aluno/ano", trend: "up", color: "#D4A017" },
  { label: "Orientadores Ativos", value: "42", sub: "32 doutores · 10 colaboradores", trend: "stable", color: "#123C7A" },
  { label: "Taxa de Evasão (12 meses)", value: "4,2%", sub: "-1,1 p.p. em relação ao ano anterior", trend: "down-good", color: "#1F8A70" },
];


const URGENCIA_CFG = {
  alta: { label: "Alta", color: "#dc2626", bg: "#fef2f2" },
  media: { label: "Média", color: "#D4A017", bg: "#fffbeb" },
  baixa: { label: "Baixa", color: "#1F8A70", bg: "#f0fdf4" },
};

const TIPO_CFG: Record<ValidationItem["tipo"], { label: string; color: string; icon: React.ReactNode }> = {
  relatorio: { label: "Relatório", color: "#123C7A", icon: <FileText size={13} /> },
  plano: { label: "Plano", color: "#8b5cf6", icon: <Layers size={13} /> },
  producao: { label: "Produção", color: "#1F8A70", icon: <Award size={13} /> },
  atividade: { label: "Atividade", color: "#D4A017", icon: <BookOpen size={13} /> },
};

const EXT_STATUS_CFG = {
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fffbeb" },
  "em-analise": { label: "Em Análise", color: "#123C7A", bg: "#eef3fc" },
  aprovada: { label: "Aprovada", color: "#1F8A70", bg: "#f0fdf4" },
  negada: { label: "Negada", color: "#dc2626", bg: "#fef2f2" },
};

const ALERT_CFG = {
  critico: { color: "#dc2626", bg: "#fef2f2", border: "#fecaca", icon: <AlertTriangle size={16} /> },
  atencao: { color: "#D4A017", bg: "#fffbeb", border: "#fde68a", icon: <Bell size={16} /> },
  info: { color: "#123C7A", bg: "#eef3fc", border: "#c7d9f5", icon: <Bell size={16} /> },
};

const ACTIVITY_TIPO_CFG: Record<PendingActivity["tipo"], { color: string; bg: string; label: string }> = {
  aprovacao: { color: "#123C7A", bg: "#eef3fc", label: "Aprovação" },
  revisao: { color: "#8b5cf6", bg: "#f5f3ff", label: "Revisão" },
  comunicado: { color: "#D4A017", bg: "#fffbeb", label: "Comunicado" },
  reuniao: { color: "#1F8A70", bg: "#f0fdf4", label: "Reunião" },
};

const PRIORITY_CFG = {
  urgente: { color: "#dc2626", label: "Urgente" },
  normal: { color: "#D4A017", label: "Normal" },
  baixa: { color: "#64748b", label: "Baixa" },
};

function handleExport(format: ExportFormat, section: string) {
  const msg = `Exportando ${section} como ${format.toUpperCase()}...`;
  const el = document.createElement("div");
  el.textContent = msg;
  Object.assign(el.style, {
    position: "fixed", bottom: "24px", right: "24px", zIndex: "9999",
    background: "#123C7A", color: "#fff", padding: "12px 20px",
    borderRadius: "12px", fontSize: "13px", fontWeight: "600",
    boxShadow: "0 8px 24px rgba(0,0,0,0.2)", transition: "opacity 0.3s",
  });
  document.body.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; }, 1800);
  setTimeout(() => { document.body.removeChild(el); }, 2100);
}


function KpiCard({ icon, label, value, sub, color, trend }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; color: string; trend?: "up" | "down" | "down-good" | "stable";
}) {
  const trendEl = trend && trend !== "stable" ? (
    <div
      className="flex items-center gap-1 px-2 py-0.5 rounded-lg"
      style={{ background: (trend === "up" || trend === "down-good") ? "#dcfce7" : "#fef2f2" }}
    >
      {(trend === "up" || trend === "down-good")
        ? <TrendingUp size={11} style={{ color: "#1F8A70" }} />
        : <TrendingDown size={11} style={{ color: "#dc2626" }} />}
      <span style={{ fontSize: "10px", fontWeight: 700, color: (trend === "up" || trend === "down-good") ? "#1F8A70" : "#dc2626" }}>
        {trend === "up" ? "↑" : "↓"}
      </span>
    </div>
  ) : null;

  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
      <div className="flex items-start justify-between mb-3">
        <div className="rounded-xl flex items-center justify-center" style={{ width: 42, height: 42, background: `${color}18` }}>
          <span style={{ color }}>{icon}</span>
        </div>
        {trendEl}
      </div>
      <p style={{ fontSize: "22px", fontWeight: 800, color: "var(--foreground)", lineHeight: 1 }} className="md:text-[28px]">{value}</p>
      <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)", marginTop: "4px" }}>{label}</p>
      {sub && <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "2px" }}>{sub}</p>}
    </div>
  );
}

function ExportBar({ section }: { section: string }) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap badge-shrink">
      {(["pdf", "excel", "csv"] as ExportFormat[]).map((fmt) => (
        <button
          key={fmt}
          onClick={() => handleExport(fmt, section)}
          title={`Exportar ${fmt.toUpperCase()}`}
          aria-label={`Exportar ${fmt.toUpperCase()}`}
          className="flex items-center gap-1 px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-lg transition-opacity hover:opacity-80 flex-shrink-0"
          style={{
            background: fmt === "pdf" ? "var(--tint-danger-bg)" : fmt === "excel" ? "var(--tint-teal-bg)" : "var(--muted)",
            color: fmt === "pdf" ? "var(--tint-danger-text)" : fmt === "excel" ? "var(--tint-teal-text)" : "var(--muted-foreground)",
            fontSize: "10px", fontWeight: 700, border: `1px solid ${fmt === "pdf" ? "var(--tint-danger-border)" : fmt === "excel" ? "var(--tint-teal-border)" : "var(--border)"}`,
          }}
        >
          {fmt === "pdf" ? <FileText size={11} /> : fmt === "excel" ? <FileSpreadsheet size={11} /> : <Download size={11} />}
          <span className="hidden sm:inline">{fmt.toUpperCase()}</span>
        </button>
      ))}
    </div>
  );
}

function SectionHeader({ title, sub, section, onReport }: {
  title: string; sub?: string; section: string; onReport?: () => void;
}) {
  return (
    <div className="flex flex-col gap-2 mb-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)", wordBreak: "break-word" }}>{title}</h3>
        {sub && <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "1px" }}>{sub}</p>}
      </div>
      <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
        <ExportBar section={section} />
        {onReport && (
          <button
            onClick={onReport}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:opacity-80 transition-opacity"
            style={{ background: "#eef3fc", color: "#123C7A", fontSize: "10px", fontWeight: 700, border: "1px solid #c7d9f5", whiteSpace: "nowrap" }}
          >
            <BarChart2 size={10} /> Relatório
          </button>
        )}
      </div>
    </div>
  );
}


function ReportModal({ type, onClose, statusData }: { type: ReportType; onClose: () => void; statusData: StatusDataProp[] }) {
  if (!type) return null;

  const configs: Record<Exclude<ReportType, null>, { title: string; sub: string; content: React.ReactNode }> = {
    status: {
      title: "Relatório — Distribuição de Status",
      sub: "Panorama completo da situação acadêmica dos alunos ativos",
      content: (
        <div className="space-y-4">
          <div className="flex justify-center">
            <PieChart width={260} height={220}>
              <Pie data={statusData} cx={125} cy={105} innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value" isAnimationActive={false}>
                {statusData.map((d, i) => <Cell key={`modal-status-${i}`} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v: number) => [`${v} alunos`, ""]} contentStyle={{ borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </div>
          <div className="space-y-2">
            {statusData.map((s) => {
              const totalAlunos = Math.max(1, statusData.reduce((acc, d) => acc + d.value, 0));
              return (
              <div key={s.name} className="flex items-center justify-between p-2.5 rounded-xl" style={{ background: `${s.color}0d` }}>
                <div className="flex items-center gap-2">
                  <div className="rounded-full" style={{ width: 10, height: 10, background: s.color }} />
                  <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{s.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-full overflow-hidden" style={{ width: 80, height: 6, background: "var(--muted)" }}>
                    <div className="h-full rounded-full" style={{ width: `${(s.value / totalAlunos) * 100}%`, background: s.color }} />
                  </div>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: s.color, minWidth: 60, textAlign: "right" }}>
                    {s.value} ({((s.value / totalAlunos) * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
            )})}
          </div>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)", textAlign: "center", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
            Total: {statusData.reduce((acc, d) => acc + d.value, 0)} alunos matriculados · Programa PPGCC
          </p>
        </div>
      ),
    },
    orientador: {
      title: "Relatório — Desempenho dos Orientadores",
      sub: "Métricas de orientação, produção e situação dos orientandos",
      content: (
        <div className="space-y-4">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={ORIENTADOR_DATA} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} width={60} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="orientandos" name="Orientandos" fill="#123C7A" radius={[0, 4, 4, 0]} barSize={6} isAnimationActive={false} />
              <Bar dataKey="producoes" name="Produções" fill="#1F8A70" radius={[0, 4, 4, 0]} barSize={6} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {ORIENTADOR_DATA.map((o) => (
              <div key={o.name} className="flex items-center justify-between p-2.5 rounded-xl" style={{ background: "var(--muted)" }}>
                <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--foreground)" }}>{o.name}</span>
                <div className="flex items-center gap-3" style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>
                  <span><span style={{ fontWeight: 700, color: "#123C7A" }}>{o.orientandos}</span> orient.</span>
                  <span><span style={{ fontWeight: 700, color: "#1F8A70" }}>{o.producoes}</span> prod.</span>
                  <span><span style={{ fontWeight: 700, color: "#D4A017" }}>{o.defesas}</span> defesas</span>
                  {o.risco > 0 && <span style={{ color: "#dc2626", fontWeight: 700 }}>{o.risco} risco</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    producao: {
      title: "Relatório — Produção Científica",
      sub: "Artigos, livros e conferências por mês em 2026",
      content: (
        <div className="space-y-4">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={PRODUCAO_DATA}>
              <defs>
                <linearGradient id="gA1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#123C7A" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#123C7A" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gA2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1F8A70" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1F8A70" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="mes" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="A1" name="Qualis A1" stroke="#123C7A" fill="url(#gA1)" strokeWidth={2} isAnimationActive={false} />
              <Area type="monotone" dataKey="A2" name="Qualis A2" stroke="#1F8A70" fill="url(#gA2)" strokeWidth={2} isAnimationActive={false} />
              <Area type="monotone" dataKey="conf" name="Conferências" stroke="#D4A017" fill="none" strokeWidth={1.5} strokeDasharray="4 4" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {[
              { label: "Total A1", value: 74, color: "#123C7A" },
              { label: "Total A2", value: 88, color: "#1F8A70" },
              { label: "Conferências", value: 84, color: "#D4A017" },
              { label: "B1", value: 124, color: "#8b5cf6" },
              { label: "Livros", value: 12, color: "#f97316" },
              { label: "Média/Aluno", value: "1,8", color: "#123C7A" },
            ].map((s) => (
              <div key={s.label} className="rounded-xl p-3 text-center" style={{ background: `${s.color}0d`, border: `1px solid ${s.color}22` }}>
                <p style={{ fontSize: "20px", fontWeight: 800, color: s.color }}>{s.value}</p>
                <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "2px" }}>{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    integralizacao: {
      title: "Relatório — Integralização por Ano",
      sub: "Tempo médio de conclusão comparado à meta do programa",
      content: (
        <div className="space-y-4">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={INTEGRALIZACAO_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="ano" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
              <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} domain={[20, 60]} unit=" m" />
              <Tooltip formatter={(v: number) => [`${v} meses`, ""]} contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <ReferenceLine y={24} stroke="#123C7A" strokeDasharray="4 4" label={{ value: "Meta M", fill: "#123C7A", fontSize: 10 }} />
              <ReferenceLine y={48} stroke="#8b5cf6" strokeDasharray="4 4" label={{ value: "Meta D", fill: "#8b5cf6", fontSize: 10 }} />
              <Bar dataKey="mestrado" name="Mestrado (meses)" fill="#123C7A" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="doutorado" name="Doutorado (meses)" fill="#8b5cf6" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
          <div className="space-y-2">
            {INTEGRALIZACAO_DATA.map((d) => (
              <div key={d.ano} className="flex items-center justify-between p-2.5 rounded-xl" style={{ background: "var(--muted)" }}>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--foreground)" }}>{d.ano}</span>
                <div className="flex items-center gap-4">
                  <span style={{ fontSize: "12px" }}>
                    <span style={{ color: "var(--muted-foreground)" }}>Mestrado: </span>
                    <span style={{ fontWeight: 700, color: d.mestrado > d.metaMestrado ? "#dc2626" : "#1F8A70" }}>{d.mestrado}m</span>
                  </span>
                  <span style={{ fontSize: "12px" }}>
                    <span style={{ color: "var(--muted-foreground)" }}>Doutorado: </span>
                    <span style={{ fontWeight: 700, color: d.doutorado > d.metaDoutorado ? "#dc2626" : "#1F8A70" }}>{d.doutorado}m</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      ),
    },
  };

  const cfg = configs[type];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "var(--modal-overlay)", backdropFilter: "blur(4px)" }}
      onClick={onClose}
    >
      <div
        className="rounded-2xl w-full mx-3 md:mx-0 max-w-lg max-h-[92vh] overflow-y-auto"
        style={{ background: "var(--card)", border: "1px solid var(--border)", boxShadow: "var(--elevation-card-shadow)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between p-5 pb-0">
          <div>
            <h2 style={{ fontSize: "16px", fontWeight: 800, color: "var(--foreground)" }}>{cfg.title}</h2>
            <p style={{ fontSize: "12px", color: "var(--muted-foreground)", marginTop: "2px" }}>{cfg.sub}</p>
          </div>
          <button onClick={onClose} className="rounded-xl p-1.5 hover:opacity-70 transition-opacity" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}>
            <X size={16} />
          </button>
        </div>
        <div className="p-5">
          {cfg.content}
          <div className="flex items-center gap-2 mt-4 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
            <span style={{ fontSize: "12px", color: "var(--muted-foreground)", marginRight: "auto" }}>Exportar relatório:</span>
            <ExportBar section={cfg.title} />
          </div>
        </div>
      </div>
    </div>
  );
}


function StatusDistribChart({ onReport, statusData }: { onReport: () => void; statusData: StatusDataProp[] }) {
  const total = Math.max(1, statusData.reduce((s, d) => s + d.value, 0));
  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SectionHeader title="Distribuição de Status" sub={`Situação acadêmica — ${total} alunos`} section="Status" onReport={onReport} />
      <div className="flex items-center gap-4">
        <div style={{ flexShrink: 0 }}>
          <PieChart width={160} height={160}>
            <Pie data={statusData} cx={75} cy={75} innerRadius={48} outerRadius={72} paddingAngle={2} dataKey="value" isAnimationActive={false}>
              {statusData.map((d, i) => <Cell key={`status-cell-${i}`} fill={d.color} />)}
            </Pie>
            <Tooltip formatter={(v: number) => [`${v} alunos`, ""]} contentStyle={{ borderRadius: 8, fontSize: 11 }} />
          </PieChart>
        </div>
        <div className="flex-1 space-y-2">
          {statusData.map((s) => (
            <div key={s.name} className="flex items-center gap-2">
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.color, flexShrink: 0 }} />
              <span style={{ fontSize: "12px", color: "var(--foreground)", flex: 1 }}>{s.name}</span>
              <div className="rounded-full overflow-hidden" style={{ width: 60, height: 5, background: "var(--muted)" }}>
                <div className="h-full rounded-full" style={{ width: `${(s.value / total) * 100}%`, background: s.color }} />
              </div>
              <span style={{ fontSize: "12px", fontWeight: 700, color: s.color, minWidth: 28, textAlign: "right" }}>{s.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function OrientadorPerfChart({ onReport }: { onReport: () => void }) {
  return (
    <div className="rounded-2xl p-4 md:p-5 overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SectionHeader title="Desempenho dos Orientadores" sub="Orientandos, produções e defesas" section="Orientadores" onReport={onReport} />
      <div className="overflow-x-auto -mx-1">
      <div style={{ minWidth: 320 }}>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={ORIENTADOR_DATA} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid key="op-grid" strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis key="op-x" dataKey="name" tick={{ fontSize: 9, fill: "var(--muted-foreground)" }} interval={0} />
          <YAxis key="op-y" width={28} tick={{ fontSize: 9, fill: "var(--muted-foreground)" }} />
          <Tooltip key="op-tip" contentStyle={{ borderRadius: 8, fontSize: 11 }} />
          <Legend key="op-leg" iconSize={8} iconType="circle" wrapperStyle={{ fontSize: 10 }} />
          <Bar key="op-b1" dataKey="orientandos" name="Orientandos" fill="#123C7A" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar key="op-b2" dataKey="producoes" name="Produções" fill="#1F8A70" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar key="op-b3" dataKey="defesas" name="Defesas" fill="#D4A017" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          <Bar key="op-b4" dataKey="risco" name="Em Risco" fill="#dc2626" radius={[3, 3, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      </div>
      </div>
    </div>
  );
}

function ProducaoChart({ onReport }: { onReport: () => void }) {
  return (
    <div className="rounded-2xl p-4 md:p-5 overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SectionHeader title="Produção Científica" sub="Qualis A1, A2 e conferências — 2026" section="Produção Científica" onReport={onReport} />
      <div className="overflow-x-auto -mx-1">
      <div style={{ minWidth: 300 }}>
      <ResponsiveContainer width="100%" height={190}>
        <AreaChart data={PRODUCAO_DATA} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
          <defs key="pr-defs">
            <linearGradient key="pr-g1" id="pGA1" x1="0" y1="0" x2="0" y2="1">
              <stop key="s1a" offset="5%" stopColor="#123C7A" stopOpacity={0.25} />
              <stop key="s1b" offset="95%" stopColor="#123C7A" stopOpacity={0} />
            </linearGradient>
            <linearGradient key="pr-g2" id="pGA2" x1="0" y1="0" x2="0" y2="1">
              <stop key="s2a" offset="5%" stopColor="#1F8A70" stopOpacity={0.25} />
              <stop key="s2b" offset="95%" stopColor="#1F8A70" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid key="pr-grid" strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis key="pr-x" dataKey="mes" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <YAxis key="pr-y" width={28} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <Tooltip key="pr-tip" contentStyle={{ borderRadius: 8, fontSize: 11 }} />
          <Legend key="pr-leg" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Area key="pr-a1" type="monotone" dataKey="A1" name="Qualis A1" stroke="#123C7A" fill="url(#pGA1)" strokeWidth={2} isAnimationActive={false} />
          <Area key="pr-a2" type="monotone" dataKey="A2" name="Qualis A2" stroke="#1F8A70" fill="url(#pGA2)" strokeWidth={2} isAnimationActive={false} />
          <Area key="pr-a3" type="monotone" dataKey="conf" name="Conferências" stroke="#D4A017" fill="none" strokeWidth={1.5} strokeDasharray="4 4" isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
      </div>
      </div>
    </div>
  );
}

function IntegralizacaoChart({ onReport }: { onReport: () => void }) {
  return (
    <div className="rounded-2xl p-4 md:p-5 overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SectionHeader title="Integralização por Ano" sub="Tempo médio em meses vs. meta do programa" section="Integralização" onReport={onReport} />
      <div className="overflow-x-auto -mx-1">
      <div style={{ minWidth: 280 }}>
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={INTEGRALIZACAO_DATA} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid key="in-grid" strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis key="in-x" dataKey="ano" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis key="in-y" width={32} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} domain={[20, 60]} unit="m" />
          <Tooltip key="in-tip" formatter={(v: number) => [`${v} meses`, ""]} contentStyle={{ borderRadius: 8, fontSize: 11 }} />
          <Legend key="in-leg" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <ReferenceLine key="in-rl1" y={24} stroke="#123C7A" strokeDasharray="4 4" strokeWidth={1.5} />
          <ReferenceLine key="in-rl2" y={48} stroke="#8b5cf6" strokeDasharray="4 4" strokeWidth={1.5} />
          <Bar key="in-b1" dataKey="mestrado" name="Mestrado" fill="#123C7A" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Bar key="in-b2" dataKey="doutorado" name="Doutorado" fill="#8b5cf6" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
      </div>
      </div>
    </div>
  );
}


function ValidationQueue() {
  const [filter, setFilter] = useState<"todos" | ValidationItem["tipo"] | "alta">("todos");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = VALIDATIONS.filter((v) => {
    if (filter === "todos") return true;
    if (filter === "alta") return v.urgencia === "alta";
    return v.tipo === filter;
  });

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Fila de Validação</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{VALIDATIONS.length} itens aguardando aprovação</p>
        </div>
        <ExportBar section="Fila de Validação" />
      </div>

      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {(["todos", "alta", "relatorio", "plano", "producao", "atividade"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="px-3 py-1 rounded-lg transition-all"
            style={{
              fontSize: "11px", fontWeight: 600,
              background: filter === f ? "var(--primary)" : "var(--muted)",
              color: filter === f ? "var(--primary-foreground)" : "var(--muted-foreground)",
              border: `1px solid ${filter === f ? "var(--primary)" : "var(--border)"}`,
            }}
          >
            {f === "todos" ? "Todos" : f === "alta" ? "⚡ Urgente" : TIPO_CFG[f as ValidationItem["tipo"]].label}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.map((v) => {
          const tc = TIPO_CFG[v.tipo];
          const uc = URGENCIA_CFG[v.urgencia];
          const isOpen = expanded === v.id;
          return (
            <div
              key={v.id}
              className="rounded-xl overflow-hidden"
              style={{ border: `1px solid ${isOpen ? "var(--primary)" : "var(--border)"}`, background: isOpen ? "var(--tint-blue-bg)" : "var(--muted)" }}
            >
              <button
                className="w-full flex items-center gap-3 p-3 text-left"
                onClick={() => setExpanded(isOpen ? null : v.id)}
              >
                <span style={{ color: tc.color, flexShrink: 0 }}>{tc.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--foreground)" }}>{v.aluno}</span>
                    <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: `${tc.color}18`, color: tc.color }}>{tc.label}</span>
                    <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: uc.bg, color: uc.color }}>{uc.label}</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "1px" }}>{v.descricao}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Prazo</p>
                  <p style={{ fontSize: "11px", fontWeight: 700, color: v.urgencia === "alta" ? "var(--tint-danger-text)" : "var(--foreground)" }}>{v.prazo}</p>
                </div>
                <ChevronRight size={14} style={{ color: "var(--muted-foreground)", transform: isOpen ? "rotate(90deg)" : undefined, transition: "transform 0.2s", flexShrink: 0 }} />
              </button>
              {isOpen && (
                <div className="px-4 pb-4 pt-0">
                  <div className="rounded-xl p-3 space-y-2" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                    <div className="grid grid-cols-2 gap-2" style={{ fontSize: "12px" }}>
                      <div><span style={{ color: "var(--muted-foreground)" }}>Orientador: </span><span style={{ fontWeight: 600, color: "var(--foreground)" }}>{v.orientador}</span></div>
                      <div><span style={{ color: "var(--muted-foreground)" }}>Enviado em: </span><span style={{ fontWeight: 600, color: "var(--foreground)" }}>{v.data}</span></div>
                    </div>
                    <div className="flex gap-2 mt-3">
                      <button className="flex-1 py-2 rounded-xl" style={{ background: "var(--tint-teal-text)", color: "#fff", fontSize: "12px", fontWeight: 700 }}>
                        <CheckCircle2 size={13} style={{ display: "inline", marginRight: 4 }} />Aprovar
                      </button>
                      <button className="flex-1 py-2 rounded-xl" style={{ background: "var(--tint-danger-bg)", color: "var(--tint-danger-text)", fontSize: "12px", fontWeight: 700, border: "1px solid var(--tint-danger-border)" }}>
                        Devolver
                      </button>
                      <button className="px-3 py-2 rounded-xl" style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "12px", fontWeight: 700, border: "1px solid var(--border)" }}>
                        <Eye size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ExtensionRequestsSection() {
  const [filterStatus, setFilterStatus] = useState<ExtensionRequest["status"] | "todos">("todos");
  const filtered = EXTENSIONS.filter((e) => filterStatus === "todos" || e.status === filterStatus);

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Solicitações de Prorrogação</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{EXTENSIONS.filter(e => e.status === "pendente" || e.status === "em-analise").length} pendentes de decisão</p>
        </div>
        <ExportBar section="Prorrogações" />
      </div>

      <div className="flex items-center gap-2 mb-4">
        {(["todos", "pendente", "em-analise", "aprovada", "negada"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className="px-2.5 py-1 rounded-lg transition-all"
            style={{
              fontSize: "10px", fontWeight: 600,
              background: filterStatus === s ? "var(--primary)" : "var(--muted)",
              color: filterStatus === s ? "var(--primary-foreground)" : "var(--muted-foreground)",
              border: `1px solid ${filterStatus === s ? "var(--primary)" : "var(--border)"}`,
            }}
          >
            {s === "todos" ? "Todos" : EXT_STATUS_CFG[s].label}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map((ext) => {
          const sc = EXT_STATUS_CFG[ext.status];
          return (
            <div key={ext.id} className="rounded-xl p-4" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--foreground)" }}>{ext.aluno}</span>
                    <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: ext.nivel === "Doutorado" ? "var(--tint-blue-bg)" : "var(--tint-violet-bg)", color: ext.nivel === "Doutorado" ? "var(--tint-blue-text)" : "var(--tint-violet-text)", border: `1px solid ${ext.nivel === "Doutorado" ? "var(--tint-blue-border)" : "var(--tint-violet-border)"}` }}>
                      {ext.nivel}
                    </span>
                    <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: sc.bg, color: sc.color }}>{sc.label}</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "2px" }}>Orient.: {ext.orientador}</p>
                </div>
                <span style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Protocolo: {ext.dataProtocolo}</span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--foreground)", marginBottom: "8px" }}><span style={{ color: "var(--muted-foreground)" }}>Motivo: </span>{ext.motivo}</p>
              <div className="flex items-center gap-4" style={{ fontSize: "11px" }}>
                <span><span style={{ color: "var(--muted-foreground)" }}>Prazo atual: </span><span style={{ fontWeight: 700, color: "var(--tint-danger-text)" }}>{ext.prazoPrevisto}</span></span>
                <ChevronRight size={12} style={{ color: "var(--muted-foreground)" }} />
                <span><span style={{ color: "var(--muted-foreground)" }}>Novo prazo: </span><span style={{ fontWeight: 700, color: "var(--tint-teal-text)" }}>{ext.novoPrazo}</span></span>
              </div>
              {(ext.status === "pendente" || ext.status === "em-analise") && (
                <div className="flex gap-2 mt-3">
                  <button className="px-4 py-1.5 rounded-lg" style={{ background: "var(--tint-teal-text)", color: "#fff", fontSize: "11px", fontWeight: 700 }}>Aprovar</button>
                  <button className="px-4 py-1.5 rounded-lg" style={{ background: "var(--tint-danger-bg)", color: "var(--tint-danger-text)", fontSize: "11px", fontWeight: 700, border: "1px solid var(--tint-danger-border)" }}>Negar</button>
                  <button className="px-4 py-1.5 rounded-lg" style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "11px", fontWeight: 700, border: "1px solid var(--border)" }}>Solicitar Docs</button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PendingActivitiesSection() {
  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Atividades Pendentes</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{PENDING_ACTIVITIES.filter(a => a.prioridade === "urgente").length} urgentes · {PENDING_ACTIVITIES.length} total</p>
        </div>
        <ExportBar section="Atividades Pendentes" />
      </div>
      <div className="space-y-2">
        {PENDING_ACTIVITIES.sort((a, b) => {
          const order = { urgente: 0, normal: 1, baixa: 2 };
          return order[a.prioridade] - order[b.prioridade];
        }).map((act) => {
          const tc = ACTIVITY_TIPO_CFG[act.tipo];
          const pc = PRIORITY_CFG[act.prioridade];
          return (
            <div key={act.id} className="flex items-center gap-3 p-3 rounded-xl" style={{ background: act.prioridade === "urgente" ? "var(--tint-danger-bg)" : "var(--muted)", border: `1px solid ${act.prioridade === "urgente" ? "var(--tint-danger-border)" : "var(--border)"}` }}>
              <div className="rounded-lg p-1.5" style={{ background: tc.bg, color: tc.color, flexShrink: 0 }}>
                <RefreshCw size={12} />
              </div>
              <div className="flex-1 min-w-0">
                <p style={{ fontSize: "12px", fontWeight: 600, color: act.prioridade === "urgente" ? "var(--tint-danger-text)" : "var(--foreground)" }}>{act.descricao}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: tc.bg, color: tc.color }}>{tc.label}</span>
                  <span style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>{act.responsavel}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <p style={{ fontSize: "10px", fontWeight: 700, color: pc.color }}>{pc.label}</p>
                <p style={{ fontSize: "11px", color: "var(--muted-foreground)" }}>Até {act.prazo}</p>
              </div>
              <button className="px-3 py-1.5 rounded-lg flex-shrink-0" style={{ background: "var(--primary)", color: "var(--primary-foreground)", fontSize: "11px", fontWeight: 700 }}>
                Agir
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AlertsCenter() {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? ALERTS : ALERTS.slice(0, 4);

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Central de Alertas</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>
            <span style={{ color: "var(--tint-danger-text)", fontWeight: 700 }}>{ALERTS.filter(a => a.nivel === "critico").length} críticos</span>
            {" · "}{ALERTS.filter(a => a.nivel === "atencao").length} atenção · {ALERTS.filter(a => a.nivel === "info").length} informativos
          </p>
        </div>
        <ExportBar section="Alertas" />
      </div>
      <div className="space-y-2">
        {visible.map((alert) => {
          const ac = ALERT_CFG[alert.nivel];
          return (
            <div key={alert.id} className="rounded-xl p-3.5" style={{ background: ac.bg, borderLeft: `3px solid ${ac.color}`, border: `1px solid ${ac.border}` }}>
              <div className="flex items-start gap-2.5">
                <span style={{ color: ac.color, flexShrink: 0, marginTop: 1 }}>{ac.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p style={{ fontSize: "13px", fontWeight: 700, color: "var(--foreground)" }}>{alert.titulo}</p>
                    <span style={{ fontSize: "10px", color: "var(--muted-foreground)", flexShrink: 0, marginLeft: 8 }}>{alert.data}</span>
                  </div>
                  <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "2px", lineHeight: 1.5 }}>{alert.descricao}</p>
                  <div className="flex items-center gap-3 mt-2">
                    {alert.afetados > 0 && (
                      <span className="px-2 py-0.5 rounded-lg" style={{ fontSize: "10px", fontWeight: 700, background: `${ac.color}18`, color: ac.color }}>
                        {alert.afetados} afetado{alert.afetados !== 1 ? "s" : ""}
                      </span>
                    )}
                    {alert.acao && (
                      <button style={{ fontSize: "11px", fontWeight: 700, color: ac.color, textDecoration: "underline" }}>
                        {alert.acao} →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {ALERTS.length > 4 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="w-full mt-3 py-2 rounded-xl transition-opacity hover:opacity-80"
          style={{ background: "var(--muted)", color: "var(--muted-foreground)", fontSize: "12px", fontWeight: 600, border: "1px solid var(--border)" }}
        >
          {showAll ? "Mostrar menos" : `Ver mais ${ALERTS.length - 4} alertas`}
        </button>
      )}
    </div>
  );
}

function ProgramStatistics() {
  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Estatísticas do Programa</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>PPGCC · Avaliação 2026 · Nota CAPES 6</p>
        </div>
        <ExportBar section="Estatísticas do Programa" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {PROGRAM_STATS.map((s) => (
          <div key={s.label} className="rounded-xl p-4" style={{ background: `${s.color}0a`, border: `1px solid ${s.color}22` }}>
            <div className="flex items-center justify-between mb-1">
              <p style={{ fontSize: "24px", fontWeight: 800, color: s.color }}>{s.value}</p>
              {s.trend === "up" && <TrendingUp size={16} style={{ color: "#1F8A70" }} />}
              {s.trend === "down-good" && <TrendingDown size={16} style={{ color: "#1F8A70" }} />}
              {s.trend === "stable" && <div style={{ width: 16, height: 2, background: "#64748b", borderRadius: 1 }} />}
            </div>
            <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--foreground)" }}>{s.label}</p>
            <p style={{ fontSize: "10px", color: "var(--muted-foreground)", marginTop: "2px", lineHeight: 1.4 }}>{s.sub}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl p-4" style={{ background: "linear-gradient(135deg, #123C7A 0%, #1F5FAA 100%)" }}>
        <div className="flex items-center justify-between">
          <div>
            <p style={{ fontSize: "13px", fontWeight: 800, color: "#fff" }}>Avaliação CAPES 2025–2028</p>
            <p style={{ fontSize: "11px", color: "rgba(255,255,255,0.75)", marginTop: "2px" }}>Próxima avaliação — Envio de dados: 30/07/2026</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-center">
              <p style={{ fontSize: "28px", fontWeight: 900, color: "#fff", lineHeight: 1 }}>6</p>
              <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>Nota atual</p>
            </div>
            <ChevronRight size={18} style={{ color: "rgba(255,255,255,0.6)" }} />
            <div className="text-center">
              <p style={{ fontSize: "28px", fontWeight: 900, color: "#D4A017", lineHeight: 1 }}>7</p>
              <p style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>Meta 2028</p>
            </div>
          </div>
        </div>
        <div className="mt-3">
          <div className="flex justify-between mb-1" style={{ fontSize: "10px", color: "rgba(255,255,255,0.7)" }}>
            <span>Progresso em direção à nota 7</span><span>68%</span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height: 6, background: "rgba(255,255,255,0.2)" }}>
            <div className="h-full rounded-full" style={{ width: "68%", background: "#D4A017" }} />
          </div>
        </div>
      </div>
    </div>
  );
}


export function CoordDashboard() {
  const { data: dashData, loading, error } = useCoordDashboard();
  const [reportModal, setReportModal] = useState<ReportType>(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 400 }}>
        <div className="text-center">
          <div className="animate-spin rounded-full border-4 border-t-transparent" style={{ width: 40, height: 40, borderColor: "var(--border)", borderTopColor: "transparent" }} />
          <p style={{ fontSize: "14px", color: "var(--muted-foreground)", marginTop: 16 }}>Carregando dashboard da coordenação...</p>
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

  let statusData = INITIAL_STATUS_DATA;
  if (dashData?.alunos_por_status) {
    statusData = [
      { name: "Regular", value: dashData.alunos_por_status.regular, color: "#1F8A70" },
      { name: "Qualificado", value: dashData.alunos_por_status.qualificado, color: "#123C7A" },
      { name: "Em Risco", value: dashData.alunos_por_status.em_risco, color: "#D4A017" },
      { name: "Prorrogação", value: dashData.alunos_por_status.em_prorrogacao, color: "#f97316" },
      { name: "Fase de Defesa", value: dashData.alunos_por_status.fase_defesa, color: "#8b5cf6" },
    ].filter(s => s.value > 0);
  }

  const ativos = dashData?.total_alunos_ativos ?? statusData.reduce((s, d) => s + d.value, 0);
  const emRisco = dashData?.alunos_por_status?.em_risco ?? 0;
  const emProrrogacao = dashData?.alunos_por_status?.em_prorrogacao ?? 0;
  const concluidos = dashData?.total_concluidos ?? 0;

  return (
    <div className="space-y-5">
      {/* Welcome Banner */}
      <div className="rounded-2xl p-4 md:p-5" style={{ background: "linear-gradient(135deg, #123C7A 0%, #1a4f9e 50%, #1F8A70 100%)" }}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <GraduationCap size={18} style={{ color: "rgba(255,255,255,0.85)" }} />
              <span style={{ fontSize: "11px", fontWeight: 600, color: "rgba(255,255,255,0.75)" }}>PPGCC · Coordenação</span>
            </div>
            <h2 style={{ fontSize: "clamp(16px,4vw,22px)", fontWeight: 800, color: "#fff", lineHeight: 1.2 }}>Painel da Coordenação</h2>
            <p style={{ fontSize: "12px", color: "rgba(255,255,255,0.75)", marginTop: "4px" }}>
              {new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
            </p>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            {[
              { v: dashData?.atividades_aguardando_validacao ?? VALIDATIONS.length, l: "Na fila", color: "#D4A017" },
              { v: dashData?.prorrogacoes_pendentes ?? EXTENSIONS.filter(e => e.status !== "aprovada" && e.status !== "negada").length, l: "Prorrogações", color: "#f97316" },
            ].map((s) => (
              <div key={s.l} className="text-center rounded-xl px-3 py-2 sm:px-4 sm:py-2.5" style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.15)" }}>
                <p style={{ fontSize: "clamp(16px,4vw,22px)", fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.v}</p>
                <p style={{ fontSize: "9px", color: "rgba(255,255,255,0.7)", marginTop: "2px" }}>{s.l}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 md:gap-4">
        <KpiCard icon={<Users size={20} />} label="Alunos Ativos" value={ativos} sub="Todos os programas" color="#123C7A" trend="up" />
        <KpiCard icon={<AlertTriangle size={20} />} label="Em Risco" value={emRisco} sub="Requerem ação imediata" color="#dc2626" trend="down" />
        <KpiCard icon={<Clock size={20} />} label="Em Prorrogação" value={emProrrogacao} sub="Com prazo estendido" color="#f97316" />
        <KpiCard icon={<CheckCircle2 size={20} />} label="Concluídos" value={concluidos} sub="Titulados em 2025–2026" color="#1F8A70" trend="up" />
        <KpiCard icon={<TrendingUp size={20} />} label="Tempo Médio" value={dashData?.tempo_medio_integralizacao_meses ? `${dashData.tempo_medio_integralizacao_meses.toFixed(1)}m` : "N/D"} sub="Integralização" color="#8b5cf6" />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <StatusDistribChart onReport={() => setReportModal("status")} statusData={statusData} />
        <OrientadorPerfChart onReport={() => setReportModal("orientador")} />
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ProducaoChart onReport={() => setReportModal("producao")} />
        <IntegralizacaoChart onReport={() => setReportModal("integralizacao")} />
      </div>

      {/* Validation Queue + Extension Requests */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ValidationQueue />
        <ExtensionRequestsSection />
      </div>

      {/* Pending Activities + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PendingActivitiesSection />
        <AlertsCenter />
      </div>

      {/* Program Statistics */}
      <ProgramStatistics />

      {/* Report Modal */}
      <ReportModal type={reportModal} onClose={() => setReportModal(null)} statusData={statusData} />
    </div>
  );
}

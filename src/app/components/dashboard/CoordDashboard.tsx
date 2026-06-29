import React, { useState } from "react";
import { useCoordDashboard } from "@/hooks/useDashboard";
import { useProductionsByMonth } from "@/hooks/useProductionsByMonth";
import { usePendingExtensions } from "@/hooks/usePendingExtensions";
import type { ProductionByMonthItem } from "@/api/reportsApi";
import type { Solicitacao } from "@/api/solicitacoesApi";
import {
  Users, UserCheck, AlertTriangle, Clock, CheckCircle2, TrendingUp, TrendingDown,
  BookOpen, Award, FileText, Download, X, ChevronRight, Eye,
  BarChart2, Filter, Bell, GraduationCap, Layers,
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

interface ProducaoChartPoint { mes: string; total: number; }

const MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

// Converte a série do backend ({ mes: "2025-01", total }) em pontos do gráfico, com o mês
// formatado como rótulo curto "mmm/aa" (ano incluído para distinguir meses de anos distintos).
function toProducaoChartData(items: ProductionByMonthItem[] | null): ProducaoChartPoint[] {
  if (!items) return [];
  return items.map((item) => {
    const [ano, mes] = item.mes.split("-");
    const label = MESES_PT[Number(mes) - 1] ? `${MESES_PT[Number(mes) - 1]}/${ano.slice(2)}` : item.mes;
    return { mes: label, total: item.total };
  });
}

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

const ALERTS: AlertItem[] = [
  { id: "a1", nivel: "critico", titulo: "Prazos vencidos sem prorrogação aprovada", descricao: "8 alunos ultrapassaram o prazo máximo de integralização sem prorrogação formalizada.", afetados: 8, data: "02/06/2026", acao: "Ver alunos" },
  { id: "a2", nivel: "critico", titulo: "Relatórios semestrais em atraso", descricao: "12 relatórios do período 2024-2 não foram entregues até a data limite.", afetados: 12, data: "01/06/2026", acao: "Notificar alunos" },
  { id: "a3", nivel: "atencao", titulo: "Bolsas com expiração iminente", descricao: "6 bolsas CAPES/CNPq vencem nos próximos 30 dias e precisam de renovação.", afetados: 6, data: "02/06/2026", acao: "Processar renovações" },
  { id: "a4", nivel: "atencao", titulo: "Orientadores com sobrecarga", descricao: "3 orientadores estão acima do limite recomendado de 8 orientandos simultâneos.", afetados: 3, data: "30/05/2026", acao: "Redistribuir orientações" },
  { id: "a5", nivel: "info", titulo: "Avaliação CAPES — Prazo para envio de dados", descricao: "O prazo para envio dos dados da avaliação quadrienal é 30/07/2026.", afetados: 0, data: "28/05/2026" },
  { id: "a6", nivel: "info", titulo: "Novo edital de bolsas produtividade CNPq", descricao: "Edital aberto para bolsas PQ 2026. Prazo de inscrição: 15/07/2026.", afetados: 0, data: "29/05/2026" },
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

// Chaveado pelos status do backend (ExtensionResponse.status); 'rejeitada' é exibido como "Negada".
const EXT_STATUS_CFG: Record<string, { label: string; color: string; bg: string }> = {
  pendente: { label: "Pendente", color: "#D4A017", bg: "#fffbeb" },
  em_analise: { label: "Em Análise", color: "#123C7A", bg: "#eef3fc" },
  aprovada: { label: "Aprovada", color: "#1F8A70", bg: "#f0fdf4" },
  rejeitada: { label: "Negada", color: "#dc2626", bg: "#fef2f2" },
};

// Formata data ISO (date "AAAA-MM-DD" ou datetime) em "DD/MM/AAAA", sem deslocar por fuso.
function formatDataBR(value?: string | null): string {
  if (!value) return "—";
  const match = value.slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) return `${match[3]}/${match[2]}/${match[1]}`;
  const parsed = new Date(value);
  return isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("pt-BR");
}

const ALERT_CFG = {
  critico: { color: "#dc2626", bg: "#fef2f2", border: "#fecaca", icon: <AlertTriangle size={16} /> },
  atencao: { color: "#D4A017", bg: "#fffbeb", border: "#fde68a", icon: <Bell size={16} /> },
  info: { color: "#123C7A", bg: "#eef3fc", border: "#c7d9f5", icon: <Bell size={16} /> },
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

function SectionHeader({ title, sub, section, onReport, isMock }: {
  title: string; sub?: string; section: string; onReport?: () => void; isMock?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 mb-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 flex items-center gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h3 style={{ fontSize: "14px", fontWeight: 700, color: "var(--foreground)", wordBreak: "break-word" }}>{title}</h3>
            {isMock && (
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: "var(--tint-orange-bg)", color: "var(--tint-orange-text)", border: "1px solid var(--tint-orange-border)" }}>
                Amostra
              </span>
            )}
          </div>
          {sub && <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "1px" }}>{sub}</p>}
        </div>
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


function ReportModal({ type, onClose, statusData, producaoData }: { type: ReportType; onClose: () => void; statusData: StatusDataProp[]; producaoData: ProducaoChartPoint[] }) {
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
      sub: "Produções validadas por mês (últimos 12 meses)",
      content: (
        <div className="space-y-4">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={producaoData}>
              <defs>
                <linearGradient id="gProd" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1F8A70" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1F8A70" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="mes" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="total" name="Produções validadas" stroke="#1F8A70" fill="url(#gProd)" strokeWidth={2} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
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
      <SectionHeader title="Desempenho dos Orientadores" sub="Orientandos, produções e defesas" section="Orientadores" onReport={onReport} isMock />
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

function ProducaoChart({ onReport, data }: { onReport: () => void; data: ProducaoChartPoint[] }) {
  return (
    <div className="rounded-2xl p-4 md:p-5 overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <SectionHeader title="Produção Científica" sub="Produções validadas por mês" section="Produção Científica" onReport={onReport} />
      <div className="overflow-x-auto -mx-1">
      <div style={{ minWidth: 300 }}>
      <ResponsiveContainer width="100%" height={190}>
        <AreaChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
          <defs key="pr-defs">
            <linearGradient key="pr-g" id="pGProd" x1="0" y1="0" x2="0" y2="1">
              <stop key="sa" offset="5%" stopColor="#1F8A70" stopOpacity={0.25} />
              <stop key="sb" offset="95%" stopColor="#1F8A70" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid key="pr-grid" strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis key="pr-x" dataKey="mes" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <YAxis key="pr-y" width={28} allowDecimals={false} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
          <Tooltip key="pr-tip" contentStyle={{ borderRadius: 8, fontSize: 11 }} />
          <Legend key="pr-leg" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
          <Area key="pr-a" type="monotone" dataKey="total" name="Produções validadas" stroke="#1F8A70" fill="url(#pGProd)" strokeWidth={2} isAnimationActive={false} />
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
      <SectionHeader title="Integralização por Ano" sub="Tempo médio em meses vs. meta do programa" section="Integralização" onReport={onReport} isMock />
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
          <div className="flex items-center gap-2">
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Fila de Validação</h3>
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: "var(--tint-orange-bg)", color: "var(--tint-orange-text)", border: "1px solid var(--tint-orange-border)" }}>Amostra</span>
          </div>
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

function ExtensionRequestsSection({ extensions, loading, error }: { extensions: Solicitacao[]; loading: boolean; error: string | null }) {
  const total = extensions.length;

  return (
    <div className="rounded-2xl p-4 md:p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Solicitações de Prorrogação</h3>
          <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>{loading ? "Carregando…" : `${total} pendente${total !== 1 ? "s" : ""} de decisão`}</p>
        </div>
        <ExportBar section="Prorrogações" />
      </div>

      {error ? (
        <p style={{ fontSize: "12px", color: "var(--tint-danger-text)" }}>Erro ao carregar prorrogações: {error}</p>
      ) : loading ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Carregando prorrogações…</p>
      ) : total === 0 ? (
        <p style={{ fontSize: "12px", color: "var(--muted-foreground)" }}>Nenhuma prorrogação pendente.</p>
      ) : (
        <div className="space-y-3">
          {extensions.map((ext) => {
            const status = String(ext.status);
            const sc = EXT_STATUS_CFG[status] ?? { label: status, color: "var(--muted-foreground)", bg: "var(--muted)" };
            const nome = ext.aluno_nome || ext.aluno || "—";
            const isDoutorado = (ext.nivel || "").toLowerCase() === "doutorado";
            const podeDecidir = status === "pendente" || status === "em_analise";
            return (
              <div key={ext.id} className="rounded-xl p-4" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--foreground)" }}>{nome}</span>
                      <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: isDoutorado ? "var(--tint-blue-bg)" : "var(--tint-violet-bg)", color: isDoutorado ? "var(--tint-blue-text)" : "var(--tint-violet-text)", border: `1px solid ${isDoutorado ? "var(--tint-blue-border)" : "var(--tint-violet-border)"}` }}>
                        {isDoutorado ? "Doutorado" : "Mestrado"}
                      </span>
                      <span className="px-1.5 py-0.5 rounded" style={{ fontSize: "10px", fontWeight: 600, background: sc.bg, color: sc.color }}>{sc.label}</span>
                    </div>
                    {ext.matricula && (
                      <p style={{ fontSize: "11px", color: "var(--muted-foreground)", marginTop: "2px" }}>Matrícula: {ext.matricula}</p>
                    )}
                  </div>
                  <span style={{ fontSize: "10px", color: "var(--muted-foreground)" }}>Protocolo: {formatDataBR(ext.created_at || ext.solicitacao)}</span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--foreground)", marginBottom: "8px" }}><span style={{ color: "var(--muted-foreground)" }}>Motivo: </span>{ext.motivo || ext.justificativa || "—"}</p>
                <div className="flex items-center gap-4" style={{ fontSize: "11px" }}>
                  <span><span style={{ color: "var(--muted-foreground)" }}>Prazo atual: </span><span style={{ fontWeight: 700, color: "var(--tint-danger-text)" }}>{formatDataBR(ext.prazo_atual || ext.data_atual)}</span></span>
                  <ChevronRight size={12} style={{ color: "var(--muted-foreground)" }} />
                  <span><span style={{ color: "var(--muted-foreground)" }}>Novo prazo: </span><span style={{ fontWeight: 700, color: "var(--tint-teal-text)" }}>{formatDataBR(ext.nova_data || ext.prazo_novo)}</span></span>
                </div>
                {podeDecidir && (
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
      )}
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
          <div className="flex items-center gap-2">
            <h3 style={{ fontSize: "15px", fontWeight: 700, color: "var(--foreground)" }}>Central de Alertas</h3>
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: "var(--tint-orange-bg)", color: "var(--tint-orange-text)", border: "1px solid var(--tint-orange-border)" }}>Amostra</span>
          </div>
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

export function CoordDashboard() {
  const { data: dashData, loading, error } = useCoordDashboard();
  const { data: producaoRaw } = useProductionsByMonth(12);
  const producaoData = toProducaoChartData(producaoRaw);
  const { data: pendingExtensions, loading: extLoading, error: extError } = usePendingExtensions();
  const extensions = pendingExtensions ?? [];
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
  const totalAlunos = dashData?.total_alunos ?? ativos;
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
              { v: dashData?.prorrogacoes_pendentes ?? extensions.length, l: "Prorrogações", color: "#f97316" },
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
        <KpiCard icon={<Users size={20} />} label="Total Alunos" value={totalAlunos} sub="Todos os programas" color="#123C7A" trend="up" />
        <KpiCard icon={<UserCheck size={20} />} label="Alunos Ativos" value={ativos} sub="Matrículas vigentes" color="#1F8A70" trend="up" />
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
        <ProducaoChart onReport={() => setReportModal("producao")} data={producaoData} />
        <IntegralizacaoChart onReport={() => setReportModal("integralizacao")} />
      </div>

      {/* Validation Queue + Extension Requests */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ValidationQueue />
        <ExtensionRequestsSection extensions={extensions} loading={extLoading} error={extError} />
      </div>
      {/* Alerts */}
      <AlertsCenter />

      {/* Report Modal */}
      <ReportModal type={reportModal} onClose={() => setReportModal(null)} statusData={statusData} producaoData={producaoData} />
    </div>
  );
}

import React, { useEffect, useMemo, useState } from "react";
import {
  Users, TrendingUp, Calendar, Clock,
  BookOpen, Award, X, ChevronDown, ChevronUp, Search, AlertTriangle,
  GraduationCap, BarChart3, ArrowUpDown, Eye,
  ChevronRight, Loader2,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";

import { useAuth } from "@/hooks/useAuth";
import { useEscapeClose } from "@/hooks/useEscapeClose";
import { TableExportMenu } from "@/app/components/export/TableExportMenu";
import type { ExportColumn } from "@/utils/exportData";
import {
  getStudentsAtRisk, getStudentsByStatus, getStudentsByAdvisor,
  getCompletionTime, getProductionsReport,
  type StudentsAtRiskResponse, type StudentsByStatusResponse,
  type StudentsByAdvisorResponse, type CompletionTimeResponse,
  type ProductionsReportResponse, type SituacaoRegistrada,
  type StudentAtRiskItem, type AdvisorGroupItem, type CompletionTimeItem,
  type ProductionByStudentItem, type ProductionByAdvisorItem,
} from "@/api/reportsApi";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReportConfig { id: string; title: string; desc: string; statLabel: string; color: string; bg: string; border: string; icon: React.ReactNode; }

/** Dados reais dos cinco relatórios, carregados de uma vez na ReportsPage. */
interface ReportsData {
  atRisk: StudentsAtRiskResponse;
  byStatus: StudentsByStatusResponse;
  byAdvisor: StudentsByAdvisorResponse;
  completion: CompletionTimeResponse;
  productions: ProductionsReportResponse;
}

// ─── Metadados de situação (rótulo + cor por enum) ──────────────────────────────

const STATUS_META: Record<SituacaoRegistrada, { label: string; color: string }> = {
  regular: { label: "Regular", color: "#123C7A" },
  em_prorrogacao: { label: "Em Prorrogação", color: "#D4A017" },
  em_risco: { label: "Em Risco", color: "#dc2626" },
  qualificado: { label: "Qualificado", color: "#1F8A70" },
  em_fase_de_defesa: { label: "Fase de Defesa", color: "#8b5cf6" },
  concluido: { label: "Concluído", color: "#0891b2" },
  desligado: { label: "Desligado", color: "#94a3b8" },
};

// ─── Mock Data (apenas Prorrogações — fora do escopo da API nesta issue) ─────────

const PRORROGACOES = [
  { id: "pr1", aluno: "João Pedro Silva", orientador: "Profa. Dra. Ana Lima", prazoOriginal: "Dez/2024", novoPrazo: "Jun/2025", motivo: "Afastamento médico (3 meses)", status: "aprovada", protocolo: "12/11/2024", aprovadoPor: "Coordenação", meses: 6 },
  { id: "pr2", aluno: "Thiago Batista", orientador: "Prof. Dr. Roberto Almeida", prazoOriginal: "Jun/2023", novoPrazo: "Jun/2024", motivo: "Produção científica insuficiente", status: "aprovada", protocolo: "05/05/2023", aprovadoPor: "Coordenação", meses: 12 },
  { id: "pr3", aluno: "Diego Machado", orientador: "Profa. Dra. Ana Lima", prazoOriginal: "Dez/2024", novoPrazo: "Jun/2025", motivo: "Créditos insuficientes", status: "aprovada", protocolo: "15/11/2024", aprovadoPor: "Coordenação", meses: 6 },
  { id: "pr4", aluno: "Marcos Oliveira", orientador: "Prof. Dr. Carlos Ferreira", prazoOriginal: "Jul/2025", novoPrazo: "Jul/2026", motivo: "Atraso no plano de trabalho", status: "pendente", protocolo: "10/01/2026", aprovadoPor: "—", meses: 12 },
  { id: "pr5", aluno: "Rafael Albuquerque", orientador: "Prof. Dr. Roberto Almeida", prazoOriginal: "Jun/2025", novoPrazo: "Dez/2025", motivo: "Afastamento médico", status: "aprovada", protocolo: "02/06/2025", aprovadoPor: "Coordenação", meses: 6 },
  { id: "pr6", aluno: "Isabela Rodrigues", orientador: "Prof. Dr. Carlos Ferreira", prazoOriginal: "Jun/2025", novoPrazo: "Dez/2025", motivo: "Produção insuficiente", status: "pendente", protocolo: "15/01/2026", aprovadoPor: "—", meses: 6 },
  { id: "pr7", aluno: "Fernanda Lima", orientador: "Prof. Dr. Marcos Duarte", prazoOriginal: "Mar/2024", novoPrazo: "Set/2024", motivo: "Complexidade do tema", status: "aprovada", protocolo: "20/02/2024", aprovadoPor: "Coord.+Orient.", meses: 6 },
  { id: "pr8", aluno: "Eduardo Moura", orientador: "Profa. Dra. Sandra Torres", prazoOriginal: "Dez/2024", novoPrazo: "Mar/2025", motivo: "Pendências de créditos", status: "negada", protocolo: "05/12/2024", aprovadoPor: "—", meses: 3 },
  { id: "pr9", aluno: "Bruno Santana", orientador: "Prof. Dr. Roberto Almeida", prazoOriginal: "Fev/2024", novoPrazo: "Ago/2024", motivo: "Experimentos adicionais", status: "aprovada", protocolo: "15/01/2024", aprovadoPor: "Coordenação", meses: 6 },
];

const PRORR_HISTORICO = [
  { periodo: "2021/1", total: 3 }, { periodo: "2021/2", total: 2 },
  { periodo: "2022/1", total: 4 }, { periodo: "2022/2", total: 3 },
  { periodo: "2023/1", total: 5 }, { periodo: "2023/2", total: 6 },
  { periodo: "2024/1", total: 4 }, { periodo: "2024/2", total: 7 },
  { periodo: "2025/1", total: 9 },
];

// ─── Report Config ─────────────────────────────────────────────────────────────

const REPORTS: ReportConfig[] = [
  { id: "atraso", title: "Alunos em Risco", desc: "Alunos com situação de risco inferida e suas razões", statLabel: "em risco", color: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)", border: "var(--tint-danger-border)", icon: <Clock size={20} /> },
  { id: "status", title: "Alunos por Status", desc: "Distribuição dos alunos por situação acadêmica", statLabel: "alunos", color: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)", border: "var(--tint-blue-border)", icon: <BarChart3 size={20} /> },
  { id: "orientador", title: "Alunos por Orientador", desc: "Distribuição e desempenho por orientador", statLabel: "orientadores", color: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)", border: "var(--tint-teal-border)", icon: <Users size={20} /> },
  { id: "tempo", title: "Tempo de Integralização", desc: "Tempo médio para conclusão dos alunos concluídos", statLabel: "média (meses)", color: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)", border: "var(--tint-gold-border)", icon: <TrendingUp size={20} /> },
  { id: "prod-aluno", title: "Produção por Aluno", desc: "Produções bibliográficas aprovadas por aluno", statLabel: "produções", color: "var(--tint-violet-text)", bg: "var(--tint-violet-bg)", border: "var(--tint-violet-border)", icon: <BookOpen size={20} /> },
  { id: "prod-prof", title: "Produção por Orientador", desc: "Produção agregada dos orientandos por orientador", statLabel: "orientadores", color: "#0891b2", bg: "rgba(8,145,178,0.10)", border: "rgba(8,145,178,0.28)", icon: <Award size={20} /> },
  { id: "prorrog", title: "Histórico de Prorrogações", desc: "Prorrogações solicitadas, aprovadas e negadas", statLabel: "registros", color: "var(--tint-orange-text)", bg: "var(--tint-orange-bg)", border: "var(--tint-orange-border)", icon: <Calendar size={20} /> },
];

// ─── Utility ──────────────────────────────────────────────────────────────────

/** Estilo de tooltip Recharts adaptado ao tema (o default é fundo branco, ilegível no dark). */
const TOOLTIP_STYLE = {
  contentStyle: { borderRadius: 8, fontSize: 12, background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)" },
  labelStyle: { color: "var(--foreground)" },
  itemStyle: { color: "var(--foreground)" },
} as const;

/** Rótulo legível da situação inferida/registrada, como exibido na tabela. */
function statusLabel(status: string): string {
  return STATUS_META[status as SituacaoRegistrada]?.label ?? status;
}

function SearchBox({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-xl px-3 py-1.5" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
      <Search size={12} style={{ color: "var(--muted-foreground)" }} />
      <input value={value} onChange={e => onChange(e.target.value)} placeholder="Buscar..." style={{ background: "transparent", border: "none", fontSize: 12, color: "var(--foreground)", outline: "none", width: 140 }} />
      {value && <button onClick={() => onChange("")} style={{ color: "var(--muted-foreground)" }}><X size={11} /></button>}
    </div>
  );
}

function FSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="flex items-center gap-1.5">
      <span style={{ fontSize: 11, color: "var(--muted-foreground)", fontWeight: 600, whiteSpace: "nowrap" }}>{label}:</span>
      <select value={value} onChange={e => onChange(e.target.value)} style={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, padding: "4px 8px", fontSize: 12, color: "var(--foreground)", outline: "none" }}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

type SortDir = "asc" | "desc";
function SortTh({ children, sKey, active, dir, onSort }: { children: React.ReactNode; sKey: string; active: string; dir: SortDir; onSort: (k: string) => void }) {
  const isActive = active === sKey;
  return (
    <th className="px-3 py-2.5 text-left cursor-pointer select-none" onClick={() => onSort(sKey)} style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>
      <div className="flex items-center gap-1">
        {children}
        {isActive ? (dir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />) : <ArrowUpDown size={9} style={{ opacity: 0.4 }} />}
      </div>
    </th>
  );
}

function StatusPill({ status, color }: { status: string; color?: string }) {
  // `color` vem sempre em hex (STATUS_META); o fallback precisa ser hex porque
  // `${c}1f` anexa alfa de 8 dígitos ao fundo — uma CSS var quebraria o valor.
  const c = color ?? "#64748b";
  return <span className="px-2 py-0.5 rounded-lg" style={{ background: `${c}1f`, color: c, fontSize: 10, fontWeight: 700, whiteSpace: "nowrap" }}>{status}</span>;
}

function ProrrogStatusPill({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    aprovada: { bg: "var(--tint-teal-bg)", color: "var(--tint-teal-text)" }, pendente: { bg: "var(--tint-gold-bg)", color: "var(--tint-gold-text)" }, negada: { bg: "var(--tint-danger-bg)", color: "var(--tint-danger-text)" },
  };
  const c = cfg[status] ?? { bg: "var(--muted)", color: "var(--muted-foreground)" };
  return <span className="px-2 py-0.5 rounded-lg" style={{ background: c.bg, color: c.color, fontSize: 10, fontWeight: 700, whiteSpace: "nowrap" }}>{status}</span>;
}

function DrillPanel({ title, color, onClose, children }: { title: string; color: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl mt-4" style={{ background: "var(--muted)", border: `1px solid ${color}30` }}>
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <Eye size={14} style={{ color }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)" }}>{title}</span>
        </div>
        <button onClick={onClose} className="rounded-lg p-1" style={{ background: "var(--card)" }}><X size={13} style={{ color: "var(--muted-foreground)" }} /></button>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="rounded-2xl p-10 text-center" style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted-foreground)", fontSize: 13 }}>{message}</div>;
}

// ─── Report: Alunos em Risco ──────────────────────────────────────────────────

const AT_RISK_COLUMNS: ExportColumn<StudentAtRiskItem>[] = [
  { key: "nome", label: "Aluno" },
  { key: "orientador_nome", label: "Orientador" },
  { key: "situacao_inferida", label: "Situação Inferida", value: s => statusLabel(s.situacao_inferida) },
  { key: "dias_restantes_prazo", label: "Dias Restantes" },
  { key: "razoes_risco", label: "Razões do Risco", value: s => s.razoes_risco.join(" | ") },
];

function AlunosRiscoReport({ data }: { data: StudentsAtRiskResponse }) {
  const [search, setSearch] = useState("");
  const [sortD, setSortD] = useState<SortDir>("asc");
  const [sel, setSel] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let d = data.items;
    if (search) d = d.filter(s => s.nome.toLowerCase().includes(search.toLowerCase()) || s.orientador_nome.toLowerCase().includes(search.toLowerCase()));
    return [...d].sort((a, b) => {
      const av = a.dias_restantes_prazo ?? Number.POSITIVE_INFINITY;
      const bv = b.dias_restantes_prazo ?? Number.POSITIVE_INFINITY;
      return sortD === "asc" ? av - bv : bv - av;
    });
  }, [data.items, search, sortD]);

  if (data.items.length === 0) return <EmptyState message="Nenhum aluno em situação de risco no momento." />;

  const selected = data.items.find(s => s.student_id === sel);
  const chartData = filtered.slice(0, 8).map(s => ({ nome: s.nome.split(" ")[0], dias: s.dias_restantes_prazo ?? 0 }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <SearchBox value={search} onChange={setSearch} />
        <TableExportMenu title="Alunos em Risco" fileName="alunos-em-risco" rows={filtered} columns={AT_RISK_COLUMNS} />
      </div>
      <div className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Dias restantes de prazo (negativo = expirado)</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
            <YAxis dataKey="nome" type="category" tick={{ fontSize: 10, fill: "var(--foreground)" }} width={70} />
            <Tooltip formatter={(v) => [`${v} dias`, "Prazo"]} {...TOOLTIP_STYLE} />
            <Bar dataKey="dias" radius={[0, 4, 4, 0]}>
              {chartData.map((e, i) => <Cell key={i} fill={e.dias < 0 ? "var(--status-danger)" : e.dias < 90 ? "var(--status-warning)" : "var(--muted-foreground)"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--muted)" }}>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Aluno</th>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Orientador</th>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Situação Inferida</th>
              <SortTh sKey="dias" active="dias" dir={sortD} onSort={() => setSortD(d => d === "asc" ? "desc" : "asc")}>Dias Restantes</SortTh>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => {
              const dias = s.dias_restantes_prazo;
              return (
                <React.Fragment key={s.student_id}>
                  <tr onClick={() => setSel(sel === s.student_id ? null : s.student_id)} className="cursor-pointer" style={{ background: sel === s.student_id ? "var(--tint-danger-bg)" : "transparent", borderBottom: "1px solid var(--border)" }}>
                    <td className="px-3 py-2.5"><p style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{s.nome}</p></td>
                    <td className="px-3 py-2.5" style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{s.orientador_nome || "—"}</td>
                    <td className="px-3 py-2.5"><StatusPill status={STATUS_META[s.situacao_inferida as SituacaoRegistrada]?.label ?? s.situacao_inferida} color={STATUS_META[s.situacao_inferida as SituacaoRegistrada]?.color} /></td>
                    <td className="px-3 py-2.5"><span style={{ fontSize: 14, fontWeight: 800, color: dias == null ? "#64748b" : dias < 0 ? "#dc2626" : dias < 90 ? "#D4A017" : "#1F8A70" }}>{dias == null ? "—" : `${dias} d`}</span></td>
                    <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color: "var(--muted-foreground)", transform: sel === s.student_id ? "rotate(90deg)" : "none", transition: "transform 0.2s" }} /></td>
                  </tr>
                  {sel === s.student_id && selected && (
                    <tr><td colSpan={5} className="px-3 py-0">
                      <div className="rounded-xl p-4 my-2" style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
                        <p style={{ fontSize: 12, fontWeight: 700, color: "var(--tint-danger-text)", marginBottom: 8 }}>Razões do risco — {selected.nome}</p>
                        {selected.razoes_risco.length > 0 ? (
                          <div className="space-y-1.5">
                            {selected.razoes_risco.map((m, i) => (
                              <div key={i} className="flex items-center gap-2"><AlertTriangle size={11} style={{ color: "var(--tint-danger-text)", flexShrink: 0 }} /><span style={{ fontSize: 12, color: "var(--tint-danger-text)" }}>{m}</span></div>
                            ))}
                          </div>
                        ) : <p style={{ fontSize: 12, color: "var(--tint-danger-text)" }}>Sem razões detalhadas no último snapshot de inferência.</p>}
                      </div>
                    </td></tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report: Alunos por Status ────────────────────────────────────────────────

function AlunosPorStatusReport({ data }: { data: StudentsByStatusResponse }) {
  const [selStatus, setSelStatus] = useState<string | null>(null);

  const entries = useMemo(() => (
    (Object.entries(data.por_situacao) as [SituacaoRegistrada, { total: number; alunos: { student_id: string; nome: string; orientador_nome: string; nivel: string }[] }][])
      .map(([status, grupo]) => ({ status, label: STATUS_META[status]?.label ?? status, color: STATUS_META[status]?.color ?? "#64748b", count: grupo.total, alunos: grupo.alunos }))
      .sort((a, b) => b.count - a.count)
  ), [data.por_situacao]);

  if (entries.length === 0) return <EmptyState message="Nenhum aluno cadastrado." />;

  const total = entries.reduce((s, e) => s + e.count, 0);
  const selected = entries.find(e => e.status === selStatus);

  const columns: ExportColumn<(typeof entries)[number]>[] = [
    { key: "label", label: "Situação" },
    { key: "count", label: "Alunos" },
    { key: "percentual", label: "Percentual (%)", value: e => (total ? Math.round((e.count / total) * 100) : 0) },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <p style={{ fontSize: 13, color: "var(--muted-foreground)" }}>Total: <strong style={{ color: "var(--foreground)" }}>{total} alunos</strong> · Clique em um segmento para ver detalhes</p>
        <TableExportMenu title="Alunos por Status" fileName="alunos-por-status" rows={entries} columns={columns} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 8 }}>Distribuição por Status</p>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={entries} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="count" nameKey="label"
                onClick={d => setSelStatus(selStatus === d.status ? null : d.status)}>
                {entries.map((e, i) => <Cell key={i} fill={e.color} stroke={selStatus === e.status ? "#fff" : "none"} strokeWidth={3} style={{ cursor: "pointer" }} />)}
              </Pie>
              <Tooltip formatter={(v, n) => [`${v} alunos`, n]} {...TOOLTIP_STYLE} />
              <Legend formatter={v => <span style={{ fontSize: 11 }}>{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-2">
          {entries.map(e => (
            <button key={e.status} onClick={() => setSelStatus(selStatus === e.status ? null : e.status)} className="w-full rounded-xl p-3 text-left transition-all"
              style={{ background: selStatus === e.status ? `${e.color}15` : "var(--card)", border: `2px solid ${selStatus === e.status ? e.color : "var(--border)"}` }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="rounded-full" style={{ width: 10, height: 10, background: e.color }} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)" }}>{e.label}</span>
                </div>
                <span style={{ fontSize: 18, fontWeight: 900, color: e.color }}>{e.count}</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 rounded-full overflow-hidden" style={{ height: 5, background: "var(--muted)" }}><div className="h-full rounded-full" style={{ width: `${total ? (e.count / total) * 100 : 0}%`, background: e.color }} /></div>
                <span style={{ fontSize: 10, color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>{total ? Math.round((e.count / total) * 100) : 0}%</span>
              </div>
            </button>
          ))}
        </div>
      </div>
      {selected && (
        <DrillPanel title={`Alunos com status: ${selected.label}`} color={selected.color} onClose={() => setSelStatus(null)}>
          {selected.alunos.length > 0 ? (
            <div className="space-y-2">
              {selected.alunos.map(s => (
                <div key={s.student_id} className="flex items-center gap-3 rounded-xl p-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width: 32, height: 32, background: "var(--tint-blue-bg)" }}><GraduationCap size={14} style={{ color: "var(--tint-blue-text)" }} /></div>
                  <div className="flex-1"><p style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{s.nome}</p><p style={{ fontSize: 11, color: "var(--muted-foreground)" }}>{s.orientador_nome || "Sem orientador"}</p></div>
                </div>
              ))}
            </div>
          ) : <p style={{ fontSize: 12, color: "var(--muted-foreground)", textAlign: "center", padding: "16px 0" }}>Sem alunos nesta categoria.</p>}
        </DrillPanel>
      )}
    </div>
  );
}

// ─── Report: Alunos por Orientador ────────────────────────────────────────────

const BY_ADVISOR_COLUMNS: ExportColumn<AdvisorGroupItem>[] = [
  { key: "advisor_nome", label: "Orientador" },
  { key: "total_orientandos", label: "Orientandos" },
  { key: "em_risco", label: "Em Risco" },
  { key: "regulares", label: "Regulares" },
];

function AlunosPorOrientadorReport({ data }: { data: StudentsByAdvisorResponse }) {
  const [sortK, setSortK] = useState<"total_orientandos" | "em_risco" | "regulares">("total_orientandos");
  const [sortD, setSortD] = useState<SortDir>("desc");

  function onSort(k: string) { const key = k as typeof sortK; if (sortK === key) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(key); setSortD("desc"); } }

  const filtered = useMemo(() => (
    [...data.items].sort((a, b) => sortD === "asc" ? a[sortK] - b[sortK] : b[sortK] - a[sortK])
  ), [data.items, sortK, sortD]);

  if (data.items.length === 0) return <EmptyState message="Nenhum orientador cadastrado." />;

  const chartData = filtered.map(o => ({ nome: o.advisor_nome.split(" ").slice(-1)[0] || o.advisor_nome, total: o.total_orientandos, emRisco: o.em_risco }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-end gap-3 flex-wrap">
        <TableExportMenu title="Alunos por Orientador" fileName="alunos-por-orientador" rows={filtered} columns={BY_ADVISOR_COLUMNS} />
      </div>
      <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Orientandos por Orientador</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="nome" tick={{ fontSize: 11, fill: "var(--foreground)" }} />
            <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} allowDecimals={false} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="total" name="Total" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
            <Bar dataKey="emRisco" name="Em Risco" fill="var(--status-danger)" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--muted)" }}>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Orientador</th>
              <SortTh sKey="total_orientandos" active={sortK} dir={sortD} onSort={onSort}>Orientandos</SortTh>
              <SortTh sKey="em_risco" active={sortK} dir={sortD} onSort={onSort}>Em Risco</SortTh>
              <SortTh sKey="regulares" active={sortK} dir={sortD} onSort={onSort}>Regulares</SortTh>
            </tr>
          </thead>
          <tbody>
            {filtered.map(o => (
              <tr key={o.advisor_id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td className="px-3 py-2.5" style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{o.advisor_nome || "—"}</td>
                <td className="px-3 py-2.5"><span style={{ fontSize: 16, fontWeight: 800, color: "#123C7A" }}>{o.total_orientandos}</span></td>
                <td className="px-3 py-2.5"><span style={{ fontSize: 13, fontWeight: 700, color: o.em_risco > 0 ? "#dc2626" : "#64748b" }}>{o.em_risco}</span></td>
                <td className="px-3 py-2.5"><span style={{ fontSize: 13, fontWeight: 600, color: "#1F8A70" }}>{o.regulares}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report: Tempo de Integralização ──────────────────────────────────────────

const COMPLETION_COLUMNS: ExportColumn<CompletionTimeItem>[] = [
  { key: "student_nome", label: "Aluno" },
  { key: "meses", label: "Meses" },
  { key: "ano_conclusao", label: "Ano de Conclusão" },
];

function TempoIntegralizacaoReport({ data }: { data: CompletionTimeResponse }) {
  const kpis = [
    { l: "Média", v: data.media_meses, c: "var(--tint-blue-text)", bg: "var(--tint-blue-bg)" },
    { l: "Mínimo", v: data.minimo_meses, c: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" },
    { l: "Máximo", v: data.maximo_meses, c: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" },
  ];
  const chartData = data.historico.map(h => ({ nome: h.student_nome.split(" ")[0], meses: h.meses }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-4 flex-wrap">
          {kpis.map(k => (
            <div key={k.l} className="rounded-xl px-4 py-2" style={{ background: k.bg }}>
              <p style={{ fontSize: 11, color: k.c }}>{k.l}</p>
              <p style={{ fontSize: 18, fontWeight: 800, color: k.c }}>{k.v == null ? "—" : `${k.v} m`}</p>
            </div>
          ))}
          <div className="rounded-xl px-4 py-2" style={{ background: "var(--muted)" }}>
            <p style={{ fontSize: 11, color: "var(--muted-foreground)" }}>Concluídos</p>
            <p style={{ fontSize: 18, fontWeight: 800, color: "var(--foreground)" }}>{data.total_concluidos}</p>
          </div>
        </div>
        <TableExportMenu title="Tempo de Integralização" fileName="tempo-de-integralizacao" rows={data.historico} columns={COMPLETION_COLUMNS} />
      </div>
      {data.historico.length === 0 ? (
        <EmptyState message="Nenhum aluno concluído com datas suficientes para o cálculo." />
      ) : (
        <>
          <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Meses até a conclusão por aluno</p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="nome" tick={{ fontSize: 10, fill: "var(--foreground)" }} />
                <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} label={{ value: "meses", angle: -90, position: "insideLeft", fontSize: 10, fill: "var(--muted-foreground)" }} />
                <Tooltip formatter={(v) => [`${v} meses`, "Integralização"]} {...TOOLTIP_STYLE} />
                <Bar dataKey="meses" radius={[4, 4, 0, 0]}>
                  {chartData.map((e, i) => <Cell key={i} fill={e.meses <= 24 ? "var(--status-active)" : e.meses <= 48 ? "var(--status-warning)" : "var(--status-danger)"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
            <table className="w-full" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--muted)" }}>
                  {["Aluno", "Meses", "Ano de Conclusão"].map(h => (
                    <th key={h} className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.historico.map((h, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td className="px-3 py-2.5" style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{h.student_nome}</td>
                    <td className="px-3 py-2.5"><span style={{ fontSize: 14, fontWeight: 800, color: h.meses <= 24 ? "#1F8A70" : h.meses <= 48 ? "#D4A017" : "#dc2626" }}>{h.meses}</span><span style={{ fontSize: 10, color: "var(--muted-foreground)" }}> m</span></td>
                    <td className="px-3 py-2.5" style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{h.ano_conclusao}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Report: Produção por Aluno ───────────────────────────────────────────────

const NIVEIS = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "SC"] as const;

const PRODUCTION_BY_STUDENT_COLUMNS: ExportColumn<ProductionByStudentItem>[] = [
  { key: "student_nome", label: "Aluno" },
  ...NIVEIS.map(nivel => ({ key: nivel, label: nivel, value: (s: ProductionByStudentItem) => s.por_nivel[nivel] })),
  { key: "total", label: "Total" },
  { key: "pontuacao_total", label: "Pontuação" },
];

function ProducaoPorAlunoReport({ data }: { data: ProductionsReportResponse }) {
  const [search, setSearch] = useState("");
  const [sortK, setSortK] = useState<"total" | "pontuacao_total">("pontuacao_total");
  const [sortD, setSortD] = useState<SortDir>("desc");

  function onSort(k: string) { const key = k as typeof sortK; if (sortK === key) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(key); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = data.por_aluno;
    if (search) d = d.filter(s => s.student_nome.toLowerCase().includes(search.toLowerCase()));
    return [...d].sort((a, b) => sortD === "asc" ? a[sortK] - b[sortK] : b[sortK] - a[sortK]);
  }, [data.por_aluno, search, sortK, sortD]);

  if (data.por_aluno.length === 0) return <EmptyState message="Nenhuma produção aprovada registrada." />;

  const chartData = filtered.slice(0, 8).map(s => ({ nome: s.student_nome.split(" ")[0], A1: s.por_nivel.A1, A2: s.por_nivel.A2, A3: s.por_nivel.A3, A4: s.por_nivel.A4, A5: s.por_nivel.A5, A6: s.por_nivel.A6, A7: s.por_nivel.A7, A8: s.por_nivel.A8, SC: s.por_nivel.SC }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <SearchBox value={search} onChange={setSearch} />
        <TableExportMenu title="Produção por Aluno" fileName="producao-por-aluno" rows={filtered} columns={PRODUCTION_BY_STUDENT_COLUMNS} />
      </div>
      <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Produções por Aluno (por nível)</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="nome" tick={{ fontSize: 10, fill: "var(--foreground)" }} />
            <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} allowDecimals={false} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="A1" fill="#123C7A" stackId="a" />
            <Bar dataKey="A2" fill="#1B4F9C" stackId="a" />
            <Bar dataKey="A3" fill="#1F6FB5" stackId="a" />
            <Bar dataKey="A4" fill="#2E86C1" stackId="a" />
            <Bar dataKey="A5" fill="#1F8A70" stackId="a" />
            <Bar dataKey="A6" fill="#3DA68C" stackId="a" />
            <Bar dataKey="A7" fill="#D4A017" stackId="a" />
            <Bar dataKey="A8" fill="#E0BC5C" stackId="a" />
            <Bar dataKey="SC" fill="#94a3b8" stackId="a" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--muted)" }}>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Aluno</th>
              {["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "SC"].map(h => <th key={h} className="px-3 py-2.5 text-center" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>{h}</th>)}
              <SortTh sKey="total" active={sortK} dir={sortD} onSort={onSort}>Total</SortTh>
              <SortTh sKey="pontuacao_total" active={sortK} dir={sortD} onSort={onSort}>Pontuação</SortTh>
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <tr key={s.student_id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td className="px-3 py-2.5" style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{s.student_nome}</td>
                {[s.por_nivel.A1, s.por_nivel.A2, s.por_nivel.A3, s.por_nivel.A4, s.por_nivel.A5, s.por_nivel.A6, s.por_nivel.A7, s.por_nivel.A8, s.por_nivel.SC].map((v, i) => (
                  <td key={i} className="px-3 py-2.5 text-center"><span style={{ fontSize: 13, fontWeight: 700, color: v > 0 ? "var(--foreground)" : "var(--muted-foreground)" }}>{v}</span></td>
                ))}
                <td className="px-3 py-2.5 text-center"><span style={{ fontSize: 15, fontWeight: 900, color: "#123C7A" }}>{s.total}</span></td>
                <td className="px-3 py-2.5 text-center"><span style={{ fontSize: 14, fontWeight: 800, color: "#8b5cf6" }}>{s.pontuacao_total}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report: Produção por Orientador ──────────────────────────────────────────

const PRODUCTION_BY_ADVISOR_COLUMNS: ExportColumn<ProductionByAdvisorItem>[] = [
  { key: "advisor_nome", label: "Orientador" },
  { key: "total", label: "Produções" },
  { key: "pontuacao_media_orientandos", label: "Pontuação Média / Orientando" },
];

function ProducaoPorOrientadorReport({ data }: { data: ProductionsReportResponse }) {
  const [sortK, setSortK] = useState<"total" | "pontuacao_media_orientandos">("total");
  const [sortD, setSortD] = useState<SortDir>("desc");

  function onSort(k: string) { const key = k as typeof sortK; if (sortK === key) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(key); setSortD("desc"); } }

  const filtered = useMemo(() => (
    [...data.por_orientador].sort((a, b) => sortD === "asc" ? a[sortK] - b[sortK] : b[sortK] - a[sortK])
  ), [data.por_orientador, sortK, sortD]);

  if (data.por_orientador.length === 0) return <EmptyState message="Nenhuma produção aprovada registrada." />;

  const chartData = filtered.map(p => ({ nome: p.advisor_nome.split(" ").slice(-1)[0] || p.advisor_nome, total: p.total }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-end gap-3 flex-wrap">
        <TableExportMenu title="Produção por Orientador" fileName="producao-por-orientador" rows={filtered} columns={PRODUCTION_BY_ADVISOR_COLUMNS} />
      </div>
      <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Produções dos orientandos por Orientador</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="nome" tick={{ fontSize: 10, fill: "var(--foreground)" }} />
            <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} allowDecimals={false} />
            <Tooltip {...TOOLTIP_STYLE} />
            <Bar dataKey="total" name="Produções" fill="#0891b2" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--muted)" }}>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Orientador</th>
              <SortTh sKey="total" active={sortK} dir={sortD} onSort={onSort}>Produções</SortTh>
              <SortTh sKey="pontuacao_media_orientandos" active={sortK} dir={sortD} onSort={onSort}>Pontuação Média / Orientando</SortTh>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <tr key={p.advisor_id} style={{ borderBottom: "1px solid var(--border)" }}>
                <td className="px-3 py-2.5" style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{p.advisor_nome || "—"}</td>
                <td className="px-3 py-2.5"><span style={{ fontSize: 15, fontWeight: 900, color: "#0891b2" }}>{p.total}</span></td>
                <td className="px-3 py-2.5"><span style={{ fontSize: 14, fontWeight: 800, color: "#8b5cf6" }}>{p.pontuacao_media_orientandos}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report: Histórico de Prorrogações (mock — fora do escopo desta issue) ──────

const PRORROGACOES_COLUMNS: ExportColumn<(typeof PRORROGACOES)[number]>[] = [
  { key: "aluno", label: "Aluno" },
  { key: "orientador", label: "Orientador" },
  { key: "prazoOriginal", label: "Prazo Original" },
  { key: "novoPrazo", label: "Novo Prazo" },
  { key: "meses", label: "Meses" },
  { key: "status", label: "Status" },
  { key: "motivo", label: "Motivo" },
  { key: "protocolo", label: "Protocolo" },
  { key: "aprovadoPor", label: "Aprovado Por" },
];

function HistoricoProrrogacoesReport() {
  const [status, setStatus] = useState("Todos");
  const [search, setSearch] = useState("");
  const [sortK, setSortK] = useState("meses");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = PRORROGACOES;
    if (status !== "Todos") d = d.filter(p => p.status === status);
    if (search) d = d.filter(p => p.aluno.toLowerCase().includes(search.toLowerCase()));
    // `as any`: ordenação por chave dinâmica sobre o mock temporário de prorrogações (fora do escopo da API nesta issue).
    return [...d].sort((a, b) => { const av = (a as any)[sortK]; const bv = (b as any)[sortK]; return sortD === "asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1); });
  }, [status, search, sortK, sortD]);

  const selItem = PRORROGACOES.find(p => p.id === sel);
  const counts = { aprovada: PRORROGACOES.filter(p => p.status === "aprovada").length, pendente: PRORROGACOES.filter(p => p.status === "pendente").length, negada: PRORROGACOES.filter(p => p.status === "negada").length };

  return (
    <div className="space-y-5">
      <div className="rounded-xl px-4 py-2.5" style={{ background: "var(--tint-orange-bg)", border: "1px solid var(--tint-orange-border)", fontSize: 12, color: "var(--tint-orange-text)" }}>
        Dados ilustrativos — a integração de prorrogações com a API será feita em issue futura.
      </div>
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 flex-wrap items-center">
          <SearchBox value={search} onChange={setSearch} />
          <FSelect label="Status" value={status} onChange={setStatus} options={["Todos", "aprovada", "pendente", "negada"]} />
        </div>
        <TableExportMenu title="Histórico de Prorrogações" fileName="historico-de-prorrogacoes" rows={filtered} columns={PRORROGACOES_COLUMNS} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", marginBottom: 12 }}>Prorrogações por Período</p>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={PRORR_HISTORICO}>
              <defs><linearGradient id="gradPr" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={0.3} /><stop offset="95%" stopColor="#ea580c" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="periodo" tick={{ fontSize: 9, fill: "var(--muted-foreground)" }} />
              <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Area type="monotone" dataKey="total" name="Prorrogações" stroke="#ea580c" fill="url(#gradPr)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3">
          {[{ l: "Aprovadas", n: counts.aprovada, c: "var(--tint-teal-text)", bg: "var(--tint-teal-bg)" }, { l: "Pendentes", n: counts.pendente, c: "var(--tint-gold-text)", bg: "var(--tint-gold-bg)" }, { l: "Negadas", n: counts.negada, c: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)" }].map(s => (
            <div key={s.l} className="rounded-xl p-4" style={{ background: s.bg, border: "1px solid var(--border)" }}>
              <p style={{ fontSize: 28, fontWeight: 900, color: s.c }}>{s.n}</p>
              <p style={{ fontSize: 11, color: s.c }}>{s.l}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border: "1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--muted)" }}>
              <SortTh sKey="aluno" active={sortK} dir={sortD} onSort={onSort}>Aluno</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Orientador</th>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Prazo Original</th>
              <th className="px-3 py-2.5 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>Novo Prazo</th>
              <SortTh sKey="meses" active={sortK} dir={sortD} onSort={onSort}>Meses</SortTh>
              <SortTh sKey="status" active={sortK} dir={sortD} onSort={onSort}>Status</SortTh>
              <th className="px-3 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <React.Fragment key={p.id}>
                <tr onClick={() => setSel(sel === p.id ? null : p.id)} className="cursor-pointer" style={{ borderBottom: "1px solid var(--border)", background: sel === p.id ? "var(--tint-orange-bg)" : "transparent" }}>
                  <td className="px-3 py-2.5" style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>{p.aluno}</td>
                  <td className="px-3 py-2.5" style={{ fontSize: 11, color: "var(--muted-foreground)" }}>{p.orientador.split(" ").slice(0, 3).join(" ")}</td>
                  <td className="px-3 py-2.5" style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{p.prazoOriginal}</td>
                  <td className="px-3 py-2.5" style={{ fontSize: 12, fontWeight: 600, color: "var(--foreground)" }}>{p.novoPrazo}</td>
                  <td className="px-3 py-2.5"><span style={{ fontSize: 14, fontWeight: 800, color: p.meses >= 12 ? "#dc2626" : p.meses >= 6 ? "#D4A017" : "#1F8A70" }}>+{p.meses}m</span></td>
                  <td className="px-3 py-2.5"><ProrrogStatusPill status={p.status} /></td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color: "var(--muted-foreground)", transform: sel === p.id ? "rotate(90deg)" : "none", transition: "transform 0.2s" }} /></td>
                </tr>
                {sel === p.id && selItem && (
                  <tr><td colSpan={7} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background: "var(--tint-orange-bg)", border: "1px solid var(--tint-orange-border)" }}>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <div><p style={{ fontSize: 10, color: "var(--tint-orange-text)", fontWeight: 600 }}>MOTIVO</p><p style={{ fontSize: 12, color: "var(--foreground)", marginTop: 2 }}>{selItem.motivo}</p></div>
                        <div><p style={{ fontSize: 10, color: "var(--tint-orange-text)", fontWeight: 600 }}>PROTOCOLO</p><p style={{ fontSize: 12, color: "var(--foreground)", marginTop: 2 }}>{selItem.protocolo}</p></div>
                        <div><p style={{ fontSize: 10, color: "var(--tint-orange-text)", fontWeight: 600 }}>APROVADO POR</p><p style={{ fontSize: 12, color: "var(--foreground)", marginTop: 2 }}>{selItem.aprovadoPor}</p></div>
                      </div>
                    </div>
                  </td></tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report Modal ─────────────────────────────────────────────────────────────

function renderReport(id: string, data: ReportsData) {
  switch (id) {
    case "atraso": return <AlunosRiscoReport data={data.atRisk} />;
    case "status": return <AlunosPorStatusReport data={data.byStatus} />;
    case "orientador": return <AlunosPorOrientadorReport data={data.byAdvisor} />;
    case "tempo": return <TempoIntegralizacaoReport data={data.completion} />;
    case "prod-aluno": return <ProducaoPorAlunoReport data={data.productions} />;
    case "prod-prof": return <ProducaoPorOrientadorReport data={data.productions} />;
    case "prorrog": return <HistoricoProrrogacoesReport />;
    default: return null;
  }
}

function ReportModal({ reportId, stat, data, onClose }: { reportId: string; stat: string; data: ReportsData; onClose: () => void }) {
  useEscapeClose(true, onClose);
  const cfg = REPORTS.find(r => r.id === reportId)!;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: "rgba(0,0,0,0.5)" }} onClick={onClose}>
      <div className="w-full max-w-6xl max-h-[92vh] flex flex-col rounded-2xl" style={{ background: "var(--background)", boxShadow: "0 24px 80px rgba(0,0,0,0.25)" }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-4 px-6 py-4 flex-shrink-0" style={{ background: "var(--card)", borderRadius: "16px 16px 0 0", borderBottom: "1px solid var(--border)" }}>
          <div className="rounded-xl p-2.5 flex-shrink-0" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
            <span style={{ color: cfg.color }}>{cfg.icon}</span>
          </div>
          <div className="flex-1 min-w-0">
            <h2 style={{ fontSize: 18, fontWeight: 800, color: "var(--foreground)" }}>{cfg.title}</h2>
            <p style={{ fontSize: 12, color: "var(--muted-foreground)" }}>{cfg.desc}</p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right">
              <p style={{ fontSize: 24, fontWeight: 900, color: cfg.color }}>{stat}</p>
              <p style={{ fontSize: 10, color: "var(--muted-foreground)" }}>{cfg.statLabel}</p>
            </div>
            <button onClick={onClose} className="rounded-xl p-2.5" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}><X size={16} /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {renderReport(reportId, data)}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

/** Estatística exibida no card e no cabeçalho do modal, derivada dos dados reais. */
function statFor(id: string, data: ReportsData): string {
  switch (id) {
    case "atraso": return String(data.atRisk.total);
    case "status": return String(Object.values(data.byStatus.por_situacao).reduce((s, g) => s + (g?.total ?? 0), 0));
    case "orientador": return String(data.byAdvisor.items.length);
    case "tempo": return data.completion.media_meses == null ? "—" : `${data.completion.media_meses}m`;
    case "prod-aluno": return String(data.productions.total_producoes_aprovadas);
    case "prod-prof": return String(data.productions.por_orientador.length);
    case "prorrog": return String(PRORROGACOES.length);
    default: return "—";
  }
}

export function ReportsPage() {
  const { token, role } = useAuth();
  const [openReport, setOpenReport] = useState<string | null>(null);
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    if (role !== "coordenacao") {
      // Não-coordenação fica bloqueado pelo guard de render abaixo; enquanto o papel
      // ainda não resolveu (role === null) mantém o spinner em vez de disparar as
      // requisições exclusivas da coordenação com papel indefinido.
      setLoading(role === null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([
      getStudentsAtRisk(token),
      getStudentsByStatus(token),
      getStudentsByAdvisor(token),
      getCompletionTime(token),
      getProductionsReport(token),
    ])
      .then(([atRisk, byStatus, byAdvisor, completion, productions]) => {
        if (active) setData({ atRisk, byStatus, byAdvisor, completion, productions });
      })
      .catch(() => { if (active) setError("Não foi possível carregar os relatórios. Tente novamente."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
    // `role` nas dependências: o token chega antes do papel (GET /auth/me); sem re-executar
    // quando o papel resolve, a página ficava presa no spinner sem nunca buscar (issue #320).
  }, [token, role]);

  if (role && role !== "coordenacao") {
    return <EmptyState message="Os relatórios gerenciais são exclusivos da coordenação." />;
  }

  const summary = data ? [
    { label: "Total de Alunos", value: statFor("status", data), color: "var(--tint-blue-text)" },
    { label: "Em Risco", value: String(data.atRisk.total), color: "var(--tint-danger-text)" },
    { label: "Concluídos", value: String(data.completion.total_concluidos), color: "var(--tint-teal-text)" },
    { label: "Produções", value: String(data.productions.total_producoes_aprovadas), color: "var(--tint-violet-text)" },
  ] : [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 style={{ color: "var(--foreground)", marginBottom: 4 }}>Relatórios Gerenciais</h1>
          <p style={{ color: "var(--muted-foreground)", fontSize: 14 }}>Análises com gráficos, tabelas e drill-down por categoria</p>
        </div>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3" style={{ background: "var(--tint-danger-bg)", color: "var(--tint-danger-text)", fontSize: 13 }}>{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center gap-2 py-20" style={{ color: "var(--muted-foreground)" }}>
          <Loader2 size={18} className="animate-spin" /> <span style={{ fontSize: 13 }}>Carregando relatórios...</span>
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {summary.map(s => (
              <div key={s.label} className="rounded-2xl p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <p style={{ fontSize: 32, fontWeight: 900, color: s.color }}>{s.value}</p>
                <p style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 2 }}>{s.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {REPORTS.map(r => (
              <div key={r.id} className="rounded-2xl p-5 flex flex-col" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <div className="flex items-start justify-between mb-4">
                  <div className="rounded-xl p-2.5" style={{ background: r.bg, border: `1px solid ${r.border}` }}>
                    <span style={{ color: r.color }}>{r.icon}</span>
                  </div>
                  <div className="text-right">
                    <p style={{ fontSize: 22, fontWeight: 900, color: r.color }}>{statFor(r.id, data)}</p>
                    <p style={{ fontSize: 9, color: "var(--muted-foreground)" }}>{r.statLabel}</p>
                  </div>
                </div>
                <p style={{ fontSize: 14, fontWeight: 700, color: "var(--foreground)", marginBottom: 4 }}>{r.title}</p>
                <p style={{ fontSize: 11, color: "var(--muted-foreground)", lineHeight: 1.5, flex: 1, marginBottom: 16 }}>{r.desc}</p>
                <button onClick={() => setOpenReport(r.id)}
                  className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 transition-all"
                  style={{ background: r.color, color: "#fff", fontSize: 12, fontWeight: 700 }}
                  onMouseEnter={e => (e.currentTarget.style.opacity = "0.9")}
                  onMouseLeave={e => (e.currentTarget.style.opacity = "1")}>
                  <Eye size={13} /> Abrir Relatório
                </button>
              </div>
            ))}
          </div>

          {openReport && <ReportModal reportId={openReport} stat={statFor(openReport, data)} data={data} onClose={() => setOpenReport(null)} />}
        </>
      ) : null}
    </div>
  );
}

import React, { useState, useMemo } from "react";
import {
  Download, Users, FileText, TrendingUp, Calendar, Clock,
  BookOpen, Award, X, ChevronDown, ChevronUp, Search, AlertTriangle,
  CheckCircle2, GraduationCap, BarChart3, ArrowUpDown, Eye, Filter,
  FileSpreadsheet, FileBadge, ChevronRight,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, AreaChart, Area,
} from "recharts";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ReportConfig { id: string; title: string; desc: string; stat: string; statLabel: string; color: string; bg: string; border: string; icon: React.ReactNode; }

// ─── Mock Data ────────────────────────────────────────────────────────────────

const ATRASO_STUDENTS = [
  { id:"at1", nome:"Marcos Oliveira",     matricula:"2021001", orientador:"Prof. Dr. Carlos Ferreira",  programa:"PPGCC", nivel:"Doutorado", prazoOriginal:"Jul/2025", diasAtraso:334, creditos:35, meta:60, plano:40, motivos:["Créditos insuficientes (35/60)","Plano de trabalho: 40%","Nenhuma publicação registrada"] },
  { id:"at2", nome:"João Pedro Silva",    matricula:"2022003", orientador:"Profa. Dra. Ana Lima",        programa:"PPGCC", nivel:"Mestrado",  prazoOriginal:"Dez/2024", diasAtraso:183, creditos:22, meta:36, plano:60, motivos:["Créditos insuficientes (22/36)","Qualificação pendente"] },
  { id:"at3", nome:"Fernanda Castro",     matricula:"2021005", orientador:"Profa. Dra. Carla Mendes",    programa:"PPGEE", nivel:"Doutorado", prazoOriginal:"Mar/2026", diasAtraso:92,  creditos:48, meta:60, plano:70, motivos:["Plano incompleto (70%)","Produção insuficiente para nível Doutorado"] },
  { id:"at4", nome:"Rafael Albuquerque",  matricula:"2022008", orientador:"Prof. Dr. Roberto Almeida",  programa:"PPGCC", nivel:"Mestrado",  prazoOriginal:"Jun/2025", diasAtraso:274, creditos:18, meta:36, plano:45, motivos:["Afastamento médico (3 meses)","Créditos insuficientes (18/36)"] },
  { id:"at5", nome:"Isabela Rodrigues",   matricula:"2020002", orientador:"Prof. Dr. Carlos Ferreira",  programa:"PPGEE", nivel:"Doutorado", prazoOriginal:"Jun/2025", diasAtraso:274, creditos:55, meta:60, plano:85, motivos:["Apenas 1 publicação (mínimo 2)","Comprovante de proficiência vencido"] },
  { id:"at6", nome:"Diego Machado",       matricula:"2022011", orientador:"Profa. Dra. Ana Lima",        programa:"PPGCC", nivel:"Mestrado",  prazoOriginal:"Dez/2024", diasAtraso:183, creditos:12, meta:36, plano:30, motivos:["Créditos insuficientes (12/36)","Plano de trabalho: 30%","Ausência em reuniões de orientação"] },
  { id:"at7", nome:"Patrícia Nascimento", matricula:"2021009", orientador:"Profa. Dra. Carla Mendes",    programa:"PPGCC", nivel:"Doutorado", prazoOriginal:"Set/2025", diasAtraso:60,  creditos:54, meta:60, plano:90, motivos:["Pendência administrativa (documentação)"] },
  { id:"at8", nome:"Henrique Lopes",      matricula:"2022014", orientador:"Prof. Dr. Roberto Almeida",  programa:"PPGEE", nivel:"Doutorado", prazoOriginal:"Mar/2026", diasAtraso:45,  creditos:42, meta:60, plano:62, motivos:["Créditos insuficientes (42/60)","Plano de trabalho: 62%"] },
];

const STATUS_DATA = [
  { status:"Em Andamento",  count:42, mestrado:24, doutorado:18, color:"#123C7A" },
  { status:"Em Risco",      count:8,  mestrado:3,  doutorado:5,  color:"#dc2626" },
  { status:"Concluído",     count:15, mestrado:10, doutorado:5,  color:"#1F8A70" },
  { status:"Prorrogado",    count:5,  mestrado:2,  doutorado:3,  color:"#D4A017" },
  { status:"Trancado",      count:2,  mestrado:2,  doutorado:0,  color:"#94a3b8" },
];
const STATUS_STUDENTS = [
  { nome:"Lucas Ferreira Silva",  status:"Em Risco",     nivel:"Doutorado", orientador:"Profa. Dra. Carla Mendes",   entrada:"2023" },
  { nome:"Ana Paula Costa",       status:"Em Andamento", nivel:"Doutorado", orientador:"Prof. Dr. Roberto Almeida",  entrada:"2021" },
  { nome:"Pedro Henrique Lima",   status:"Concluído",    nivel:"Mestrado",  orientador:"Profa. Dra. Ana Lima",       entrada:"2022" },
  { nome:"Bruna Cavalcanti",      status:"Em Andamento", nivel:"Mestrado",  orientador:"Prof. Dr. Carlos Ferreira",  entrada:"2024" },
  { nome:"Thiago Batista",        status:"Prorrogado",   nivel:"Doutorado", orientador:"Prof. Dr. Roberto Almeida",  entrada:"2020" },
  { nome:"Camila Fonseca",        status:"Em Andamento", nivel:"Doutorado", orientador:"Profa. Dra. Carla Mendes",   entrada:"2022" },
  { nome:"Rafael Costa",          status:"Trancado",     nivel:"Mestrado",  orientador:"Profa. Dra. Ana Lima",       entrada:"2023" },
  { nome:"Juliana Pinto",         status:"Concluído",    nivel:"Mestrado",  orientador:"Prof. Dr. Carlos Ferreira",  entrada:"2021" },
];

const ORIENTADORES_DATA = [
  { nome:"Prof. Dr. Roberto Almeida",  depto:"Ciência da Computação", total:12, mestrado:5, doutorado:7, emRisco:2, concluidos:8, color:"#123C7A", students:["Ana Paula Costa","Thiago Batista","Rafael Albuquerque","Maria Souza","Carlos Lima","Beatriz Melo"] },
  { nome:"Profa. Dra. Carla Mendes",   depto:"Ciência da Computação", total:9,  mestrado:3, doutorado:6, emRisco:1, concluidos:5, color:"#1F8A70", students:["Lucas Ferreira Silva","Camila Fonseca","Fernanda Castro","Patrícia Nascimento","Rodrigo Lima"] },
  { nome:"Profa. Dra. Ana Lima",       depto:"Engenharia Elétrica",   total:8,  mestrado:6, doutorado:2, emRisco:2, concluidos:4, color:"#D4A017", students:["João Pedro Silva","Diego Machado","Pedro Henrique Lima","Mariana Torres","Rafael Costa"] },
  { nome:"Prof. Dr. Carlos Ferreira",  depto:"Engenharia Elétrica",   total:11, mestrado:4, doutorado:7, emRisco:3, concluidos:6, color:"#8b5cf6", students:["Marcos Oliveira","Isabela Rodrigues","Bruna Cavalcanti","Juliana Pinto","Paulo Silva"] },
  { nome:"Prof. Dr. Marcos Duarte",    depto:"Ciência da Computação", total:7,  mestrado:4, doutorado:3, emRisco:0, concluidos:4, color:"#0891b2", students:["Henrique Lopes","Fernanda Lima","Ricardo Santos","Aline Costa"] },
  { nome:"Profa. Dra. Sandra Torres",  depto:"Engenharia Elétrica",   total:6,  mestrado:3, doutorado:3, emRisco:1, concluidos:3, color:"#ea580c", students:["Eduardo Moura","Bianca Oliveira","Felipe Rocha"] },
];

const TEMPO_DATA = [
  { ano:"2018", mestrado:28, doutorado:54 },
  { ano:"2019", mestrado:27, doutorado:52 },
  { ano:"2020", mestrado:26, doutorado:51 },
  { ano:"2021", mestrado:25, doutorado:50 },
  { ano:"2022", mestrado:24, doutorado:49 },
  { ano:"2023", mestrado:25, doutorado:48 },
  { ano:"2024", mestrado:24, doutorado:47 },
  { ano:"2025", mestrado:23, doutorado:46 },
];
const TEMPO_STUDENTS = [
  { nome:"Pedro Henrique Lima",  nivel:"Mestrado",  inicio:"Ago/2022", fim:"Ago/2024", meses:24, orientador:"Profa. Dra. Ana Lima" },
  { nome:"Juliana Pinto",        nivel:"Mestrado",  inicio:"Mar/2021", fim:"Mar/2023", meses:24, orientador:"Prof. Dr. Carlos Ferreira" },
  { nome:"Ana Clara Souza",      nivel:"Doutorado", inicio:"Jan/2019", fim:"Jun/2023", meses:53, orientador:"Prof. Dr. Roberto Almeida" },
  { nome:"Ricardo Barbosa",      nivel:"Doutorado", inicio:"Jul/2018", fim:"Dec/2022", meses:53, orientador:"Profa. Dra. Carla Mendes" },
  { nome:"Marina Gomes",         nivel:"Mestrado",  inicio:"Fev/2023", fim:"Fev/2025", meses:24, orientador:"Prof. Dr. Marcos Duarte" },
  { nome:"Caio Alves",           nivel:"Doutorado", inicio:"Mar/2020", fim:"Set/2024", meses:54, orientador:"Profa. Dra. Sandra Torres" },
  { nome:"Tatiane Melo",         nivel:"Mestrado",  inicio:"Jul/2021", fim:"Jan/2024", meses:30, orientador:"Prof. Dr. Carlos Ferreira" },
  { nome:"Bruno Santana",        nivel:"Doutorado", inicio:"Ago/2019", fim:"Fev/2024", meses:54, orientador:"Prof. Dr. Roberto Almeida" },
];

const PROD_ALUNO = [
  { nome:"Lucas Ferreira Silva",  orientador:"Profa. Dra. Carla Mendes",  nivel:"Doutorado", a1:2, a2:1, b1:0, b2:0, software:1, patente:0, total:4 },
  { nome:"Ana Paula Costa",       orientador:"Prof. Dr. Roberto Almeida", nivel:"Doutorado", a1:3, a2:2, b1:1, b2:0, software:0, patente:1, total:7 },
  { nome:"Carlos Eduardo Lima",   orientador:"Profa. Dra. Ana Lima",       nivel:"Doutorado", a1:1, a2:2, b1:2, b2:1, software:0, patente:0, total:6 },
  { nome:"Marina Torres",         orientador:"Prof. Dr. Carlos Ferreira",  nivel:"Mestrado",  a1:0, a2:1, b1:2, b2:0, software:1, patente:0, total:4 },
  { nome:"Pedro Henrique Lima",   orientador:"Profa. Dra. Ana Lima",       nivel:"Mestrado",  a1:0, a2:2, b1:1, b2:1, software:0, patente:0, total:4 },
  { nome:"Camila Fonseca",        orientador:"Profa. Dra. Carla Mendes",  nivel:"Doutorado", a1:1, a2:0, b1:1, b2:2, software:2, patente:0, total:6 },
  { nome:"Rodrigo Silva",         orientador:"Prof. Dr. Roberto Almeida", nivel:"Mestrado",  a1:0, a2:0, b1:1, b2:2, software:0, patente:0, total:3 },
  { nome:"Beatriz Melo",          orientador:"Prof. Dr. Carlos Ferreira",  nivel:"Doutorado", a1:2, a2:1, b1:0, b2:0, software:1, patente:1, total:5 },
  { nome:"Fernanda Castro",       orientador:"Profa. Dra. Carla Mendes",  nivel:"Doutorado", a1:1, a2:1, b1:1, b2:0, software:0, patente:0, total:3 },
  { nome:"Eduardo Moura",         orientador:"Profa. Dra. Sandra Torres", nivel:"Mestrado",  a1:0, a2:1, b1:0, b2:1, software:0, patente:0, total:2 },
];

const PROD_PROF = [
  { nome:"Prof. Dr. Roberto Almeida",  depto:"CC",  orientandos:12, a1:8, a2:6, b1:5, b2:3, software:2, patente:2, total:26 },
  { nome:"Profa. Dra. Carla Mendes",   depto:"CC",  orientandos:9,  a1:6, a2:4, b1:4, b2:2, software:5, patente:1, total:22 },
  { nome:"Prof. Dr. Carlos Ferreira",  depto:"EE",  orientandos:11, a1:5, a2:7, b1:6, b2:2, software:1, patente:3, total:24 },
  { nome:"Profa. Dra. Ana Lima",       depto:"EE",  orientandos:8,  a1:3, a2:5, b1:7, b2:4, software:0, patente:0, total:19 },
  { nome:"Prof. Dr. Marcos Duarte",    depto:"CC",  orientandos:7,  a1:4, a2:3, b1:2, b2:1, software:3, patente:1, total:14 },
  { nome:"Profa. Dra. Sandra Torres",  depto:"EE",  orientandos:6,  a1:2, a2:4, b1:3, b2:2, software:0, patente:0, total:11 },
];

const PRORROGACOES = [
  { id:"pr1", aluno:"João Pedro Silva",    orientador:"Profa. Dra. Ana Lima",        nivel:"Mestrado",  prazoOriginal:"Dez/2024", novoPrazo:"Jun/2025", motivo:"Afastamento médico (3 meses)",   status:"aprovada",  protocolo:"12/11/2024", aprovadoPor:"Coordenação", meses:6  },
  { id:"pr2", aluno:"Thiago Batista",      orientador:"Prof. Dr. Roberto Almeida",   nivel:"Doutorado", prazoOriginal:"Jun/2023", novoPrazo:"Jun/2024", motivo:"Produção científica insuficiente", status:"aprovada", protocolo:"05/05/2023", aprovadoPor:"Coordenação", meses:12 },
  { id:"pr3", aluno:"Diego Machado",       orientador:"Profa. Dra. Ana Lima",        nivel:"Mestrado",  prazoOriginal:"Dez/2024", novoPrazo:"Jun/2025", motivo:"Créditos insuficientes",         status:"aprovada",  protocolo:"15/11/2024", aprovadoPor:"Coordenação", meses:6  },
  { id:"pr4", aluno:"Marcos Oliveira",     orientador:"Prof. Dr. Carlos Ferreira",   nivel:"Doutorado", prazoOriginal:"Jul/2025", novoPrazo:"Jul/2026", motivo:"Atraso no plano de trabalho",    status:"pendente",  protocolo:"10/01/2026", aprovadoPor:"—",           meses:12 },
  { id:"pr5", aluno:"Rafael Albuquerque",  orientador:"Prof. Dr. Roberto Almeida",   nivel:"Mestrado",  prazoOriginal:"Jun/2025", novoPrazo:"Dez/2025", motivo:"Afastamento médico",             status:"aprovada",  protocolo:"02/06/2025", aprovadoPor:"Coordenação", meses:6  },
  { id:"pr6", aluno:"Isabela Rodrigues",   orientador:"Prof. Dr. Carlos Ferreira",   nivel:"Doutorado", prazoOriginal:"Jun/2025", novoPrazo:"Dez/2025", motivo:"Produção insuficiente",          status:"pendente",  protocolo:"15/01/2026", aprovadoPor:"—",           meses:6  },
  { id:"pr7", aluno:"Fernanda Lima",       orientador:"Prof. Dr. Marcos Duarte",     nivel:"Mestrado",  prazoOriginal:"Mar/2024", novoPrazo:"Set/2024", motivo:"Complexidade do tema",           status:"aprovada",  protocolo:"20/02/2024", aprovadoPor:"Coord.+Orient.", meses:6 },
  { id:"pr8", aluno:"Eduardo Moura",       orientador:"Profa. Dra. Sandra Torres",   nivel:"Mestrado",  prazoOriginal:"Dez/2024", novoPrazo:"Mar/2025", motivo:"Pendências de créditos",         status:"negada",    protocolo:"05/12/2024", aprovadoPor:"—",           meses:3  },
  { id:"pr9", aluno:"Bruno Santana",       orientador:"Prof. Dr. Roberto Almeida",   nivel:"Doutorado", prazoOriginal:"Fev/2024", novoPrazo:"Ago/2024", motivo:"Experimentos adicionais",        status:"aprovada",  protocolo:"15/01/2024", aprovadoPor:"Coordenação", meses:6  },
];

const PRORR_HISTORICO = [
  { periodo:"2021/1", total:3 },{ periodo:"2021/2", total:2 },
  { periodo:"2022/1", total:4 },{ periodo:"2022/2", total:3 },
  { periodo:"2023/1", total:5 },{ periodo:"2023/2", total:6 },
  { periodo:"2024/1", total:4 },{ periodo:"2024/2", total:7 },
  { periodo:"2025/1", total:9 },
];

// ─── Report Config ─────────────────────────────────────────────────────────────

const REPORTS: ReportConfig[] = [
  { id:"atraso",     title:"Alunos em Atraso",             desc:"Alunos com prazo expirado ou progresso crítico",        stat:"8",   statLabel:"em atraso",       color:"var(--tint-danger-text)", bg:"var(--tint-danger-bg)", border:"var(--tint-danger-border)", icon:<Clock size={20}/> },
  { id:"status",     title:"Alunos por Status",             desc:"Distribuição dos alunos por situação acadêmica",         stat:"72",  statLabel:"alunos ativos",   color:"var(--tint-blue-text)",   bg:"var(--tint-blue-bg)",   border:"var(--tint-blue-border)",   icon:<BarChart3 size={20}/> },
  { id:"orientador", title:"Alunos por Orientador",         desc:"Distribuição e desempenho por orientador",              stat:"6",   statLabel:"orientadores",    color:"var(--tint-teal-text)",   bg:"var(--tint-teal-bg)",   border:"var(--tint-teal-border)",   icon:<Users size={20}/> },
  { id:"tempo",      title:"Tempo de Integralização",       desc:"Tempo médio para conclusão de mestrado e doutorado",    stat:"24m", statLabel:"média mestrado",  color:"var(--tint-gold-text)",   bg:"var(--tint-gold-bg)",   border:"var(--tint-gold-border)",   icon:<TrendingUp size={20}/> },
  { id:"prod-aluno", title:"Produção por Aluno",            desc:"Publicações e produções por aluno",                     stat:"186", statLabel:"produções totais",color:"var(--tint-violet-text)", bg:"var(--tint-violet-bg)", border:"var(--tint-violet-border)", icon:<BookOpen size={20}/> },
  { id:"prod-prof",  title:"Produção por Professor",        desc:"Publicações por orientador e seus orientandos",         stat:"116", statLabel:"publicações",     color:"#0891b2", bg:"rgba(8,145,178,0.10)", border:"rgba(8,145,178,0.28)", icon:<Award size={20}/> },
  { id:"prorrog",    title:"Histórico de Prorrogações",     desc:"Prorrogações solicitadas, aprovadas e negadas",         stat:"9",   statLabel:"registros",       color:"var(--tint-orange-text)", bg:"var(--tint-orange-bg)", border:"var(--tint-orange-border)", icon:<Calendar size={20}/> },
];

// ─── Utility ──────────────────────────────────────────────────────────────────

function showToast(msg: string, color = "#1F8A70") {
  const el = document.createElement("div");
  el.textContent = msg;
  Object.assign(el.style, { position:"fixed", bottom:"24px", right:"24px", zIndex:"9999", background:color, color:"#fff", padding:"12px 20px", borderRadius:"12px", fontSize:"13px", fontWeight:"700", boxShadow:"0 8px 24px rgba(0,0,0,0.2)", opacity:"1", transition:"opacity 0.3s" });
  document.body.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; }, 2000);
  setTimeout(() => { try { document.body.removeChild(el); } catch{} }, 2300);
}

function FSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <div className="flex items-center gap-1.5">
      <span style={{ fontSize:11, color:"var(--muted-foreground)", fontWeight:600, whiteSpace:"nowrap" }}>{label}:</span>
      <select value={value} onChange={e => onChange(e.target.value)} style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:8, padding:"4px 8px", fontSize:12, color:"var(--foreground)", outline:"none" }}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

function SearchBox({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-xl px-3 py-1.5" style={{ background:"var(--muted)", border:"1px solid var(--border)" }}>
      <Search size={12} style={{ color:"var(--muted-foreground)" }}/>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder="Buscar..." style={{ background:"transparent", border:"none", fontSize:12, color:"var(--foreground)", outline:"none", width:140 }}/>
      {value && <button onClick={() => onChange("")} style={{ color:"var(--muted-foreground)" }}><X size={11}/></button>}
    </div>
  );
}

function ExportBar({ title }: { title: string }) {
  return (
    <div className="flex gap-2">
      {[["PDF","#dc2626",<FileBadge size={12}/>],["Excel","#1F8A70",<FileSpreadsheet size={12}/>],["CSV","#123C7A",<Download size={12}/>]].map(([fmt, c, ic]) => (
        <button key={fmt as string} onClick={() => showToast(`Exportando ${title} como ${fmt}...`, c as string)}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5" style={{ background:`${c}15`, color:c as string, border:`1px solid ${c}30`, fontSize:11, fontWeight:700 }}>
          {ic as React.ReactNode} {fmt as string}
        </button>
      ))}
    </div>
  );
}

type SortDir = "asc" | "desc";
function SortTh({ children, sKey, active, dir, onSort }: { children: React.ReactNode; sKey: string; active: string; dir: SortDir; onSort: (k: string) => void }) {
  const isActive = active === sKey;
  return (
    <th className="px-3 py-2.5 text-left cursor-pointer select-none" onClick={() => onSort(sKey)} style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)", whiteSpace:"nowrap" }}>
      <div className="flex items-center gap-1">
        {children}
        {isActive ? (dir === "asc" ? <ChevronUp size={10}/> : <ChevronDown size={10}/>) : <ArrowUpDown size={9} style={{ opacity:0.4 }}/>}
      </div>
    </th>
  );
}

function StatusPill({ status }: { status: string }) {
  const cfg: Record<string, { bg: string; color: string }> = {
    aprovada:        { bg:"#dcfce7", color:"#1F8A70" },
    pendente:        { bg:"#fef9c3", color:"#D4A017" },
    negada:          { bg:"#fee2e2", color:"#dc2626" },
    "Em Andamento":  { bg:"#eef3fc", color:"#123C7A" },
    "Em Risco":      { bg:"#fee2e2", color:"#dc2626" },
    Concluído:       { bg:"#dcfce7", color:"#1F8A70" },
    Prorrogado:      { bg:"#fef9c3", color:"#D4A017" },
    Trancado:        { bg:"#f1f5f9", color:"#64748b" },
    Doutorado:       { bg:"#eef3fc", color:"#123C7A" },
    Mestrado:        { bg:"#ede9fe", color:"#8b5cf6" },
  };
  const c = cfg[status] ?? { bg:"#f1f5f9", color:"#64748b" };
  return <span className="px-2 py-0.5 rounded-lg" style={{ background:c.bg, color:c.color, fontSize:10, fontWeight:700, whiteSpace:"nowrap" }}>{status}</span>;
}

function DrillPanel({ title, color, onClose, children }: { title: string; color: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl mt-4" style={{ background:"var(--muted)", border:`1px solid ${color}30` }}>
      <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom:"1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <Eye size={14} style={{ color }}/>
          <span style={{ fontSize:13, fontWeight:700, color:"var(--foreground)" }}>{title}</span>
        </div>
        <button onClick={onClose} className="rounded-lg p-1" style={{ background:"var(--card)" }}><X size={13} style={{ color:"var(--muted-foreground)" }}/></button>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// ─── Report: Alunos em Atraso ─────────────────────────────────────────────────

function AlunosAtrasoReport() {
  const [search, setSearch] = useState("");
  const [nivel, setNivel] = useState("Todos");
  const [sortK, setSortK] = useState("diasAtraso");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let d = ATRASO_STUDENTS;
    if (nivel !== "Todos") d = d.filter(s => s.nivel === nivel);
    if (search) d = d.filter(s => s.nome.toLowerCase().includes(search.toLowerCase()) || s.orientador.toLowerCase().includes(search.toLowerCase()));
    return [...d].sort((a, b) => { const av = (a as any)[sortK]; const bv = (b as any)[sortK]; return sortD === "asc" ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1); });
  }, [search, nivel, sortK, sortD]);

  const selected = ATRASO_STUDENTS.find(s => s.id === sel);
  const chartData = filtered.slice(0, 8).map(s => ({ nome: s.nome.split(" ")[0], dias: s.diasAtraso }));

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 flex-wrap items-center">
          <SearchBox value={search} onChange={setSearch}/>
          <FSelect label="Nível" value={nivel} onChange={setNivel} options={["Todos","Mestrado","Doutorado"]}/>
        </div>
        <ExportBar title="Alunos em Atraso"/>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 rounded-2xl p-4" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
          <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Dias em Atraso por Aluno</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} layout="vertical" margin={{ left:10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false}/>
              <XAxis type="number" tick={{ fontSize:10, fill:"var(--muted-foreground)" }} label={{ value:"dias", position:"insideRight", fontSize:10 }}/>
              <YAxis dataKey="nome" type="category" tick={{ fontSize:10, fill:"var(--foreground)" }} width={70}/>
              <Tooltip formatter={(v) => [`${v} dias`, "Atraso"]} contentStyle={{ borderRadius:8, fontSize:12 }}/>
              <Bar dataKey="dias" radius={[0,4,4,0]}>
                {chartData.map((e, i) => <Cell key={i} fill={e.dias > 200 ? "#dc2626" : e.dias > 100 ? "#D4A017" : "#94a3b8"}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3">
          {[{ l:"Atraso Crítico (>200d)", n:filtered.filter(s=>s.diasAtraso>200).length, c:"#dc2626", bg:"#fee2e2" },{ l:"Atraso Moderado (100-200d)", n:filtered.filter(s=>s.diasAtraso>=100&&s.diasAtraso<=200).length, c:"#D4A017", bg:"#fef9c3" },{ l:"Atraso Leve (<100d)", n:filtered.filter(s=>s.diasAtraso<100).length, c:"#64748b", bg:"#f1f5f9" }].map(s => (
            <div key={s.l} className="rounded-xl p-4" style={{ background:s.bg, border:`1px solid ${s.c}30` }}>
              <p style={{ fontSize:26, fontWeight:900, color:s.c }}>{s.n}</p>
              <p style={{ fontSize:11, color:s.c, marginTop:2 }}>{s.l}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              <SortTh sKey="nome" active={sortK} dir={sortD} onSort={onSort}>Aluno</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Orientador</th>
              <SortTh sKey="nivel" active={sortK} dir={sortD} onSort={onSort}>Nível</SortTh>
              <SortTh sKey="diasAtraso" active={sortK} dir={sortD} onSort={onSort}>Dias em Atraso</SortTh>
              <SortTh sKey="creditos" active={sortK} dir={sortD} onSort={onSort}>Créditos</SortTh>
              <SortTh sKey="plano" active={sortK} dir={sortD} onSort={onSort}>Plano</SortTh>
              <th className="px-3 py-2.5"/>
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <React.Fragment key={s.id}>
                <tr onClick={() => setSel(sel === s.id ? null : s.id)} className="cursor-pointer" style={{ background: sel === s.id ? `${s.diasAtraso > 200 ? "#dc2626" : "#D4A017"}08` : "transparent", borderBottom:"1px solid var(--border)" }}>
                  <td className="px-3 py-2.5"><p style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{s.nome}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>{s.matricula}</p></td>
                  <td className="px-3 py-2.5" style={{ fontSize:12, color:"var(--muted-foreground)" }}>{s.orientador.split(" ").slice(0,3).join(" ")}</td>
                  <td className="px-3 py-2.5"><StatusPill status={s.nivel}/></td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:14, fontWeight:800, color:s.diasAtraso>200?"#dc2626":s.diasAtraso>100?"#D4A017":"#64748b" }}>{s.diasAtraso}</span><span style={{ fontSize:10, color:"var(--muted-foreground)" }}> dias</span></td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:12, fontWeight:700, color:s.creditos >= s.meta ? "#1F8A70":"#dc2626" }}>{s.creditos}/{s.meta}</span></td>
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2"><div className="rounded-full overflow-hidden flex-1" style={{ height:5, background:"var(--muted)", minWidth:60 }}><div className="h-full rounded-full" style={{ width:`${s.plano}%`, background:s.plano>=70?"#1F8A70":s.plano>=40?"#D4A017":"#dc2626" }}/></div><span style={{ fontSize:10, fontWeight:700 }}>{s.plano}%</span></div>
                  </td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color:"var(--muted-foreground)", transform: sel===s.id ? "rotate(90deg)":"none", transition:"transform 0.2s" }}/></td>
                </tr>
                {sel === s.id && (
                  <tr><td colSpan={7} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background:"#fee2e2", border:"1px solid #fca5a5" }}>
                      <p style={{ fontSize:12, fontWeight:700, color:"#dc2626", marginBottom:8 }}>Motivos do atraso — {s.nome}</p>
                      <div className="space-y-1.5">
                        {s.motivos.map((m, i) => (
                          <div key={i} className="flex items-center gap-2"><AlertTriangle size={11} style={{ color:"#dc2626", flexShrink:0 }}/><span style={{ fontSize:12, color:"#991b1b" }}>{m}</span></div>
                        ))}
                      </div>
                      <div className="mt-3 pt-3 grid grid-cols-3 gap-3" style={{ borderTop:"1px solid #fca5a5" }}>
                        <div><p style={{ fontSize:10, color:"#dc2626" }}>Prazo Original</p><p style={{ fontSize:12, fontWeight:700, color:"#991b1b" }}>{s.prazoOriginal}</p></div>
                        <div><p style={{ fontSize:10, color:"#dc2626" }}>Créditos</p><p style={{ fontSize:12, fontWeight:700, color:"#991b1b" }}>{s.creditos}/{s.meta}</p></div>
                        <div><p style={{ fontSize:10, color:"#dc2626" }}>Plano</p><p style={{ fontSize:12, fontWeight:700, color:"#991b1b" }}>{s.plano}%</p></div>
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

// ─── Report: Alunos por Status ────────────────────────────────────────────────

function AlunosPorStatusReport() {
  const [selStatus, setSelStatus] = useState<string | null>(null);
  const COLORS = STATUS_DATA.map(s => s.color);
  const total = STATUS_DATA.reduce((s, d) => s + d.count, 0);

  const drillStudents = selStatus ? STATUS_STUDENTS.filter(s => s.status === selStatus) : [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <p style={{ fontSize:13, color:"var(--muted-foreground)" }}>Total: <strong style={{ color:"var(--foreground)" }}>{total} alunos</strong> · Clique em um segmento para ver detalhes</p>
        <ExportBar title="Alunos por Status"/>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
          <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:8 }}>Distribuição por Status</p>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={STATUS_DATA} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="count"
                onClick={d => setSelStatus(selStatus === d.status ? null : d.status)}>
                {STATUS_DATA.map((e, i) => <Cell key={i} fill={e.color} stroke={selStatus===e.status?"#fff":"none"} strokeWidth={3} style={{ cursor:"pointer" }}/>)}
              </Pie>
              <Tooltip formatter={(v, n) => [`${v} alunos`, n]}/>
              <Legend formatter={v => <span style={{ fontSize:11 }}>{v}</span>}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-2">
          {STATUS_DATA.map(s => (
            <button key={s.status} onClick={() => setSelStatus(selStatus === s.status ? null : s.status)} className="w-full rounded-xl p-3 text-left transition-all"
              style={{ background:selStatus===s.status?`${s.color}15`:"var(--card)", border:`2px solid ${selStatus===s.status?s.color:"var(--border)"}` }}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="rounded-full" style={{ width:10, height:10, background:s.color }}/>
                  <span style={{ fontSize:13, fontWeight:700, color:"var(--foreground)" }}>{s.status}</span>
                </div>
                <span style={{ fontSize:18, fontWeight:900, color:s.color }}>{s.count}</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 rounded-full overflow-hidden" style={{ height:5, background:"var(--muted)" }}><div className="h-full rounded-full" style={{ width:`${(s.count/total)*100}%`, background:s.color }}/></div>
                <span style={{ fontSize:10, color:"var(--muted-foreground)", whiteSpace:"nowrap" }}>{Math.round((s.count/total)*100)}% · M:{s.mestrado} D:{s.doutorado}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
      {selStatus && (
        <DrillPanel title={`Alunos com status: ${selStatus}`} color={STATUS_DATA.find(s=>s.status===selStatus)?.color ?? "#123C7A"} onClose={() => setSelStatus(null)}>
          {drillStudents.length > 0 ? (
            <div className="space-y-2">
              {drillStudents.map((s, i) => (
                <div key={i} className="flex items-center gap-3 rounded-xl p-3" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
                  <div className="rounded-full flex items-center justify-center flex-shrink-0" style={{ width:32, height:32, background:"#eef3fc" }}><GraduationCap size={14} style={{ color:"#123C7A" }}/></div>
                  <div className="flex-1"><p style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{s.nome}</p><p style={{ fontSize:11, color:"var(--muted-foreground)" }}>{s.orientador}</p></div>
                  <StatusPill status={s.nivel}/>
                  <span style={{ fontSize:11, color:"var(--muted-foreground)" }}>{s.entrada}</span>
                </div>
              ))}
              <p style={{ fontSize:11, color:"var(--muted-foreground)", textAlign:"center", marginTop:4 }}>Mostrando {drillStudents.length} alunos nesta categoria</p>
            </div>
          ) : <p style={{ fontSize:12, color:"var(--muted-foreground)", textAlign:"center", padding:"16px 0" }}>Dados detalhados não disponíveis para esta amostra.</p>}
        </DrillPanel>
      )}
    </div>
  );
}

// ─── Report: Alunos por Orientador ────────────────────────────────────────────

function AlunosPorOrientadorReport() {
  const [depto, setDepto] = useState("Todos");
  const [sortK, setSortK] = useState("total");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = ORIENTADORES_DATA;
    if (depto !== "Todos") d = d.filter(o => o.depto === depto);
    return [...d].sort((a, b) => { const av = (a as any)[sortK]; const bv = (b as any)[sortK]; return sortD === "asc" ? (av>bv?1:-1) : (av<bv?1:-1); });
  }, [depto, sortK, sortD]);

  const selOrient = ORIENTADORES_DATA.find(o => o.nome === sel);

  const chartData = filtered.map(o => ({ nome: o.nome.split(" ").slice(-1)[0], mestrado: o.mestrado, doutorado: o.doutorado, emRisco: o.emRisco }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <FSelect label="Departamento" value={depto} onChange={setDepto} options={["Todos","Ciência da Computação","Engenharia Elétrica"]}/>
        <ExportBar title="Alunos por Orientador"/>
      </div>
      <div className="rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Alunos por Orientador</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ bottom:20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
            <XAxis dataKey="nome" tick={{ fontSize:11, fill:"var(--foreground)" }}/>
            <YAxis tick={{ fontSize:10, fill:"var(--muted-foreground)" }}/>
            <Tooltip contentStyle={{ borderRadius:8, fontSize:12 }}/>
            <Legend wrapperStyle={{ fontSize:11 }}/>
            <Bar dataKey="mestrado" name="Mestrado" fill="#123C7A" radius={[3,3,0,0]}/>
            <Bar dataKey="doutorado" name="Doutorado" fill="#1F8A70" radius={[3,3,0,0]}/>
            <Bar dataKey="emRisco" name="Em Risco" fill="#dc2626" radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              <SortTh sKey="nome" active={sortK} dir={sortD} onSort={onSort}>Orientador</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Depto.</th>
              <SortTh sKey="total" active={sortK} dir={sortD} onSort={onSort}>Total</SortTh>
              <SortTh sKey="mestrado" active={sortK} dir={sortD} onSort={onSort}>Mestrado</SortTh>
              <SortTh sKey="doutorado" active={sortK} dir={sortD} onSort={onSort}>Doutorado</SortTh>
              <SortTh sKey="emRisco" active={sortK} dir={sortD} onSort={onSort}>Em Risco</SortTh>
              <SortTh sKey="concluidos" active={sortK} dir={sortD} onSort={onSort}>Concluídos</SortTh>
              <th className="px-3 py-2.5"/>
            </tr>
          </thead>
          <tbody>
            {filtered.map(o => (
              <React.Fragment key={o.nome}>
                <tr onClick={() => setSel(sel === o.nome ? null : o.nome)} className="cursor-pointer" style={{ borderBottom:"1px solid var(--border)", background: sel===o.nome ? `${o.color}08`:"transparent" }}>
                  <td className="px-3 py-2.5"><div className="flex items-center gap-2"><div className="rounded-full" style={{ width:8, height:8, background:o.color }}/><span style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{o.nome}</span></div></td>
                  <td className="px-3 py-2.5" style={{ fontSize:11, color:"var(--muted-foreground)" }}>{o.depto}</td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:16, fontWeight:800, color:o.color }}>{o.total}</span></td>
                  <td className="px-3 py-2.5" style={{ fontSize:13, fontWeight:600, color:"#123C7A" }}>{o.mestrado}</td>
                  <td className="px-3 py-2.5" style={{ fontSize:13, fontWeight:600, color:"#1F8A70" }}>{o.doutorado}</td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:13, fontWeight:700, color:o.emRisco>0?"#dc2626":"#64748b" }}>{o.emRisco}</span></td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:13, fontWeight:600, color:"#1F8A70" }}>{o.concluidos}</span></td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color:"var(--muted-foreground)", transform: sel===o.nome ? "rotate(90deg)":"none", transition:"transform 0.2s" }}/></td>
                </tr>
                {sel === o.nome && selOrient && (
                  <tr><td colSpan={8} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background:`${selOrient.color}10`, border:`1px solid ${selOrient.color}30` }}>
                      <p style={{ fontSize:12, fontWeight:700, color:selOrient.color, marginBottom:8 }}>Orientandos de {selOrient.nome.split(" ").slice(-2).join(" ")}</p>
                      <div className="flex flex-wrap gap-2">
                        {selOrient.students.map((s, i) => (
                          <span key={i} className="rounded-lg px-2.5 py-1" style={{ background:"var(--card)", border:"1px solid var(--border)", fontSize:12, color:"var(--foreground)" }}>{s}</span>
                        ))}
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

// ─── Report: Tempo Médio ──────────────────────────────────────────────────────

function TempoIntegralizacaoReport() {
  const [nivel, setNivel] = useState("Todos");
  const [sel, setSel] = useState<string | null>(null);

  const avgMestrado = Math.round(TEMPO_DATA.reduce((s, d) => s + d.mestrado, 0) / TEMPO_DATA.length);
  const avgDoutorado = Math.round(TEMPO_DATA.reduce((s, d) => s + d.doutorado, 0) / TEMPO_DATA.length);

  const drillStudents = sel ? TEMPO_STUDENTS.filter(s => nivel === "Todos" || s.nivel === nivel) : [];

  const filteredStudents = useMemo(() => {
    if (nivel === "Todos") return TEMPO_STUDENTS;
    return TEMPO_STUDENTS.filter(s => s.nivel === nivel);
  }, [nivel]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 items-center flex-wrap">
          <FSelect label="Nível" value={nivel} onChange={setNivel} options={["Todos","Mestrado","Doutorado"]}/>
          <div className="flex gap-4">
            <div className="rounded-xl px-4 py-2" style={{ background:"#eef3fc" }}><p style={{ fontSize:11, color:"#123C7A" }}>Média Mestrado</p><p style={{ fontSize:18, fontWeight:800, color:"#123C7A" }}>{avgMestrado} meses</p></div>
            <div className="rounded-xl px-4 py-2" style={{ background:"#dcfce7" }}><p style={{ fontSize:11, color:"#1F8A70" }}>Média Doutorado</p><p style={{ fontSize:18, fontWeight:800, color:"#1F8A70" }}>{avgDoutorado} meses</p></div>
          </div>
        </div>
        <ExportBar title="Tempo de Integralização"/>
      </div>
      <div className="rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Evolução do Tempo Médio (2018–2025)</p>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={TEMPO_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
            <XAxis dataKey="ano" tick={{ fontSize:11, fill:"var(--muted-foreground)" }}/>
            <YAxis tick={{ fontSize:10, fill:"var(--muted-foreground)" }} label={{ value:"meses", angle:-90, position:"insideLeft", fontSize:10, fill:"var(--muted-foreground)" }}/>
            <Tooltip formatter={(v, n) => [`${v} meses`, n]} contentStyle={{ borderRadius:8, fontSize:12 }}/>
            <Legend wrapperStyle={{ fontSize:11 }}/>
            {(nivel === "Todos" || nivel === "Mestrado") && <Line type="monotone" dataKey="mestrado" name="Mestrado" stroke="#123C7A" strokeWidth={2.5} dot={{ fill:"#123C7A", r:4 }} activeDot={{ r:6 }}/>}
            {(nivel === "Todos" || nivel === "Doutorado") && <Line type="monotone" dataKey="doutorado" name="Doutorado" stroke="#1F8A70" strokeWidth={2.5} dot={{ fill:"#1F8A70", r:4 }} activeDot={{ r:6 }}/>}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              {["Aluno","Nível","Início","Conclusão","Meses","Orientador"].map(h => (
                <th key={h} className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredStudents.map((s, i) => (
              <tr key={i} style={{ borderBottom:"1px solid var(--border)" }}>
                <td className="px-3 py-2.5" style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{s.nome}</td>
                <td className="px-3 py-2.5"><StatusPill status={s.nivel}/></td>
                <td className="px-3 py-2.5" style={{ fontSize:12, color:"var(--muted-foreground)" }}>{s.inicio}</td>
                <td className="px-3 py-2.5" style={{ fontSize:12, color:"var(--muted-foreground)" }}>{s.fim}</td>
                <td className="px-3 py-2.5"><span style={{ fontSize:14, fontWeight:800, color:s.meses<=24?"#1F8A70":s.meses<=48?"#D4A017":"#dc2626" }}>{s.meses}</span><span style={{ fontSize:10, color:"var(--muted-foreground)" }}> m</span></td>
                <td className="px-3 py-2.5" style={{ fontSize:11, color:"var(--muted-foreground)" }}>{s.orientador.split(" ").slice(0,3).join(" ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Report: Produção por Aluno ───────────────────────────────────────────────

function ProducaoPorAlunoReport() {
  const [search, setSearch] = useState("");
  const [nivel, setNivel] = useState("Todos");
  const [sortK, setSortK] = useState("total");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = PROD_ALUNO;
    if (nivel !== "Todos") d = d.filter(s => s.nivel === nivel);
    if (search) d = d.filter(s => s.nome.toLowerCase().includes(search.toLowerCase()));
    return [...d].sort((a, b) => { const av=(a as any)[sortK]; const bv=(b as any)[sortK]; return sortD==="asc"?(av>bv?1:-1):(av<bv?1:-1); });
  }, [search, nivel, sortK, sortD]);

  const selStudent = PROD_ALUNO.find(s => s.nome === sel);
  const chartData = filtered.slice(0,8).map(s => ({ nome:s.nome.split(" ")[0], A1:s.a1, A2:s.a2, B1:s.b1, B2:s.b2 }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 flex-wrap items-center">
          <SearchBox value={search} onChange={setSearch}/>
          <FSelect label="Nível" value={nivel} onChange={setNivel} options={["Todos","Mestrado","Doutorado"]}/>
        </div>
        <ExportBar title="Produção por Aluno"/>
      </div>
      <div className="rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Artigos por Aluno (Qualis)</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ bottom:10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
            <XAxis dataKey="nome" tick={{ fontSize:10, fill:"var(--foreground)" }}/>
            <YAxis tick={{ fontSize:10, fill:"var(--muted-foreground)" }}/>
            <Tooltip contentStyle={{ borderRadius:8, fontSize:12 }}/>
            <Legend wrapperStyle={{ fontSize:11 }}/>
            <Bar dataKey="A1" fill="#123C7A" radius={[3,3,0,0]} stackId="a"/>
            <Bar dataKey="A2" fill="#1F8A70" radius={[0,0,0,0]} stackId="a"/>
            <Bar dataKey="B1" fill="#D4A017" radius={[0,0,0,0]} stackId="a"/>
            <Bar dataKey="B2" fill="#94a3b8" radius={[0,0,3,3]} stackId="a"/>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              <SortTh sKey="nome" active={sortK} dir={sortD} onSort={onSort}>Aluno</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Nível</th>
              <SortTh sKey="a1" active={sortK} dir={sortD} onSort={onSort}>A1</SortTh>
              <SortTh sKey="a2" active={sortK} dir={sortD} onSort={onSort}>A2</SortTh>
              <SortTh sKey="b1" active={sortK} dir={sortD} onSort={onSort}>B1</SortTh>
              <SortTh sKey="b2" active={sortK} dir={sortD} onSort={onSort}>B2</SortTh>
              <SortTh sKey="software" active={sortK} dir={sortD} onSort={onSort}>Soft.</SortTh>
              <SortTh sKey="patente" active={sortK} dir={sortD} onSort={onSort}>Pat.</SortTh>
              <SortTh sKey="total" active={sortK} dir={sortD} onSort={onSort}>Total</SortTh>
              <th className="px-3 py-2.5"/>
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <React.Fragment key={s.nome}>
                <tr onClick={() => setSel(sel === s.nome ? null : s.nome)} className="cursor-pointer" style={{ borderBottom:"1px solid var(--border)", background:sel===s.nome?"#eef3fc":"transparent" }}>
                  <td className="px-3 py-2.5"><p style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{s.nome}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>{s.orientador.split(" ").slice(-2).join(" ")}</p></td>
                  <td className="px-3 py-2.5"><StatusPill status={s.nivel}/></td>
                  {[s.a1,s.a2,s.b1,s.b2,s.software,s.patente].map((v, i) => (
                    <td key={i} className="px-3 py-2.5 text-center"><span style={{ fontSize:13, fontWeight:700, color:v>0?"var(--foreground)":"var(--muted-foreground)" }}>{v}</span></td>
                  ))}
                  <td className="px-3 py-2.5 text-center"><span style={{ fontSize:15, fontWeight:900, color:"#123C7A" }}>{s.total}</span></td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color:"var(--muted-foreground)", transform: sel===s.nome?"rotate(90deg)":"none", transition:"transform 0.2s" }}/></td>
                </tr>
                {sel === s.nome && selStudent && (
                  <tr><td colSpan={10} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background:"#eef3fc", border:"1px solid #b8cef7" }}>
                      <p style={{ fontSize:12, fontWeight:700, color:"#123C7A", marginBottom:8 }}>Detalhes de produção — {selStudent.nome}</p>
                      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                        {[["A1",selStudent.a1,"#123C7A"],["A2",selStudent.a2,"#1F8A70"],["B1",selStudent.b1,"#D4A017"],["B2",selStudent.b2,"#94a3b8"],["Software",selStudent.software,"#0891b2"],["Patente",selStudent.patente,"#8b5cf6"]].map(([l,v,c]) => (
                          <div key={l as string} className="rounded-xl p-3 text-center" style={{ background:"var(--card)" }}>
                            <p style={{ fontSize:20, fontWeight:900, color:c as string }}>{v as number}</p>
                            <p style={{ fontSize:10, color:"var(--muted-foreground)" }}>{l as string}</p>
                          </div>
                        ))}
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

// ─── Report: Produção por Professor ───────────────────────────────────────────

function ProducaoPorProfReport() {
  const [depto, setDepto] = useState("Todos");
  const [sortK, setSortK] = useState("total");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = PROD_PROF;
    if (depto !== "Todos") d = d.filter(p => p.depto === depto);
    return [...d].sort((a, b) => { const av=(a as any)[sortK]; const bv=(b as any)[sortK]; return sortD==="asc"?(av>bv?1:-1):(av<bv?1:-1); });
  }, [depto, sortK, sortD]);

  const selProf = PROD_PROF.find(p => p.nome === sel);
  const chartData = filtered.map(p => ({ nome: p.nome.split(" ").slice(-1)[0], A1:p.a1, A2:p.a2, B1:p.b1, B2:p.b2 }));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <FSelect label="Departamento" value={depto} onChange={setDepto} options={["Todos","CC","EE"]}/>
        <ExportBar title="Produção por Professor"/>
      </div>
      <div className="rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
        <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Publicações por Orientador</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
            <XAxis dataKey="nome" tick={{ fontSize:10, fill:"var(--foreground)" }}/>
            <YAxis tick={{ fontSize:10, fill:"var(--muted-foreground)" }}/>
            <Tooltip contentStyle={{ borderRadius:8, fontSize:12 }}/>
            <Legend wrapperStyle={{ fontSize:11 }}/>
            <Bar dataKey="A1" fill="#123C7A" stackId="a" radius={[0,0,0,0]}/>
            <Bar dataKey="A2" fill="#1F8A70" stackId="a"/>
            <Bar dataKey="B1" fill="#D4A017" stackId="a"/>
            <Bar dataKey="B2" fill="#94a3b8" stackId="a" radius={[3,3,0,0]}/>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              <SortTh sKey="nome" active={sortK} dir={sortD} onSort={onSort}>Professor</SortTh>
              <SortTh sKey="orientandos" active={sortK} dir={sortD} onSort={onSort}>Orient.</SortTh>
              <SortTh sKey="a1" active={sortK} dir={sortD} onSort={onSort}>A1</SortTh>
              <SortTh sKey="a2" active={sortK} dir={sortD} onSort={onSort}>A2</SortTh>
              <SortTh sKey="b1" active={sortK} dir={sortD} onSort={onSort}>B1</SortTh>
              <SortTh sKey="b2" active={sortK} dir={sortD} onSort={onSort}>B2</SortTh>
              <SortTh sKey="software" active={sortK} dir={sortD} onSort={onSort}>Soft.</SortTh>
              <SortTh sKey="patente" active={sortK} dir={sortD} onSort={onSort}>Pat.</SortTh>
              <SortTh sKey="total" active={sortK} dir={sortD} onSort={onSort}>Total</SortTh>
              <th className="px-3 py-2.5"/>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <React.Fragment key={p.nome}>
                <tr onClick={() => setSel(sel===p.nome?null:p.nome)} className="cursor-pointer" style={{ borderBottom:"1px solid var(--border)", background:sel===p.nome?"#eef3fc":"transparent" }}>
                  <td className="px-3 py-2.5"><p style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{p.nome}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>Depto. {p.depto}</p></td>
                  <td className="px-3 py-2.5 text-center" style={{ fontSize:13, fontWeight:700, color:"#123C7A" }}>{p.orientandos}</td>
                  {[p.a1,p.a2,p.b1,p.b2,p.software,p.patente].map((v, i) => (
                    <td key={i} className="px-3 py-2.5 text-center"><span style={{ fontSize:13, fontWeight:600, color:v>0?"var(--foreground)":"var(--muted-foreground)" }}>{v}</span></td>
                  ))}
                  <td className="px-3 py-2.5 text-center"><span style={{ fontSize:15, fontWeight:900, color:"#0891b2" }}>{p.total}</span></td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color:"var(--muted-foreground)", transform:sel===p.nome?"rotate(90deg)":"none", transition:"transform 0.2s" }}/></td>
                </tr>
                {sel === p.nome && selProf && (
                  <tr><td colSpan={10} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background:"#e0f7fa", border:"1px solid #99d8e8" }}>
                      <p style={{ fontSize:12, fontWeight:700, color:"#0891b2", marginBottom:8 }}>Resumo — {selProf.nome}</p>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                        <div className="rounded-xl p-3 text-center" style={{ background:"var(--card)" }}><p style={{ fontSize:20, fontWeight:900, color:"#123C7A" }}>{selProf.a1+selProf.a2}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>Qualis A</p></div>
                        <div className="rounded-xl p-3 text-center" style={{ background:"var(--card)" }}><p style={{ fontSize:20, fontWeight:900, color:"#D4A017" }}>{selProf.b1+selProf.b2}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>Qualis B</p></div>
                        <div className="rounded-xl p-3 text-center" style={{ background:"var(--card)" }}><p style={{ fontSize:20, fontWeight:900, color:"#0891b2" }}>{selProf.software}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>Software</p></div>
                        <div className="rounded-xl p-3 text-center" style={{ background:"var(--card)" }}><p style={{ fontSize:20, fontWeight:900, color:"#8b5cf6" }}>{selProf.patente}</p><p style={{ fontSize:10, color:"var(--muted-foreground)" }}>Patentes</p></div>
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

// ─── Report: Histórico de Prorrogações ────────────────────────────────────────

function HistoricoProrrogacoesReport() {
  const [status, setStatus] = useState("Todos");
  const [nivel, setNivel] = useState("Todos");
  const [search, setSearch] = useState("");
  const [sortK, setSortK] = useState("meses");
  const [sortD, setSortD] = useState<SortDir>("desc");
  const [sel, setSel] = useState<string | null>(null);

  function onSort(k: string) { if (sortK === k) setSortD(d => d === "asc" ? "desc" : "asc"); else { setSortK(k); setSortD("desc"); } }

  const filtered = useMemo(() => {
    let d = PRORROGACOES;
    if (status !== "Todos") d = d.filter(p => p.status === status);
    if (nivel !== "Todos") d = d.filter(p => p.nivel === nivel);
    if (search) d = d.filter(p => p.aluno.toLowerCase().includes(search.toLowerCase()));
    return [...d].sort((a, b) => { const av=(a as any)[sortK]; const bv=(b as any)[sortK]; return sortD==="asc"?(av>bv?1:-1):(av<bv?1:-1); });
  }, [status, nivel, search, sortK, sortD]);

  const selItem = PRORROGACOES.find(p => p.id === sel);

  const counts = { aprovada: PRORROGACOES.filter(p=>p.status==="aprovada").length, pendente: PRORROGACOES.filter(p=>p.status==="pendente").length, negada: PRORROGACOES.filter(p=>p.status==="negada").length };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-3 flex-wrap items-center">
          <SearchBox value={search} onChange={setSearch}/>
          <FSelect label="Status" value={status} onChange={setStatus} options={["Todos","aprovada","pendente","negada"]}/>
          <FSelect label="Nível" value={nivel} onChange={setNivel} options={["Todos","Mestrado","Doutorado"]}/>
        </div>
        <ExportBar title="Histórico de Prorrogações"/>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 rounded-2xl p-5" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
          <p style={{ fontSize:13, fontWeight:700, color:"var(--foreground)", marginBottom:12 }}>Prorrogações por Período</p>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={PRORR_HISTORICO}>
              <defs><linearGradient id="gradPr" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ea580c" stopOpacity={0.3}/><stop offset="95%" stopColor="#ea580c" stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)"/>
              <XAxis dataKey="periodo" tick={{ fontSize:9, fill:"var(--muted-foreground)" }}/>
              <YAxis tick={{ fontSize:10, fill:"var(--muted-foreground)" }}/>
              <Tooltip contentStyle={{ borderRadius:8, fontSize:12 }}/>
              <Area type="monotone" dataKey="total" name="Prorrogações" stroke="#ea580c" fill="url(#gradPr)" strokeWidth={2.5}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3">
          {[{ l:"Aprovadas", n:counts.aprovada, c:"#1F8A70", bg:"#dcfce7" },{ l:"Pendentes", n:counts.pendente, c:"#D4A017", bg:"#fef9c3" },{ l:"Negadas", n:counts.negada, c:"#dc2626", bg:"#fee2e2" }].map(s => (
            <div key={s.l} className="rounded-xl p-4" style={{ background:s.bg, border:`1px solid ${s.c}30` }}>
              <p style={{ fontSize:28, fontWeight:900, color:s.c }}>{s.n}</p>
              <p style={{ fontSize:11, color:s.c }}>{s.l}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl overflow-hidden" style={{ border:"1px solid var(--border)" }}>
        <table className="w-full" style={{ borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ background:"var(--muted)" }}>
              <SortTh sKey="aluno" active={sortK} dir={sortD} onSort={onSort}>Aluno</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Orientador</th>
              <SortTh sKey="nivel" active={sortK} dir={sortD} onSort={onSort}>Nível</SortTh>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Prazo Original</th>
              <th className="px-3 py-2.5 text-left" style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Novo Prazo</th>
              <SortTh sKey="meses" active={sortK} dir={sortD} onSort={onSort}>Meses</SortTh>
              <SortTh sKey="status" active={sortK} dir={sortD} onSort={onSort}>Status</SortTh>
              <th className="px-3 py-2.5"/>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <React.Fragment key={p.id}>
                <tr onClick={() => setSel(sel===p.id?null:p.id)} className="cursor-pointer" style={{ borderBottom:"1px solid var(--border)", background:sel===p.id?"#fff7ed":"transparent" }}>
                  <td className="px-3 py-2.5" style={{ fontSize:13, fontWeight:600, color:"var(--foreground)" }}>{p.aluno}</td>
                  <td className="px-3 py-2.5" style={{ fontSize:11, color:"var(--muted-foreground)" }}>{p.orientador.split(" ").slice(0,3).join(" ")}</td>
                  <td className="px-3 py-2.5"><StatusPill status={p.nivel}/></td>
                  <td className="px-3 py-2.5" style={{ fontSize:12, color:"var(--muted-foreground)" }}>{p.prazoOriginal}</td>
                  <td className="px-3 py-2.5" style={{ fontSize:12, fontWeight:600, color:"var(--foreground)" }}>{p.novoPrazo}</td>
                  <td className="px-3 py-2.5"><span style={{ fontSize:14, fontWeight:800, color:p.meses>=12?"#dc2626":p.meses>=6?"#D4A017":"#1F8A70" }}>+{p.meses}m</span></td>
                  <td className="px-3 py-2.5"><StatusPill status={p.status}/></td>
                  <td className="px-3 py-2.5"><ChevronRight size={13} style={{ color:"var(--muted-foreground)", transform:sel===p.id?"rotate(90deg)":"none", transition:"transform 0.2s" }}/></td>
                </tr>
                {sel === p.id && selItem && (
                  <tr><td colSpan={8} className="px-3 py-0">
                    <div className="rounded-xl p-4 my-2" style={{ background:"#fff7ed", border:"1px solid #fdba74" }}>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                        <div><p style={{ fontSize:10, color:"#ea580c", fontWeight:600 }}>MOTIVO</p><p style={{ fontSize:12, color:"var(--foreground)", marginTop:2 }}>{selItem.motivo}</p></div>
                        <div><p style={{ fontSize:10, color:"#ea580c", fontWeight:600 }}>PROTOCOLO</p><p style={{ fontSize:12, color:"var(--foreground)", marginTop:2 }}>{selItem.protocolo}</p></div>
                        <div><p style={{ fontSize:10, color:"#ea580c", fontWeight:600 }}>APROVADO POR</p><p style={{ fontSize:12, color:"var(--foreground)", marginTop:2 }}>{selItem.aprovadoPor}</p></div>
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

function renderReport(id: string) {
  switch (id) {
    case "atraso":     return <AlunosAtrasoReport/>;
    case "status":     return <AlunosPorStatusReport/>;
    case "orientador": return <AlunosPorOrientadorReport/>;
    case "tempo":      return <TempoIntegralizacaoReport/>;
    case "prod-aluno": return <ProducaoPorAlunoReport/>;
    case "prod-prof":  return <ProducaoPorProfReport/>;
    case "prorrog":    return <HistoricoProrrogacoesReport/>;
    default:           return null;
  }
}

function ReportModal({ reportId, onClose }: { reportId: string; onClose: () => void }) {
  const cfg = REPORTS.find(r => r.id === reportId)!;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background:"rgba(0,0,0,0.5)" }} onClick={onClose}>
      <div className="w-full max-w-6xl max-h-[92vh] flex flex-col rounded-2xl" style={{ background:"var(--background)", boxShadow:"0 24px 80px rgba(0,0,0,0.25)" }} onClick={e => e.stopPropagation()}>
        {/* Modal header */}
        <div className="flex items-center gap-4 px-6 py-4 flex-shrink-0" style={{ background:"var(--card)", borderRadius:"16px 16px 0 0", borderBottom:"1px solid var(--border)" }}>
          <div className="rounded-xl p-2.5 flex-shrink-0" style={{ background:cfg.bg, border:`1px solid ${cfg.border}` }}>
            <span style={{ color:cfg.color }}>{cfg.icon}</span>
          </div>
          <div className="flex-1 min-w-0">
            <h2 style={{ fontSize:18, fontWeight:800, color:"var(--foreground)" }}>{cfg.title}</h2>
            <p style={{ fontSize:12, color:"var(--muted-foreground)" }}>{cfg.desc}</p>
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="text-right">
              <p style={{ fontSize:24, fontWeight:900, color:cfg.color }}>{cfg.stat}</p>
              <p style={{ fontSize:10, color:"var(--muted-foreground)" }}>{cfg.statLabel}</p>
            </div>
            <button onClick={onClose} className="rounded-xl p-2.5" style={{ background:"var(--muted)", color:"var(--muted-foreground)" }}><X size={16}/></button>
          </div>
        </div>
        {/* Modal body */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderReport(reportId)}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const SUMMARY_STATS = [
  { label:"Total de Alunos", value:"72", color:"#123C7A" },
  { label:"Em Risco",        value:"8",  color:"#dc2626" },
  { label:"Prorrogações",    value:"9",  color:"#ea580c" },
  { label:"Publicações",     value:"302",color:"#1F8A70" },
];

export function ReportsPage() {
  const [openReport, setOpenReport] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 style={{ color:"var(--foreground)", marginBottom:4 }}>Relatórios Gerenciais</h1>
          <p style={{ color:"var(--muted-foreground)", fontSize:14 }}>Análises detalhadas com gráficos, tabelas e drill-down por categoria</p>
        </div>
        <div className="flex gap-2">
          {[["PDF","#dc2626"],["Excel","#1F8A70"],["CSV","#123C7A"]].map(([fmt,c]) => (
            <button key={fmt} onClick={() => showToast(`Exportando relatório completo como ${fmt}...`, c)}
              className="flex items-center gap-1.5 rounded-xl px-3 py-2" style={{ background:`${c}10`, color:c, border:`1px solid ${c}30`, fontSize:12, fontWeight:700 }}>
              <Download size={12}/> {fmt}
            </button>
          ))}
        </div>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {SUMMARY_STATS.map(s => (
          <div key={s.label} className="rounded-2xl p-4" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
            <p style={{ fontSize:32, fontWeight:900, color:s.color }}>{s.value}</p>
            <p style={{ fontSize:12, color:"var(--muted-foreground)", marginTop:2 }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Report Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {REPORTS.map(r => (
          <div key={r.id} className="rounded-2xl p-5 flex flex-col" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
            <div className="flex items-start justify-between mb-4">
              <div className="rounded-xl p-2.5" style={{ background:r.bg, border:`1px solid ${r.border}` }}>
                <span style={{ color:r.color }}>{r.icon}</span>
              </div>
              <div className="text-right">
                <p style={{ fontSize:22, fontWeight:900, color:r.color }}>{r.stat}</p>
                <p style={{ fontSize:9, color:"var(--muted-foreground)" }}>{r.statLabel}</p>
              </div>
            </div>
            <p style={{ fontSize:14, fontWeight:700, color:"var(--foreground)", marginBottom:4 }}>{r.title}</p>
            <p style={{ fontSize:11, color:"var(--muted-foreground)", lineHeight:1.5, flex:1, marginBottom:16 }}>{r.desc}</p>
            <button onClick={() => setOpenReport(r.id)}
              className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 transition-all"
              style={{ background:r.color, color:"#fff", fontSize:12, fontWeight:700 }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "0.9")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "1")}>
              <Eye size={13}/> Abrir Relatório
            </button>
          </div>
        ))}
        {/* Extra: full summary card */}
        <div className="rounded-2xl p-5 flex flex-col" style={{ background:"linear-gradient(135deg, var(--brand-blue) 0%, var(--brand-blue-dark) 100%)", border:"1px solid var(--brand-blue-light)", boxShadow:"var(--elevation-card-shadow)" }}>
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-xl p-2.5" style={{ background:"rgba(255,255,255,0.15)" }}>
              <FileText size={20} style={{ color:"#D4A017" }}/>
            </div>
          </div>
          <p style={{ fontSize:14, fontWeight:700, color:"#fff", marginBottom:4 }}>Relatório Consolidado</p>
          <p style={{ fontSize:11, color:"rgba(255,255,255,0.7)", lineHeight:1.5, flex:1, marginBottom:16 }}>Exportar todos os relatórios combinados em um único documento</p>
          <div className="space-y-2">
            {[["PDF Completo","#D4A017"],["Excel Consolidado","#fff"],["CSV Geral","rgba(255,255,255,0.7)"]].map(([l,c]) => (
              <button key={l} onClick={() => showToast(`Gerando ${l}...`, "#123C7A")} className="w-full flex items-center justify-center gap-2 rounded-xl py-2 transition-all"
                style={{ background:"rgba(255,255,255,0.1)", color:c, fontSize:11, fontWeight:700, border:`1px solid ${c}30` }}>
                <Download size={11}/> {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {openReport && <ReportModal reportId={openReport} onClose={() => setOpenReport(null)}/>}
    </div>
  );
}

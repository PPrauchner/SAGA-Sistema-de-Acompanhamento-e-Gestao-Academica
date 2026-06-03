import React, { useState, useMemo } from "react";
import {
  Plus, Edit2, X, ChevronLeft, ChevronRight, Clock, User,
  MessageSquare, Activity, CheckCircle2, Circle, XCircle, Send,
  BookOpen, FlaskConical, FileText, GraduationCap, Layers, Flag,
  AlignLeft, BarChart2, Calendar, Tag, Columns, Search,
} from "lucide-react";
import { useApp } from "../../context/AppContext";

// ─── Types ────────────────────────────────────────────────────────────────────

type TaskStatus = "pendente" | "em-andamento" | "concluida" | "bloqueada";
type Priority   = "urgente" | "alta" | "media" | "baixa";
type ViewType   = "kanban" | "timeline" | "gantt" | "calendario";
type ModalState =
  | { kind: "detail";    task: Task }
  | { kind: "task-form"; task?: Task; stageId?: string }
  | { kind: "plan-form" }
  | null;

interface Comentario  { id: string; autor: string; avatar: string; texto: string; data: string; }
interface Atualizacao { id: string; campo: string; anterior: string; novo: string; data: string; autor: string; }
interface Task {
  id: string; stageId: string; titulo: string; descricao: string;
  responsavel: string; responsavelAvatar: string; prazo: string;
  status: TaskStatus; prioridade: Priority; progresso: number; tags: string[];
  comentarios: Comentario[]; atualizacoes: Atualizacao[];
}
interface Stage {
  id: string; nome: string; cor: string; bgCor: string; borderCor: string;
  icon: React.ReactNode; descricao: string; inicio: string; fim: string;
  progresso: number; ordem: number;
}
interface WorkPlanData {
  titulo: string; aluno: string; orientador: string; programa: string;
  inicio: string; fim: string; progresso: number; descricao: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PLAN_START   = "2025-01";
const PLAN_MONTHS  = 24;
const CURRENT_MONTH = 18; // June 2026

const STATUS_CFG: Record<TaskStatus, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  concluida:      { label: "Concluída",     color: "var(--tint-teal-text)",   bg: "var(--tint-teal-bg)",   icon: <CheckCircle2 size={11} /> },
  "em-andamento": { label: "Em Andamento",  color: "var(--tint-blue-text)",   bg: "var(--tint-blue-bg)",   icon: <Circle       size={11} /> },
  pendente:       { label: "Pendente",      color: "var(--muted-foreground)", bg: "var(--muted)",          icon: <Circle       size={11} /> },
  bloqueada:      { label: "Bloqueada",     color: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)", icon: <XCircle      size={11} /> },
};
const PRIORITY_CFG: Record<Priority, { label: string; color: string; bg: string }> = {
  urgente: { label: "Urgente", color: "var(--tint-danger-text)", bg: "var(--tint-danger-bg)" },
  alta:    { label: "Alta",    color: "var(--tint-orange-text)", bg: "var(--tint-orange-bg)" },
  media:   { label: "Média",   color: "var(--tint-gold-text)",   bg: "var(--tint-gold-bg)" },
  baixa:   { label: "Baixa",   color: "#64748b", bg: "#f1f5f9" },
};

// ─── Data ─────────────────────────────────────────────────────────────────────

const INITIAL_STAGES: Stage[] = [
  { id:"revisao",         nome:"Revisão Bibliográfica", cor:"#8b5cf6", bgCor:"#f5f3ff", borderCor:"#ddd6fe", icon:<BookOpen       size={14}/>, descricao:"Levantamento e síntese do estado da arte",            inicio:"2025-01", fim:"2025-04", progresso:100, ordem:1 },
  { id:"problema",        nome:"Definição do Problema", cor:"#123C7A", bgCor:"#eef3fc", borderCor:"#c7d9f5", icon:<AlignLeft      size={14}/>, descricao:"Formulação da pergunta e hipóteses de pesquisa",      inicio:"2025-03", fim:"2025-07", progresso:100, ordem:2 },
  { id:"desenvolvimento", nome:"Desenvolvimento",        cor:"#1F8A70", bgCor:"#f0fdf4", borderCor:"#bbf7d0", icon:<Layers         size={14}/>, descricao:"Implementação e construção da proposta",             inicio:"2025-06", fim:"2026-03", progresso:75,  ordem:3 },
  { id:"qualificacao",    nome:"Qualificação",           cor:"#D4A017", bgCor:"#fffbeb", borderCor:"#fde68a", icon:<GraduationCap  size={14}/>, descricao:"Apresentação e aprovação do projeto à banca",        inicio:"2025-10", fim:"2025-12", progresso:100, ordem:4 },
  { id:"experimentos",    nome:"Experimentos",           cor:"#f97316", bgCor:"#fff7ed", borderCor:"#fed7aa", icon:<FlaskConical   size={14}/>, descricao:"Execução e análise dos experimentos",                inicio:"2025-12", fim:"2026-08", progresso:40,  ordem:5 },
  { id:"escrita",         nome:"Escrita",                cor:"#06b6d4", bgCor:"#ecfeff", borderCor:"#a5f3fc", icon:<FileText       size={14}/>, descricao:"Redação da dissertação/tese",                        inicio:"2026-04", fim:"2026-10", progresso:15,  ordem:6 },
  { id:"defesa",          nome:"Defesa",                 cor:"#10b981", bgCor:"#f0fdf4", borderCor:"#6ee7b7", icon:<Flag           size={14}/>, descricao:"Defesa pública e depósito final",                    inicio:"2026-10", fim:"2026-12", progresso:0,   ordem:7 },
];

const INITIAL_PLAN: WorkPlanData = {
  titulo: "Algoritmos de Aprendizado Profundo para Sistemas Embarcados",
  aluno: "Lucas Ferreira Silva", orientador: "Profa. Dra. Carla Mendes",
  programa: "PPGCC — Mestrado", inicio: "2025-01", fim: "2026-12", progresso: 62,
  descricao: "Pesquisa focada no desenvolvimento e análise de algoritmos de aprendizado profundo otimizados para sistemas embarcados de baixo consumo energético, com aplicações em IoT e computação de borda.",
};

const INITIAL_TASKS: Task[] = [
  // Revisão Bibliográfica
  { id:"t1",  stageId:"revisao",         titulo:"Levantamento de artigos seminais em DNN",         descricao:"Identificar os principais artigos fundadores na área de redes neurais profundas aplicadas a sistemas embarcados.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-02-28", status:"concluida",    prioridade:"alta",   progresso:100, tags:["literatura","DNN"],
    comentarios:[{id:"c1",autor:"Lucas Ferreira",avatar:"L",texto:"Encontrei 47 artigos relevantes no IEEE e ACM.",data:"12/02/2025"},{id:"c2",autor:"Profa. Carla",avatar:"C",texto:"Ótimo! Inclua também os da NeurIPS 2023.",data:"13/02/2025"}],
    atualizacoes:[{id:"u1",campo:"Status",anterior:"pendente",novo:"em-andamento",data:"01/02/2025",autor:"Lucas"},{id:"u2",campo:"Status",anterior:"em-andamento",novo:"concluida",data:"28/02/2025",autor:"Lucas"}]},
  { id:"t2",  stageId:"revisao",         titulo:"Levantamento bibliográfico em IoT e Edge",        descricao:"Revisar literatura sobre otimização de redes para dispositivos de borda.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-03-15", status:"concluida",    prioridade:"alta",   progresso:100, tags:["IoT","edge"],       comentarios:[], atualizacoes:[] },
  { id:"t3",  stageId:"revisao",         titulo:"Fichamento e síntese da literatura",              descricao:"Consolidar as principais contribuições em um documento de síntese.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-04-01", status:"concluida",    prioridade:"media",  progresso:100, tags:["síntese"],           comentarios:[], atualizacoes:[] },
  { id:"t4",  stageId:"revisao",         titulo:"Relatório de revisão bibliográfica",              descricao:"Escrever o relatório formal de revisão para aprovação do orientador.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-04-20", status:"concluida",    prioridade:"alta",   progresso:100, tags:["relatório"],
    comentarios:[{id:"c3",autor:"Profa. Carla",avatar:"C",texto:"Aprovado! Excelente trabalho.",data:"22/04/2025"}], atualizacoes:[] },
  // Definição do Problema
  { id:"t5",  stageId:"problema",        titulo:"Identificação do gap de pesquisa",                descricao:"Analisar a literatura e identificar as lacunas que a pesquisa irá abordar.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-04-30", status:"concluida",    prioridade:"urgente", progresso:100, tags:["gap","pesquisa"],   comentarios:[], atualizacoes:[] },
  { id:"t6",  stageId:"problema",        titulo:"Formulação da pergunta de pesquisa",              descricao:"Definir formalmente a pergunta central da dissertação.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-05-15", status:"concluida",    prioridade:"urgente", progresso:100, tags:["metodologia"],      comentarios:[], atualizacoes:[] },
  { id:"t7",  stageId:"problema",        titulo:"Definição de hipóteses e objetivos",              descricao:"Formular hipóteses testáveis e objetivos específicos da pesquisa.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-06-01", status:"concluida",    prioridade:"alta",   progresso:100, tags:["hipóteses"],        comentarios:[], atualizacoes:[] },
  { id:"t8",  stageId:"problema",        titulo:"Documento de definição do problema",              descricao:"Produzir documento formal de definição aprovado pelo orientador.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-07-10", status:"concluida",    prioridade:"alta",   progresso:100, tags:["documento"],        comentarios:[], atualizacoes:[] },
  // Desenvolvimento
  { id:"t9",  stageId:"desenvolvimento", titulo:"Arquitetura base do modelo proposto",             descricao:"Desenhar e implementar a arquitetura inicial do modelo de DNN otimizado.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-07-30", status:"concluida",    prioridade:"urgente", progresso:100, tags:["arquitetura","DNN"], comentarios:[], atualizacoes:[] },
  { id:"t10", stageId:"desenvolvimento", titulo:"Pipeline de pré-processamento de dados",          descricao:"Implementar pipeline completo de ingestão e pré-processamento dos datasets.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-09-15", status:"concluida",    prioridade:"alta",   progresso:100, tags:["pipeline","dados"], comentarios:[], atualizacoes:[] },
  { id:"t11", stageId:"desenvolvimento", titulo:"Módulo de compressão e quantização",              descricao:"Implementar técnicas de compressão da rede neural para execução em hardware limitado.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-06-30", status:"em-andamento", prioridade:"urgente", progresso:55, tags:["compressão","quantização"],
    comentarios:[{id:"c4",autor:"Lucas Ferreira",avatar:"L",texto:"Desafios com a quantização INT4 — precisão abaixo do esperado.",data:"20/05/2026"},{id:"c5",autor:"Profa. Carla",avatar:"C",texto:"Tente quantization-aware training. Discutimos na sexta.",data:"21/05/2026"},{id:"c6",autor:"Lucas Ferreira",avatar:"L",texto:"Implementei QAT, resultados melhoraram 3,2pp de acurácia!",data:"01/06/2026"}],
    atualizacoes:[{id:"u4",campo:"Status",anterior:"pendente",novo:"em-andamento",data:"15/04/2026",autor:"Lucas"},{id:"u5",campo:"Prazo",anterior:"2026-05-30",novo:"2026-06-30",data:"22/05/2026",autor:"Profa. Carla"},{id:"u6",campo:"Progresso",anterior:"30%",novo:"55%",data:"01/06/2026",autor:"Lucas"}]},
  { id:"t12", stageId:"desenvolvimento", titulo:"Implementação das métricas de avaliação",         descricao:"Codificar todas as métricas: latência, throughput, acurácia e consumo de energia.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-07-15", status:"em-andamento", prioridade:"alta",   progresso:35, tags:["métricas"], comentarios:[], atualizacoes:[] },
  { id:"t13", stageId:"desenvolvimento", titulo:"Testes unitários e integração",                   descricao:"Cobrir com testes unitários todos os módulos do sistema.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-08-30", status:"pendente",    prioridade:"media",  progresso:0,  tags:["testes"],   comentarios:[], atualizacoes:[] },
  // Qualificação
  { id:"t14", stageId:"qualificacao",    titulo:"Elaboração do documento de qualificação",         descricao:"Redigir o documento completo de qualificação conforme normas do programa.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-11-15", status:"concluida",    prioridade:"urgente", progresso:100, tags:["qualificação"], comentarios:[], atualizacoes:[] },
  { id:"t15", stageId:"qualificacao",    titulo:"Apresentação para banca examinadora",             descricao:"Apresentar o projeto de pesquisa à banca de qualificação.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-12-01", status:"concluida",    prioridade:"urgente", progresso:100, tags:["banca"],
    comentarios:[{id:"c7",autor:"Profa. Carla",avatar:"C",texto:"Aprovado pela banca! Parabéns, Lucas!",data:"01/12/2025"}], atualizacoes:[] },
  { id:"t16", stageId:"qualificacao",    titulo:"Revisões pós-qualificação",                       descricao:"Implementar as sugestões da banca examinadora.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2025-12-20", status:"concluida",    prioridade:"alta",   progresso:100, tags:["revisão"], comentarios:[], atualizacoes:[] },
  // Experimentos
  { id:"t17", stageId:"experimentos",    titulo:"Configuração do ambiente experimental",           descricao:"Preparar hardware (Raspberry Pi 4, Jetson Nano) e software (TensorFlow Lite, ONNX).", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-01-31", status:"concluida",    prioridade:"alta",   progresso:100, tags:["hardware","ambiente"], comentarios:[], atualizacoes:[] },
  { id:"t18", stageId:"experimentos",    titulo:"Experimentos — Benchmark baseline",               descricao:"Executar experimentos com modelos baseline (MobileNet, EfficientNet-Lite).", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-06-15", status:"em-andamento", prioridade:"urgente", progresso:70, tags:["baseline","benchmark"],
    comentarios:[{id:"c8",autor:"Lucas Ferreira",avatar:"L",texto:"Baseline com MobileNetV3 concluído. Resultados encorajadores.",data:"10/06/2026"}], atualizacoes:[] },
  { id:"t19", stageId:"experimentos",    titulo:"Experimentos — Modelo proposto",                  descricao:"Executar baterias de experimentos com o modelo desenvolvido.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-07-31", status:"pendente",    prioridade:"urgente", progresso:10, tags:["experimentos"], comentarios:[], atualizacoes:[] },
  { id:"t20", stageId:"experimentos",    titulo:"Análise comparativa de resultados",               descricao:"Comparar desempenho do modelo proposto vs. baselines em todas as métricas.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-08-15", status:"pendente",    prioridade:"alta",   progresso:0,  tags:["análise"], comentarios:[], atualizacoes:[] },
  { id:"t21", stageId:"experimentos",    titulo:"Validação estatística dos resultados",            descricao:"Aplicar testes estatísticos (Wilcoxon, t-test) para validar a superioridade do modelo.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-09-30", status:"pendente",    prioridade:"media",  progresso:0,  tags:["estatística"], comentarios:[], atualizacoes:[] },
  // Escrita
  { id:"t22", stageId:"escrita",         titulo:"Capítulo 1 — Introdução",                        descricao:"Redigir capítulo de introdução com motivação, objetivos e estrutura do trabalho.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-06-30", status:"em-andamento", prioridade:"alta",   progresso:40, tags:["escrita","introdução"], comentarios:[], atualizacoes:[] },
  { id:"t23", stageId:"escrita",         titulo:"Capítulo 2 — Revisão da Literatura",             descricao:"Expandir e formatar a revisão bibliográfica como capítulo da dissertação.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-07-31", status:"pendente",    prioridade:"alta",   progresso:0,  tags:["escrita"], comentarios:[], atualizacoes:[] },
  { id:"t24", stageId:"escrita",         titulo:"Capítulo 3 — Metodologia",                       descricao:"Descrever formalmente os métodos, datasets e protocolo experimental.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-08-31", status:"pendente",    prioridade:"alta",   progresso:0,  tags:["escrita","metodologia"], comentarios:[], atualizacoes:[] },
  { id:"t25", stageId:"escrita",         titulo:"Revisão geral e formatação ABNT",                descricao:"Revisão final do texto e formatação conforme normas ABNT do programa.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-10-15", status:"pendente",    prioridade:"media",  progresso:0,  tags:["revisão","ABNT"], comentarios:[], atualizacoes:[] },
  // Defesa
  { id:"t26", stageId:"defesa",          titulo:"Submissão da dissertação ao programa",           descricao:"Entregar versão definitiva da dissertação ao colegiado do programa.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-10-31", status:"pendente",    prioridade:"urgente", progresso:0,  tags:["submissão"], comentarios:[], atualizacoes:[] },
  { id:"t27", stageId:"defesa",          titulo:"Agendamento e composição da banca",              descricao:"Coordenar com o orientador a composição e agendamento da banca de defesa.", responsavel:"Profa. Carla Mendes", responsavelAvatar:"C", prazo:"2026-11-15", status:"pendente", prioridade:"urgente", progresso:0, tags:["banca"], comentarios:[], atualizacoes:[] },
  { id:"t28", stageId:"defesa",          titulo:"Apresentação da defesa pública",                 descricao:"Realizar a defesa pública da dissertação perante a banca examinadora.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-12-01", status:"pendente",    prioridade:"urgente", progresso:0,  tags:["defesa"], comentarios:[], atualizacoes:[] },
  { id:"t29", stageId:"defesa",          titulo:"Depósito final e publicação",                    descricao:"Realizar o depósito final da dissertação no repositório institucional.", responsavel:"Lucas Ferreira", responsavelAvatar:"L", prazo:"2026-12-20", status:"pendente",    prioridade:"alta",   progresso:0,  tags:["depósito"], comentarios:[], atualizacoes:[] },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function moFromStart(start: string, target: string) {
  const [sy, sm] = start.split("-").map(Number);
  const [ty, tm] = target.split("-").map(Number);
  return (ty - sy) * 12 + (tm - sm);
}
function fmtDate(d: string) { const [y,m,day] = d.split("-"); return `${day}/${m}/${y}`; }
function isOverdue(prazo: string, status: TaskStatus) {
  return status !== "concluida" && new Date(prazo) < new Date("2026-06-02");
}

// ─── Micro-components ─────────────────────────────────────────────────────────

function SBadge({ status }: { status: TaskStatus }) {
  const c = STATUS_CFG[status];
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg" style={{ background: c.bg, color: c.color, fontSize: 10, fontWeight: 700 }}>{c.icon} {c.label}</span>;
}
function PBadge({ priority }: { priority: Priority }) {
  const c = PRIORITY_CFG[priority];
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg" style={{ background: c.bg, color: c.color, fontSize: 10, fontWeight: 700 }}><Flag size={9}/> {c.label}</span>;
}
function PBar({ value, color, h = 6 }: { value: number; color: string; h?: number }) {
  return <div className="rounded-full overflow-hidden" style={{ height: h, background: "var(--muted)" }}><div className="h-full rounded-full" style={{ width: `${value}%`, background: color }} /></div>;
}
function Av({ text, color = "#123C7A", size = 28 }: { text: string; color?: string; size?: number }) {
  return <div className="flex items-center justify-center rounded-full flex-shrink-0" style={{ width: size, height: size, background: color, color: "#fff", fontSize: size * 0.38, fontWeight: 800 }}>{text}</div>;
}

// ─── KANBAN VIEW ──────────────────────────────────────────────────────────────

function KanbanCard({ task, stage, stages, onSelect, onMove }: {
  task: Task; stage: Stage; stages: Stage[];
  onSelect: () => void; onMove: (id: string, sid: string) => void;
}) {
  const od = isOverdue(task.prazo, task.status);
  const sorted = [...stages].sort((a,b) => a.ordem - b.ordem);
  const idx  = sorted.findIndex(s => s.id === task.stageId);
  const prev = idx > 0 ? sorted[idx-1] : null;
  const next = idx < sorted.length-1 ? sorted[idx+1] : null;
  return (
    <div className="rounded-xl p-3 cursor-pointer group"
      style={{ background:"var(--card)", border:`1px solid ${od?"#fecaca":"var(--border)"}`, boxShadow:"0 1px 4px rgba(0,0,0,0.05)" }}
      onClick={onSelect}>
      <div className="flex items-start gap-2 mb-2">
        <p style={{ fontSize:12, fontWeight:700, color:"var(--foreground)", lineHeight:1.4, flex:1 }}>{task.titulo}</p>
        <PBadge priority={task.prioridade}/>
      </div>
      <div className="mb-2"><SBadge status={task.status}/></div>
      {task.progresso > 0 && (
        <div className="mb-2">
          <div className="flex justify-between mb-1" style={{ fontSize:10 }}>
            <span style={{ color:"var(--muted-foreground)" }}>Progresso</span>
            <span style={{ fontWeight:700, color:stage.cor }}>{task.progresso}%</span>
          </div>
          <PBar value={task.progresso} color={stage.cor} h={4}/>
        </div>
      )}
      {task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {task.tags.slice(0,3).map(t => <span key={t} className="px-1.5 py-0.5 rounded" style={{ fontSize:9, fontWeight:600, background:`${stage.cor}18`, color:stage.cor }}>{t}</span>)}
        </div>
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Av text={task.responsavelAvatar} color={stage.cor} size={20}/>
          <span style={{ fontSize:10, color:"var(--muted-foreground)" }}>{task.responsavel.split(" ")[0]}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {task.comentarios.length > 0 && <span className="flex items-center gap-0.5" style={{ fontSize:10, color:"var(--muted-foreground)" }}><MessageSquare size={10}/> {task.comentarios.length}</span>}
          <span className="flex items-center gap-0.5" style={{ fontSize:10, color:od?"#dc2626":"var(--muted-foreground)", fontWeight:od?700:400 }}><Clock size={10}/> {fmtDate(task.prazo)}</span>
        </div>
      </div>
      <div className="flex gap-1.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
        {prev && <button className="flex-1 py-1 rounded-lg" style={{ background:`${prev.cor}18`, color:prev.cor, fontSize:9, fontWeight:700 }} onClick={() => onMove(task.id, prev.id)}>← {prev.nome.split(" ")[0]}</button>}
        {next && <button className="flex-1 py-1 rounded-lg" style={{ background:`${next.cor}18`, color:next.cor, fontSize:9, fontWeight:700 }} onClick={() => onMove(task.id, next.id)}>{next.nome.split(" ")[0]} →</button>}
      </div>
    </div>
  );
}

function KanbanView({ tasks, stages, onSelect, onMove, onAdd }: {
  tasks: Task[]; stages: Stage[];
  onSelect:(t:Task)=>void; onMove:(id:string,sid:string)=>void; onAdd:(sid:string)=>void;
}) {
  const sorted = [...stages].sort((a,b) => a.ordem - b.ordem);
  return (
    <div className="overflow-x-auto pb-4">
      <div className="flex gap-4" style={{ minWidth: sorted.length * 296 }}>
        {sorted.map(stage => {
          const st = tasks.filter(t => t.stageId === stage.id);
          const done = st.filter(t => t.status === "concluida").length;
          return (
            <div key={stage.id} style={{ width:280, flexShrink:0 }}>
              <div className="rounded-xl p-3 mb-3" style={{ background:`color-mix(in srgb, ${stage.cor} 12%, var(--card))`, border:`1px solid color-mix(in srgb, ${stage.cor} 35%, transparent)` }}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5"><span style={{ color:stage.cor }}>{stage.icon}</span><span style={{ fontSize:12, fontWeight:700, color:stage.cor }}>{stage.nome}</span></div>
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.5 rounded-lg" style={{ fontSize:10, fontWeight:700, background:`${stage.cor}20`, color:stage.cor }}>{done}/{st.length}</span>
                    <button onClick={() => onAdd(stage.id)} className="rounded-lg p-1" style={{ background:stage.cor, color:"#fff" }}><Plus size={11}/></button>
                  </div>
                </div>
                <PBar value={stage.progresso} color={stage.cor} h={4}/>
                <p style={{ fontSize:9, color:stage.cor, marginTop:3, fontWeight:600 }}>{stage.progresso}% concluído</p>
              </div>
              <div className="flex flex-col gap-2">
                {st.length === 0
                  ? <div className="rounded-xl p-5 text-center" style={{ border:`2px dashed ${stage.borderCor}` }}><p style={{ fontSize:11, color:"var(--muted-foreground)" }}>Sem tarefas</p><button onClick={() => onAdd(stage.id)} style={{ fontSize:11, color:stage.cor, fontWeight:700, marginTop:4 }}>+ Adicionar</button></div>
                  : st.map(task => <KanbanCard key={task.id} task={task} stage={stage} stages={stages} onSelect={() => onSelect(task)} onMove={onMove}/>)
                }
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── TIMELINE VIEW ────────────────────────────────────────────────────────────

function TimelineView({ tasks, stages, onSelect }: { tasks:Task[]; stages:Stage[]; onSelect:(t:Task)=>void }) {
  const sMap = Object.fromEntries(stages.map(s => [s.id, s]));
  const TODAY = "2026-06";
  const MN = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

  const grouped = useMemo(() => {
    const map: Record<string, Task[]> = {};
    [...tasks].sort((a,b) => a.prazo.localeCompare(b.prazo)).forEach(t => {
      const k = t.prazo.slice(0,7);
      if (!map[k]) map[k] = [];
      map[k].push(t);
    });
    return map;
  }, [tasks]);

  const keys = Object.keys(grouped).sort();
  function fmtKey(k: string) { const [y,m] = k.split("-"); return `${MN[+m-1]} ${y}`; }

  return (
    <div className="space-y-0">
      {keys.map((key, ki) => {
        const past = key < TODAY, cur = key === TODAY;
        return (
          <div key={key} className="flex gap-4">
            <div className="flex flex-col items-center" style={{ width:60, flexShrink:0 }}>
              <div className="rounded-full flex items-center justify-center flex-shrink-0 z-10"
                style={{ width:36, height:36, background:cur?"#123C7A":past?"#1F8A70":"var(--muted)", border:`2px solid ${cur?"#123C7A":past?"#1F8A70":"var(--border)"}`, color:(cur||past)?"#fff":"var(--muted-foreground)", fontSize:11, fontWeight:700 }}>
                {cur?"●":past?"✓":"○"}
              </div>
              {ki < keys.length-1 && <div className="flex-1 w-px" style={{ background:past?"#1F8A70":"var(--border)", minHeight:20, marginTop:2 }}/>}
            </div>
            <div className="flex-1 pb-6">
              <div className="flex items-center gap-2 mb-3 mt-1.5">
                <h4 style={{ fontSize:14, fontWeight:800, color:cur?"#123C7A":"var(--foreground)" }}>{fmtKey(key)}</h4>
                {cur && <span className="px-2 py-0.5 rounded-lg" style={{ fontSize:10, fontWeight:700, background:"#eef3fc", color:"#123C7A" }}>Mês atual</span>}
                <span style={{ fontSize:11, color:"var(--muted-foreground)" }}>{grouped[key].length} tarefa{grouped[key].length!==1?"s":""}</span>
              </div>
              <div className="space-y-2">
                {grouped[key].map(task => {
                  const stage = sMap[task.stageId];
                  const od = isOverdue(task.prazo, task.status);
                  return (
                    <button key={task.id} onClick={() => onSelect(task)}
                      className="w-full rounded-xl p-3 text-left transition-opacity hover:opacity-80"
                      style={{ background:"var(--card)", border:`1px solid ${od?"#fecaca":"var(--border)"}` }}>
                      <div className="flex items-center gap-3">
                        <div className="rounded-lg p-1.5 flex-shrink-0" style={{ background:stage.bgCor, color:stage.cor }}>{stage.icon}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span style={{ fontSize:13, fontWeight:700, color:"var(--foreground)" }}>{task.titulo}</span>
                            <SBadge status={task.status}/>
                            <PBadge priority={task.prioridade}/>
                            {od && <span style={{ fontSize:10, fontWeight:700, color:"#dc2626" }}>Atrasada</span>}
                          </div>
                          <p style={{ fontSize:11, color:stage.cor, fontWeight:600, marginTop:2 }}>{stage.nome}</p>
                        </div>
                        {task.progresso > 0 && (
                          <div style={{ width:48, flexShrink:0, textAlign:"center" }}>
                            <p style={{ fontSize:18, fontWeight:800, color:stage.cor, lineHeight:1 }}>{task.progresso}%</p>
                            <p style={{ fontSize:9, color:"var(--muted-foreground)" }}>progresso</p>
                          </div>
                        )}
                      </div>
                      {task.progresso > 0 && task.progresso < 100 && <div className="mt-2"><PBar value={task.progresso} color={stage.cor} h={3}/></div>}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── GANTT VIEW ───────────────────────────────────────────────────────────────

function GanttView({ stages, tasks, planStart, totalMonths, currentMonth }: {
  stages:Stage[]; tasks:Task[]; planStart:string; totalMonths:number; currentMonth:number;
}) {
  const COL = 58, LEFT = 188;
  const sorted = [...stages].sort((a,b) => a.ordem - b.ordem);
  const months = Array.from({ length:totalMonths }, (_,i) => i+1);
  const [py, pm] = planStart.split("-").map(Number);
  const MN = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

  function lbl(i: number) {
    const tot = pm + i - 1, y = py + Math.floor(tot/12), mo = tot % 12;
    return (mo===0) ? `${MN[0]} ${y}` : (i%3===0 ? MN[mo] : "");
  }
  function bar(s: Stage) {
    const l = moFromStart(planStart, s.inicio) * COL;
    const w = (moFromStart(planStart, s.fim) - moFromStart(planStart, s.inicio) + 1) * COL;
    return { l, w };
  }
  function dotL(t: Task) { return moFromStart(planStart, t.prazo.slice(0,7)) * COL + COL/2; }
  const todayL = (currentMonth - 0.5) * COL;
  const DOT_C: Record<TaskStatus, string> = { concluida:"#1F8A70", "em-andamento":"#6366f1", pendente:"#94a3b8", bloqueada:"#dc2626" };

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
      <div className="overflow-x-auto">
        <div style={{ minWidth: LEFT + totalMonths*COL }}>
          {/* Header */}
          <div className="flex" style={{ borderBottom:"1px solid var(--border)", background:"var(--muted)" }}>
            <div className="flex items-center px-3" style={{ width:LEFT, flexShrink:0, height:36 }}>
              <span style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Etapa / Período</span>
            </div>
            <div className="flex" style={{ width:totalMonths*COL }}>
              {months.map((m,i) => (
                <div key={m} style={{ width:COL, flexShrink:0, height:36, textAlign:"center", padding:"10px 2px 0", borderLeft:"1px solid var(--border)", background:m===currentMonth?"#eef3fc":"transparent" }}>
                  <span style={{ fontSize:9, fontWeight:m===currentMonth?800:400, color:m===currentMonth?"#123C7A":"var(--muted-foreground)" }}>{lbl(m)}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Rows */}
          {sorted.map((stage, si) => {
            const { l, w } = bar(stage);
            const st = tasks.filter(t => t.stageId === stage.id);
            return (
              <div key={stage.id} className="flex" style={{ borderBottom:si<sorted.length-1?"1px solid var(--border)":"none", minHeight:52 }}>
                <div className="flex items-center gap-2 px-3" style={{ width:LEFT, flexShrink:0, background:`${stage.bgCor}70` }}>
                  <span style={{ color:stage.cor, flexShrink:0 }}>{stage.icon}</span>
                  <div className="min-w-0">
                    <p style={{ fontSize:10, fontWeight:700, color:stage.cor, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{stage.nome}</p>
                    <p style={{ fontSize:9, color:"var(--muted-foreground)" }}>{stage.progresso}%</p>
                  </div>
                </div>
                <div className="relative flex-1" style={{ background:`${stage.bgCor}30` }}>
                  {months.map(m => <div key={m} className="absolute top-0 bottom-0" style={{ left:(m-1)*COL, width:1, background:"var(--border)", opacity:0.4 }}/>)}
                  <div className="absolute top-0 bottom-0 z-20" style={{ left:todayL, width:2, background:"#123C7A", opacity:0.7 }}/>
                  <div className="absolute rounded-lg overflow-hidden z-10" style={{ left:l, width:w, top:"50%", transform:"translateY(-50%)", height:20, background:`${stage.cor}22`, border:`1px solid ${stage.cor}44` }}>
                    <div className="h-full rounded-lg" style={{ width:`${stage.progresso}%`, background:`${stage.cor}55` }}/>
                  </div>
                  {st.map(t => (
                    <div key={t.id} className="absolute z-30 rounded-full" title={t.titulo}
                      style={{ left:dotL(t)-5, top:"50%", transform:"translateY(calc(-50% - 13px))", width:10, height:10, background:DOT_C[t.status], border:"2px solid var(--card)", boxShadow:"0 1px 3px rgba(0,0,0,0.2)" }}/>
                  ))}
                </div>
              </div>
            );
          })}
          {/* Legend */}
          <div className="flex items-center gap-4 px-4 py-2.5" style={{ borderTop:"1px solid var(--border)", background:"var(--muted)" }}>
            <span style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Tarefas:</span>
            {[{c:"#1F8A70",l:"Concluída"},{c:"#6366f1",l:"Em andamento"},{c:"#94a3b8",l:"Pendente"},{c:"#dc2626",l:"Bloqueada"}].map(x => (
              <div key={x.l} className="flex items-center gap-1"><div className="rounded-full" style={{ width:8,height:8,background:x.c }}/><span style={{ fontSize:10, color:"var(--muted-foreground)" }}>{x.l}</span></div>
            ))}
            <div className="flex items-center gap-1"><div style={{ width:12,height:2,background:"#123C7A" }}/><span style={{ fontSize:10, color:"var(--muted-foreground)" }}>Hoje (mês {currentMonth})</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── CALENDAR VIEW ────────────────────────────────────────────────────────────

function CalendarView({ tasks, stages, onSelect }: { tasks:Task[]; stages:Stage[]; onSelect:(t:Task)=>void }) {
  const [cal, setCal] = useState(new Date(2026,5,1));
  const sMap = Object.fromEntries(stages.map(s => [s.id, s]));
  const y = cal.getFullYear(), mo = cal.getMonth();
  const MONTHS = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
  const DAYS = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];
  const firstDay = new Date(y,mo,1).getDay();
  const daysInMonth = new Date(y,mo+1,0).getDate();

  const byDay = useMemo(() => {
    const map: Record<number, Task[]> = {};
    tasks.forEach(t => {
      const d = new Date(t.prazo + "T00:00:00");
      if (d.getFullYear()===y && d.getMonth()===mo) { const day=d.getDate(); if(!map[day]) map[day]=[]; map[day].push(t); }
    });
    return map;
  }, [tasks, y, mo]);

  const cells: number[] = [];
  for (let i=0;i<firstDay;i++) cells.push(0);
  for (let d=1;d<=daysInMonth;d++) cells.push(d);
  while (cells.length%7!==0) cells.push(0);

  const isToday = (d:number) => d===2 && y===2026 && mo===5;
  const moTasks = tasks.filter(t => { const d=new Date(t.prazo+"T00:00:00"); return d.getFullYear()===y && d.getMonth()===mo; });

  return (
    <div className="rounded-2xl overflow-hidden" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
      <div className="flex items-center justify-between p-4" style={{ borderBottom:"1px solid var(--border)" }}>
        <div>
          <h3 style={{ fontSize:16, fontWeight:800, color:"var(--foreground)" }}>{MONTHS[mo]} {y}</h3>
          <p style={{ fontSize:12, color:"var(--muted-foreground)" }}>{moTasks.length} tarefa{moTasks.length!==1?"s":""} com prazo neste mês</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setCal(new Date(y,mo-1,1))} className="rounded-xl p-2" style={{ background:"var(--muted)", border:"1px solid var(--border)" }}><ChevronLeft size={14} style={{ color:"var(--foreground)" }}/></button>
          <button onClick={() => setCal(new Date(2026,5,1))} className="px-3 py-1.5 rounded-xl" style={{ background:"var(--muted)", border:"1px solid var(--border)", fontSize:11, fontWeight:700, color:"var(--foreground)" }}>Hoje</button>
          <button onClick={() => setCal(new Date(y,mo+1,1))} className="rounded-xl p-2" style={{ background:"var(--muted)", border:"1px solid var(--border)" }}><ChevronRight size={14} style={{ color:"var(--foreground)" }}/></button>
        </div>
      </div>
      <div className="grid grid-cols-7" style={{ background:"var(--muted)", borderBottom:"1px solid var(--border)" }}>
        {DAYS.map(d => <div key={d} className="py-2 text-center" style={{ fontSize:11, fontWeight:700, color:"var(--muted-foreground)" }}>{d}</div>)}
      </div>
      <div className="grid grid-cols-7" style={{ gridAutoRows:"minmax(76px,auto)" }}>
        {cells.map((day,i) => {
          if (day===0) return <div key={i} style={{ background:"var(--muted)", opacity:0.35, borderRight:"1px solid var(--border)", borderBottom:"1px solid var(--border)" }}/>;
          const dt = byDay[day] || [];
          const td = isToday(day);
          return (
            <div key={i} className="p-1.5" style={{ borderRight:"1px solid var(--border)", borderBottom:"1px solid var(--border)", background:td?"#eef3fc":"var(--card)" }}>
              <div className="flex items-center justify-between mb-1">
                <span className="flex items-center justify-center rounded-full" style={{ width:22, height:22, fontSize:11, fontWeight:td?800:500, background:td?"#123C7A":"transparent", color:td?"#fff":"var(--foreground)" }}>{day}</span>
                {dt.length > 2 && <span style={{ fontSize:9, color:"var(--muted-foreground)" }}>+{dt.length-2}</span>}
              </div>
              <div className="space-y-0.5">
                {dt.slice(0,2).map(t => { const st=sMap[t.stageId]; return (
                  <button key={t.id} onClick={() => onSelect(t)} className="w-full rounded px-1 py-0.5 text-left truncate block" style={{ fontSize:9, fontWeight:600, background:`${st.cor}20`, color:st.cor }}>{t.titulo}</button>
                ); })}
              </div>
            </div>
          );
        })}
      </div>
      {moTasks.length > 0 && (
        <div className="p-4" style={{ borderTop:"1px solid var(--border)", background:"var(--muted)" }}>
          <p style={{ fontSize:12, fontWeight:700, color:"var(--foreground)", marginBottom:8 }}>Tarefas em {MONTHS[mo]}:</p>
          <div className="flex flex-wrap gap-2">
            {[...moTasks].sort((a,b) => a.prazo.localeCompare(b.prazo)).map(t => { const st=sMap[t.stageId]; return (
              <button key={t.id} onClick={() => onSelect(t)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl transition-opacity hover:opacity-80"
                style={{ background:`${st.cor}15`, border:`1px solid ${st.cor}30`, color:st.cor, fontSize:11, fontWeight:600 }}>
                {st.icon}<span>{t.titulo.length>28?t.titulo.slice(0,28)+"…":t.titulo}</span><span style={{ color:"var(--muted-foreground)", fontWeight:400 }}>— {fmtDate(t.prazo)}</span>
              </button>
            ); })}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── TASK DETAIL MODAL ────────────────────────────────────────────────────────

function TaskDetailModal({ task, stage, onClose, onEdit, onAddComment }: {
  task:Task; stage:Stage; onClose:()=>void; onEdit:()=>void;
  onAddComment:(taskId:string, c:Omit<Comentario,"id">)=>void;
}) {
  const [tab, setTab] = useState<"info"|"comentarios"|"historico">("info");
  const [msg, setMsg] = useState("");
  const od = isOverdue(task.prazo, task.status);

  function submit() {
    if (!msg.trim()) return;
    onAddComment(task.id, { autor:"Lucas Ferreira", avatar:"L", texto:msg.trim(), data:"02/06/2026" });
    setMsg("");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)" }} onClick={onClose}>
      <div className="rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col" style={{ background:"var(--card)", boxShadow:"0 24px 64px rgba(0,0,0,0.3)" }} onClick={e => e.stopPropagation()}>
        <div className="p-5 pb-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="rounded-lg p-1.5" style={{ background:stage.bgCor, color:stage.cor }}>{stage.icon}</div>
              <span style={{ fontSize:11, fontWeight:700, color:stage.cor }}>{stage.nome}</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={onEdit} className="flex items-center gap-1 px-3 py-1.5 rounded-xl" style={{ background:"#eef3fc", color:"#123C7A", fontSize:11, fontWeight:700, border:"1px solid #c7d9f5" }}><Edit2 size={11}/> Editar</button>
              <button onClick={onClose} className="rounded-xl p-1.5" style={{ background:"var(--muted)" }}><X size={16} style={{ color:"var(--muted-foreground)" }}/></button>
            </div>
          </div>
          <h2 style={{ fontSize:16, fontWeight:800, color:"var(--foreground)", marginBottom:10, lineHeight:1.3 }}>{task.titulo}</h2>
          <div className="flex flex-wrap gap-2 mb-3">
            <SBadge status={task.status}/> <PBadge priority={task.prioridade}/>
            {od && <span className="px-2 py-0.5 rounded-lg" style={{ background:"#fef2f2", color:"#dc2626", fontSize:10, fontWeight:700 }}>Atrasada</span>}
          </div>
          <div className="mb-4">
            <div className="flex justify-between mb-1.5" style={{ fontSize:11 }}>
              <span style={{ color:"var(--muted-foreground)" }}>Progresso</span>
              <span style={{ fontWeight:800, color:stage.cor }}>{task.progresso}%</span>
            </div>
            <PBar value={task.progresso} color={stage.cor} h={8}/>
          </div>
          <div className="flex gap-0" style={{ borderBottom:"1px solid var(--border)" }}>
            {([{id:"info",label:"Detalhes"},{id:"comentarios",label:`Comentários (${task.comentarios.length})`},{id:"historico",label:`Histórico (${task.atualizacoes.length})`}] as const).map(tb => (
              <button key={tb.id} onClick={() => setTab(tb.id)} className="px-4 py-2"
                style={{ fontSize:12, fontWeight:700, color:tab===tb.id?"#123C7A":"var(--muted-foreground)", borderBottom:`2px solid ${tab===tb.id?"#123C7A":"transparent"}`, marginBottom:-1 }}>
                {tb.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-5 pt-4">
          {tab === "info" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl p-3" style={{ background:"var(--muted)" }}>
                  <div className="flex items-center gap-1.5 mb-1.5"><User size={11} style={{ color:"var(--muted-foreground)" }}/><span style={{ fontSize:10, fontWeight:700, color:"var(--muted-foreground)" }}>Responsável</span></div>
                  <div className="flex items-center gap-2"><Av text={task.responsavelAvatar} color={stage.cor} size={24}/><span style={{ fontSize:12, fontWeight:700, color:"var(--foreground)" }}>{task.responsavel}</span></div>
                </div>
                <div className="rounded-xl p-3" style={{ background:od?"#fef2f2":"var(--muted)" }}>
                  <div className="flex items-center gap-1.5 mb-1.5"><Clock size={11} style={{ color:od?"#dc2626":"var(--muted-foreground)" }}/><span style={{ fontSize:10, fontWeight:700, color:od?"#dc2626":"var(--muted-foreground)" }}>Prazo</span></div>
                  <span style={{ fontSize:14, fontWeight:800, color:od?"#dc2626":"var(--foreground)" }}>{fmtDate(task.prazo)}</span>
                </div>
              </div>
              {task.descricao && <div><p style={{ fontSize:11, fontWeight:700, color:"var(--muted-foreground)", marginBottom:6 }}>Descrição</p><p style={{ fontSize:13, color:"var(--foreground)", lineHeight:1.6 }}>{task.descricao}</p></div>}
              {task.tags.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 mb-2"><Tag size={11} style={{ color:"var(--muted-foreground)" }}/><span style={{ fontSize:11, fontWeight:700, color:"var(--muted-foreground)" }}>Tags</span></div>
                  <div className="flex flex-wrap gap-1.5">{task.tags.map(t => <span key={t} className="px-2 py-1 rounded-lg" style={{ fontSize:11, fontWeight:600, background:`${stage.cor}15`, color:stage.cor, border:`1px solid ${stage.cor}30` }}>#{t}</span>)}</div>
                </div>
              )}
            </div>
          )}
          {tab === "comentarios" && (
            <div className="space-y-3">
              {task.comentarios.length === 0 && <div className="text-center py-8" style={{ color:"var(--muted-foreground)" }}><MessageSquare size={28} style={{ margin:"0 auto 8px", opacity:0.35 }}/><p style={{ fontSize:13 }}>Nenhum comentário ainda</p></div>}
              {task.comentarios.map(c => (
                <div key={c.id} className="flex gap-3">
                  <Av text={c.avatar} color={c.avatar==="C"?"#1F8A70":"#123C7A"} size={28}/>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1"><span style={{ fontSize:12, fontWeight:700, color:"var(--foreground)" }}>{c.autor}</span><span style={{ fontSize:10, color:"var(--muted-foreground)" }}>{c.data}</span></div>
                    <div className="rounded-xl p-3" style={{ background:"var(--muted)", fontSize:12, color:"var(--foreground)", lineHeight:1.55 }}>{c.texto}</div>
                  </div>
                </div>
              ))}
              <div className="flex gap-2 pt-3" style={{ borderTop:"1px solid var(--border)" }}>
                <Av text="L" color="#123C7A" size={28}/>
                <div className="flex-1 flex gap-2">
                  <input value={msg} onChange={e => setMsg(e.target.value)} onKeyDown={e => e.key==="Enter" && !e.shiftKey && submit()} placeholder="Adicionar comentário..."
                    className="flex-1 rounded-xl px-3 py-2" style={{ background:"var(--muted)", border:"1px solid var(--border)", fontSize:12, color:"var(--foreground)", outline:"none" }}/>
                  <button onClick={submit} className="rounded-xl px-3" style={{ background:"#123C7A", color:"#fff" }}><Send size={13}/></button>
                </div>
              </div>
            </div>
          )}
          {tab === "historico" && (
            <div className="space-y-3">
              {task.atualizacoes.length === 0 && <div className="text-center py-8" style={{ color:"var(--muted-foreground)" }}><Activity size={28} style={{ margin:"0 auto 8px", opacity:0.35 }}/><p style={{ fontSize:13 }}>Nenhuma atualização registrada</p></div>}
              {[...task.atualizacoes].reverse().map(u => (
                <div key={u.id} className="flex items-start gap-3 p-3 rounded-xl" style={{ background:"var(--muted)" }}>
                  <Activity size={14} style={{ color:"#123C7A", flexShrink:0, marginTop:2 }}/>
                  <div className="flex-1">
                    <p style={{ fontSize:12, color:"var(--foreground)" }}>
                      <span style={{ fontWeight:700 }}>{u.campo}</span> alterado:{" "}
                      <span style={{ color:"#dc2626", textDecoration:"line-through" }}>{u.anterior}</span>{" → "}
                      <span style={{ color:"#1F8A70", fontWeight:700 }}>{u.novo}</span>
                    </p>
                    <p style={{ fontSize:10, color:"var(--muted-foreground)", marginTop:2 }}>{u.autor} · {u.data}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── TASK FORM MODAL ──────────────────────────────────────────────────────────

function TaskFormModal({ task, stages, defaultStageId, onClose, onSave }: {
  task?: Task; stages:Stage[]; defaultStageId?:string;
  onClose:()=>void; onSave:(d:Partial<Task>&{id?:string})=>void;
}) {
  const sorted = [...stages].sort((a,b) => a.ordem-b.ordem);
  const [f, setF] = useState({
    titulo: task?.titulo ?? "", descricao: task?.descricao ?? "",
    stageId: task?.stageId ?? defaultStageId ?? sorted[0].id,
    responsavel: task?.responsavel ?? "Lucas Ferreira",
    responsavelAvatar: task?.responsavelAvatar ?? "L",
    prazo: task?.prazo ?? "2026-06-30",
    status: (task?.status ?? "pendente") as TaskStatus,
    prioridade: (task?.prioridade ?? "media") as Priority,
    progresso: task?.progresso ?? 0,
    tags: task?.tags.join(", ") ?? "",
  });
  const inp: React.CSSProperties = { width:"100%", background:"var(--muted)", border:"1px solid var(--border)", borderRadius:10, padding:"8px 12px", fontSize:13, color:"var(--foreground)", outline:"none" };
  const lbl: React.CSSProperties = { fontSize:11, fontWeight:700, color:"var(--muted-foreground)", marginBottom:4, display:"block" };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)" }} onClick={onClose}>
      <div className="rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto" style={{ background:"var(--card)", boxShadow:"0 24px 64px rgba(0,0,0,0.3)" }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 pb-4" style={{ borderBottom:"1px solid var(--border)" }}>
          <h2 style={{ fontSize:16, fontWeight:800, color:"var(--foreground)" }}>{task?"Editar Tarefa":"Nova Tarefa"}</h2>
          <button onClick={onClose} className="rounded-xl p-1.5" style={{ background:"var(--muted)" }}><X size={16} style={{ color:"var(--muted-foreground)" }}/></button>
        </div>
        <div className="p-5 space-y-4">
          <div><label style={lbl}>Título *</label><input style={inp} value={f.titulo} onChange={e => setF(p=>({...p,titulo:e.target.value}))} placeholder="Título da tarefa..."/></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label style={lbl}>Etapa</label>
              <select style={inp} value={f.stageId} onChange={e => setF(p=>({...p,stageId:e.target.value}))}>
                {sorted.map(s => <option key={s.id} value={s.id}>{s.nome}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Prioridade</label>
              <select style={inp} value={f.prioridade} onChange={e => setF(p=>({...p,prioridade:e.target.value as Priority}))}>
                <option value="urgente">Urgente</option><option value="alta">Alta</option><option value="media">Média</option><option value="baixa">Baixa</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label style={lbl}>Status</label>
              <select style={inp} value={f.status} onChange={e => setF(p=>({...p,status:e.target.value as TaskStatus}))}>
                <option value="pendente">Pendente</option><option value="em-andamento">Em Andamento</option><option value="concluida">Concluída</option><option value="bloqueada">Bloqueada</option>
              </select>
            </div>
            <div><label style={lbl}>Prazo</label><input type="date" style={inp} value={f.prazo} onChange={e => setF(p=>({...p,prazo:e.target.value}))}/></div>
          </div>
          <div><label style={lbl}>Responsável</label><input style={inp} value={f.responsavel} onChange={e => setF(p=>({...p,responsavel:e.target.value,responsavelAvatar:e.target.value.charAt(0).toUpperCase()}))} placeholder="Nome do responsável"/></div>
          <div>
            <div className="flex justify-between mb-1"><label style={lbl}>Progresso</label><span style={{ fontSize:13, fontWeight:800, color:"#123C7A" }}>{f.progresso}%</span></div>
            <input type="range" min={0} max={100} step={5} value={f.progresso} onChange={e => setF(p=>({...p,progresso:+e.target.value}))} style={{ width:"100%", accentColor:"#123C7A" }}/>
            <div className="mt-1"><PBar value={f.progresso} color="#123C7A" h={5}/></div>
          </div>
          <div><label style={lbl}>Tags (separadas por vírgula)</label><input style={inp} value={f.tags} onChange={e => setF(p=>({...p,tags:e.target.value}))} placeholder="ex: literatura, DNN, revisão"/></div>
          <div><label style={lbl}>Descrição</label>
            <textarea style={{ ...inp, height:80, resize:"none", lineHeight:"1.5" } as React.CSSProperties} value={f.descricao} onChange={e => setF(p=>({...p,descricao:e.target.value}))} placeholder="Descrição detalhada da tarefa..."/>
          </div>
        </div>
        <div className="flex gap-3 p-5 pt-0">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl" style={{ background:"var(--muted)", color:"var(--foreground)", fontSize:13, fontWeight:700, border:"1px solid var(--border)" }}>Cancelar</button>
          <button onClick={() => { if (!f.titulo.trim()) return; onSave({...(task?{id:task.id}:{}), ...f, tags:f.tags.split(",").map(t=>t.trim()).filter(Boolean) }); onClose(); }}
            className="flex-1 py-2.5 rounded-xl" style={{ background:"#123C7A", color:"#fff", fontSize:13, fontWeight:700 }}>
            {task?"Salvar Alterações":"Criar Tarefa"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── PLAN FORM MODAL ──────────────────────────────────────────────────────────

function PlanFormModal({ plan, onClose, onSave }: { plan:WorkPlanData; onClose:()=>void; onSave:(p:WorkPlanData)=>void }) {
  const [f, setF] = useState({...plan});
  const inp: React.CSSProperties = { width:"100%", background:"var(--muted)", border:"1px solid var(--border)", borderRadius:10, padding:"8px 12px", fontSize:13, color:"var(--foreground)", outline:"none" };
  const lbl: React.CSSProperties = { fontSize:11, fontWeight:700, color:"var(--muted-foreground)", marginBottom:4, display:"block" };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background:"rgba(0,0,0,0.5)", backdropFilter:"blur(4px)" }} onClick={onClose}>
      <div className="rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto" style={{ background:"var(--card)", boxShadow:"0 24px 64px rgba(0,0,0,0.3)" }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 pb-4" style={{ borderBottom:"1px solid var(--border)" }}>
          <h2 style={{ fontSize:16, fontWeight:800, color:"var(--foreground)" }}>Editar Plano de Trabalho</h2>
          <button onClick={onClose} className="rounded-xl p-1.5" style={{ background:"var(--muted)" }}><X size={16} style={{ color:"var(--muted-foreground)" }}/></button>
        </div>
        <div className="p-5 space-y-4">
          <div><label style={lbl}>Título do Plano</label><input style={inp} value={f.titulo} onChange={e => setF(p=>({...p,titulo:e.target.value}))}/></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label style={lbl}>Início</label><input type="month" style={inp} value={f.inicio} onChange={e => setF(p=>({...p,inicio:e.target.value}))}/></div>
            <div><label style={lbl}>Término previsto</label><input type="month" style={inp} value={f.fim} onChange={e => setF(p=>({...p,fim:e.target.value}))}/></div>
          </div>
          <div><label style={lbl}>Orientador</label><input style={inp} value={f.orientador} onChange={e => setF(p=>({...p,orientador:e.target.value}))}/></div>
          <div><label style={lbl}>Programa</label><input style={inp} value={f.programa} onChange={e => setF(p=>({...p,programa:e.target.value}))}/></div>
          <div><label style={lbl}>Descrição</label><textarea style={{ ...inp, height:90, resize:"none" } as React.CSSProperties} value={f.descricao} onChange={e => setF(p=>({...p,descricao:e.target.value}))}/></div>
        </div>
        <div className="flex gap-3 p-5 pt-0">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl" style={{ background:"var(--muted)", color:"var(--foreground)", fontSize:13, fontWeight:700, border:"1px solid var(--border)" }}>Cancelar</button>
          <button onClick={() => { onSave(f); onClose(); }} className="flex-1 py-2.5 rounded-xl" style={{ background:"#123C7A", color:"#fff", fontSize:13, fontWeight:700 }}>Salvar</button>
        </div>
      </div>
    </div>
  );
}

// ─── MAIN PAGE ────────────────────────────────────────────────────────────────

export function WorkPlanPage() {
  const { currentUser } = useApp();
  const [tasks, setTasks]   = useState<Task[]>(INITIAL_TASKS);
  const [stages]            = useState<Stage[]>(INITIAL_STAGES);
  const [plan, setPlan]     = useState<WorkPlanData>(INITIAL_PLAN);
  const [view, setView]     = useState<ViewType>("kanban");
  const [modal, setModal]   = useState<ModalState>(null);
  const [fStatus, setFStatus] = useState<TaskStatus|"todos">("todos");
  const [fStage, setFStage]   = useState("todos");
  const [search, setSearch]   = useState("");

  const filtered = useMemo(() => tasks.filter(t => {
    if (fStatus !== "todos" && t.status !== fStatus) return false;
    if (fStage !== "todos" && t.stageId !== fStage) return false;
    if (search && !t.titulo.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  }), [tasks, fStatus, fStage, search]);

  function saveTask(data: Partial<Task> & { id?: string }) {
    if (data.id) {
      setTasks(ts => ts.map(t => t.id === data.id ? { ...t, ...data } : t));
    } else {
      setTasks(ts => [...ts, {
        id: `t${Date.now()}`, stageId: data.stageId ?? stages[0].id,
        titulo: data.titulo ?? "", descricao: data.descricao ?? "",
        responsavel: data.responsavel ?? currentUser?.name ?? "Usuário",
        responsavelAvatar: data.responsavelAvatar ?? "U",
        prazo: data.prazo ?? "2026-12-31",
        status: data.status ?? "pendente", prioridade: data.prioridade ?? "media",
        progresso: data.progresso ?? 0, tags: data.tags ?? [],
        comentarios: [], atualizacoes: [{ id:`u${Date.now()}`, campo:"Status", anterior:"", novo:"pendente", data:"02/06/2026", autor:currentUser?.name ?? "Sistema" }],
      }]);
    }
  }

  function moveTask(taskId: string, sid: string) {
    setTasks(ts => ts.map(t => t.id === taskId ? { ...t, stageId: sid } : t));
  }

  function addComment(taskId: string, c: Omit<Comentario, "id">) {
    const nc = { ...c, id: `c${Date.now()}` };
    setTasks(ts => ts.map(t => t.id === taskId ? { ...t, comentarios:[...t.comentarios, nc] } : t));
    setModal(m => m?.kind === "detail" && m.task.id === taskId
      ? { ...m, task: { ...m.task, comentarios:[...m.task.comentarios, nc] } } : m);
  }

  const done    = tasks.filter(t => t.status === "concluida").length;
  const inProg  = tasks.filter(t => t.status === "em-andamento").length;
  const overdue = tasks.filter(t => isOverdue(t.prazo, t.status)).length;
  const overall = Math.round(stages.reduce((s,st) => s + st.progresso, 0) / stages.length);
  const sortedStages = [...stages].sort((a,b) => a.ordem-b.ordem);

  const VIEWS: { id: ViewType; label: string; icon: React.ReactNode }[] = [
    { id:"kanban",     label:"Kanban",          icon:<Columns   size={13}/> },
    { id:"timeline",   label:"Linha do Tempo",  icon:<Activity  size={13}/> },
    { id:"gantt",      label:"Gantt",           icon:<BarChart2 size={13}/> },
    { id:"calendario", label:"Calendário",      icon:<Calendar  size={13}/> },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="rounded-2xl p-5" style={{ background:"linear-gradient(135deg,#123C7A 0%,#1a4f9e 55%,#1F8A70 100%)" }}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Layers size={15} style={{ color:"rgba(255,255,255,0.8)" }}/>
              <span style={{ fontSize:11, fontWeight:600, color:"rgba(255,255,255,0.7)" }}>{plan.programa} · {plan.orientador}</span>
            </div>
            <h1 style={{ fontSize:19, fontWeight:800, color:"#fff", marginBottom:4, lineHeight:1.3 }}>{plan.titulo}</h1>
            <p style={{ fontSize:12, color:"rgba(255,255,255,0.65)" }}>
              {plan.inicio.split("-").reverse().join("/")} → {plan.fim.split("-").reverse().join("/")} · {PLAN_MONTHS} meses · Mês {CURRENT_MONTH}/{PLAN_MONTHS}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2">
              {[{v:done,l:"concluídas",c:"#4ade80"},{v:inProg,l:"em andamento",c:"#fbbf24"},{v:overdue,l:"atrasadas",c:"#f87171"}].map(s => (
                <div key={s.l} className="text-center rounded-xl px-3 py-2" style={{ background:"rgba(255,255,255,0.12)", border:"1px solid rgba(255,255,255,0.15)" }}>
                  <p style={{ fontSize:20, fontWeight:800, color:s.c, lineHeight:1 }}>{s.v}</p>
                  <p style={{ fontSize:9, color:"rgba(255,255,255,0.65)", marginTop:2 }}>{s.l}</p>
                </div>
              ))}
            </div>
            <div className="flex flex-col gap-2">
              <button onClick={() => setModal({kind:"plan-form"})} className="flex items-center gap-1.5 px-3 py-2 rounded-xl"
                style={{ background:"rgba(255,255,255,0.15)", color:"#fff", fontSize:12, fontWeight:700, border:"1px solid rgba(255,255,255,0.25)" }}>
                <Edit2 size={12}/> Editar Plano
              </button>
              <button onClick={() => setModal({kind:"task-form"})} className="flex items-center gap-1.5 px-3 py-2 rounded-xl"
                style={{ background:"#fff", color:"#123C7A", fontSize:12, fontWeight:700 }}>
                <Plus size={12}/> Nova Tarefa
              </button>
            </div>
          </div>
        </div>
        <div className="mt-4">
          <div className="flex justify-between mb-1.5" style={{ fontSize:11, color:"rgba(255,255,255,0.8)" }}>
            <span>Progresso Geral do Plano</span><span style={{ fontWeight:800 }}>{overall}%</span>
          </div>
          <div className="rounded-full overflow-hidden" style={{ height:8, background:"rgba(255,255,255,0.2)" }}>
            <div className="h-full rounded-full" style={{ width:`${overall}%`, background:"#fff" }}/>
          </div>
        </div>
      </div>

      {/* Stage chips */}
      <div className="rounded-2xl p-4" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
        <div className="flex items-center gap-2 mb-3">
          <span style={{ fontSize:12, fontWeight:700, color:"var(--foreground)" }}>Etapas</span>
          <span style={{ fontSize:11, color:"var(--muted-foreground)" }}>{stages.filter(s=>s.progresso===100).length}/{stages.length} concluídas</span>
          {fStage !== "todos" && <button onClick={() => setFStage("todos")} style={{ marginLeft:"auto", fontSize:11, fontWeight:600, color:"#123C7A" }}>Limpar filtro ×</button>}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 stepper-step">
          {sortedStages.map(s => (
            <button key={s.id} onClick={() => setFStage(fStage===s.id?"todos":s.id)}
              className="rounded-xl p-2 sm:p-2.5 text-center transition-all min-w-0 overflow-hidden"
              style={{ background:fStage===s.id?s.bgCor:"var(--muted)", border:`1px solid ${fStage===s.id?s.borderCor:"var(--border)"}` }}>
              <div className="flex justify-center mb-1" style={{ color:s.cor }}>{s.icon}</div>
              <p className="truncate" style={{ fontSize:10, fontWeight:700, color:s.cor, lineHeight:1.3, marginBottom:3 }}>{s.nome}</p>
              <PBar value={s.progresso} color={s.cor} h={3}/>
              <p style={{ fontSize:10, fontWeight:700, color:s.cor, marginTop:2 }}>{s.progresso}%</p>
            </button>
          ))}
        </div>
      </div>

      {/* View switcher + filters */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center gap-3">
        <div className="flex items-center rounded-xl p-1 gap-1" style={{ background:"var(--muted)", border:"1px solid var(--border)" }}>
          {VIEWS.map(v => (
            <button key={v.id} onClick={() => setView(v.id)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all"
              style={{ background:view===v.id?"var(--card)":"transparent", color:view===v.id?"#123C7A":"var(--muted-foreground)", fontSize:12, fontWeight:700, border:view===v.id?"1px solid var(--border)":"1px solid transparent", boxShadow:view===v.id?"0 1px 4px rgba(0,0,0,0.07)":"none" }}>
              {v.icon} {v.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 flex-1 flex-wrap">
          <div className="flex items-center gap-2 rounded-xl px-3 py-2" style={{ background:"var(--card)", border:"1px solid var(--border)" }}>
            <Search size={13} style={{ color:"var(--muted-foreground)" }}/>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar tarefas..."
              style={{ background:"transparent", border:"none", fontSize:12, color:"var(--foreground)", outline:"none", minWidth:140 }}/>
          </div>
          <select value={fStatus} onChange={e => setFStatus(e.target.value as TaskStatus|"todos")}
            className="rounded-xl px-3 py-2"
            style={{ background:"var(--card)", border:"1px solid var(--border)", fontSize:12, color:"var(--foreground)", outline:"none" }}>
            <option value="todos">Todos os status</option>
            <option value="pendente">Pendente</option>
            <option value="em-andamento">Em Andamento</option>
            <option value="concluida">Concluída</option>
            <option value="bloqueada">Bloqueada</option>
          </select>
          <span style={{ fontSize:11, color:"var(--muted-foreground)", marginLeft:"auto" }}>{filtered.length}/{tasks.length} tarefas</span>
        </div>
      </div>

      {/* Active view */}
      {view === "kanban"     && <KanbanView   tasks={filtered} stages={stages} onSelect={t => setModal({kind:"detail",task:t})} onMove={moveTask} onAdd={sid => setModal({kind:"task-form",stageId:sid})}/>}
      {view === "timeline"   && <TimelineView  tasks={filtered} stages={stages} onSelect={t => setModal({kind:"detail",task:t})}/>}
      {view === "gantt"      && <GanttView     stages={stages}  tasks={filtered} planStart={PLAN_START} totalMonths={PLAN_MONTHS} currentMonth={CURRENT_MONTH}/>}
      {view === "calendario" && <CalendarView  tasks={filtered} stages={stages} onSelect={t => setModal({kind:"detail",task:t})}/>}

      {/* Modals */}
      {modal?.kind === "detail" && (() => {
        const st = stages.find(s => s.id === modal.task.stageId) ?? stages[0];
        return <TaskDetailModal task={modal.task} stage={st} onClose={() => setModal(null)} onEdit={() => setModal({kind:"task-form",task:modal.task})} onAddComment={addComment}/>;
      })()}
      {modal?.kind === "task-form" && (
        <TaskFormModal task={modal.task} stages={stages} defaultStageId={modal.stageId} onClose={() => setModal(null)} onSave={saveTask}/>
      )}
      {modal?.kind === "plan-form" && (
        <PlanFormModal plan={plan} onClose={() => setModal(null)} onSave={setPlan}/>
      )}
    </div>
  );
}

import React, { useState, useEffect, useRef } from "react";
import {
  Brain, Database, GitBranch, Terminal, CheckCircle2,
  XCircle, Circle, Play, RotateCcw, Cpu, Activity, AlertTriangle,
  ChevronRight, Code2, Layers, Shield, Network, FileCheck, Search, Loader2,
  ChevronDown,
} from "lucide-react";
import { getInference, type InferenceResult, type RequisitoStatus } from "@/api/inferenceApi";
import { getStudents, getStudent, type Student } from "@/api/studentsApi";
import { getChecklist, type ChecklistResponse } from "@/api/checklistApi";
import { useChecklistStudent } from "@/hooks/useChecklistStudent";
import { useAuth } from "@/hooks/useAuth";

// ─── Types ────────────────────────────────────────────────────────────────────

interface FactData {
  id: string;
  label: string;
  detail: string;
  rawValue: string;
  threshold?: string;
  value: boolean;
  category: string;
}

interface RuleCondition {
  label: string;
  value: boolean;
  negated?: boolean;
}

interface RuleData {
  id: string;
  label: string;
  formula: string;
  operator: "AND" | "OR" | "GTE";
  conditions: RuleCondition[];
  result: boolean;
  description: string;
}

interface ConclusionData {
  id: string;
  label: string;
  result: boolean;
  detail: string;
  action: string;
  severity: "ok" | "warning" | "critical";
}

interface StudentProfile {
  id: string;
  name: string;
  short: string;
  matricula: string;
  programa: string;
  overallRisk: "apto" | "regular" | "em-risco" | "critico";
  facts: FactData[];
  rules: RuleData[];
  conclusions: ConclusionData[];
  fatosUsados: string[];
  situacaoInferida: string;
}

// ─── Derivação do perfil a partir do motor real ───────────────────────────────
// O grafo, painéis e timeline abaixo são alimentados por dados reais: o backend
// devolve o checklist (RL01) e os booleanos apto_defesa/creditos_validos/em_risco,
// que aqui viram os fatos, regras e conclusões da visualização.

function statusOk(status: RequisitoStatus): boolean {
  return status === "cumprido";
}

/** Bucket de risco da visualização, fiel aos booleanos reais do motor:
 * apto_defesa → apto; em_risco → em-risco; caso contrário o aluno está regular. */
function riskFromInference(inf: InferenceResult): StudentProfile["overallRisk"] {
  if (inf.apto_defesa) return "apto";
  if (inf.em_risco) return "em-risco";
  if (inf.situacao_inferida === "desligado") return "critico";
  return "regular";
}

/** Bucket de risco do card a partir da situação inferida (sem nova consulta ao motor). */
function cardRisk(situacao: string): StudentProfile["overallRisk"] {
  if (situacao === "em_fase_de_defesa" || situacao === "concluido") return "apto";
  if (situacao === "em_risco") return "em-risco";
  if (situacao === "desligado") return "critico";
  return "regular";
}

function shortName(nome: string): string {
  const parts = nome.trim().split(/\s+/);
  return parts.length > 1 ? `${parts[0]} ${parts[1][0]}.` : parts[0];
}

/** Converte o aluno real + resultado do motor no modelo de visualização. */
function deriveProfile(student: Student, inf: InferenceResult): StudentProfile {
  const c = inf.checklist;
  const qualOk = statusOk(c.qualificacao.status);
  const prodOk = statusOk(c.producao_validada.status);
  const profOk = statusOk(c.proficiencia.status);
  const planoOk = statusOk(c.plano_concluido.status);
  const numProducoes = inf.pontuacoes_producoes.length;

  const facts: FactData[] = [
    { id:"f_cred",  label:"Créditos Obtidos",   detail:"Obtidos vs mínimo exigido",       rawValue:String(c.creditos_minimos.obtidos), threshold:String(c.creditos_minimos.minimo), value:statusOk(c.creditos_minimos.status), category:"créditos" },
    { id:"f_qual",  label:"Qualificação",        detail:"Exame de qualificação realizado", rawValue:qualOk?"Aprovada":"Pendente",        value:qualOk,  category:"qualificação" },
    { id:"f_prod",  label:"Produção Científica", detail:"Artigos validados pela banca",    rawValue:`${numProducoes} validada(s)`,       value:prodOk,  category:"produção" },
    { id:"f_prof",  label:"Proficiência",        detail:"Língua estrangeira aprovada",     rawValue:profOk?"Comprovada":"Pendente",      value:profOk,  category:"proficiência" },
    { id:"f_plano", label:"Plano de Trabalho",   detail:"Conclusão das etapas do plano",   rawValue:planoOk?"Concluído":"Em andamento",  value:planoOk, category:"plano" },
  ];

  const rules: RuleData[] = [
    { id:"r_cred", label:"Créditos Válidos",    formula:`creditos_obtidos ≥ ${c.creditos_minimos.minimo}`, operator:"GTE", result:inf.creditos_validos, description:"Verifica se o aluno atingiu o mínimo de créditos.", conditions:[{ label:`${c.creditos_minimos.obtidos} ≥ ${c.creditos_minimos.minimo}?`, value:inf.creditos_validos }] },
    { id:"r_prod", label:"Produção Suficiente", formula:"count(producoes_validadas) ≥ 1",                 operator:"GTE", result:prodOk,              description:"Verifica se há ao menos uma publicação validada.", conditions:[{ label:`${numProducoes} ≥ 1?`, value:prodOk }] },
    { id:"r_risk", label:"Em Risco",            formula:"¬creditos_validos ∨ ¬plano_concluido",           operator:"OR",  result:inf.em_risco,        description:"Acionada quando créditos insuficientes ou plano incompleto.", conditions:[{ label:"¬Créditos Válidos", value:!inf.creditos_validos, negated:true },{ label:"¬Plano Concluído", value:!planoOk, negated:true }] },
    { id:"r_apto", label:"Apto à Defesa",       formula:"r_cred ∧ f_qual ∧ r_prod ∧ f_prof ∧ f_plano",    operator:"AND", result:inf.apto_defesa,     description:"Todas as 5 condições devem ser satisfeitas.", conditions:[{ label:"Créditos Válidos", value:inf.creditos_validos },{ label:"Qualificação", value:qualOk },{ label:"Produção", value:prodOk },{ label:"Proficiência", value:profOk },{ label:"Plano Concluído", value:planoOk }] },
  ];

  const pendencias = rules[3].conditions.filter(cond => !cond.value).map(cond => cond.label);
  const conclusions: ConclusionData[] = [
    { id:"c_risco", label:"Em Risco",          result:inf.em_risco,    severity:inf.em_risco?"warning":"ok",       detail:inf.em_risco ? (inf.riscos_detectados.length ? inf.riscos_detectados.join("; ") : "Condições de risco ativadas pelo motor.") : "Nenhuma condição de risco detectada pelo motor.", action:inf.em_risco ? "Reunião com orientador para elaborar plano de recuperação." : "Manter ritmo atual." },
    { id:"c_apto",  label:"Apto à Defesa",     result:inf.apto_defesa, severity:inf.apto_defesa?"ok":"critical",    detail:inf.apto_defesa ? "Todas as condições de aptidão satisfeitas." : `Pendências: ${pendencias.join(", ") || "—"}.`, action:inf.apto_defesa ? "Iniciar processo de agendamento da defesa." : "Cumprir as condições pendentes." },
    { id:"c_prod",  label:"Produção Validada", result:prodOk,          severity:prodOk?"ok":"warning",             detail:prodOk ? `${numProducoes} produção(ões) validada(s) pela banca.` : "Sem produção científica validada.", action:prodOk ? "Manter ritmo de produção." : "Submeter e validar produção científica." },
  ];

  return {
    id: student.id,
    name: student.nome,
    short: shortName(student.nome),
    matricula: student.matricula,
    programa: student.programa_id,
    overallRisk: riskFromInference(inf),
    facts,
    rules,
    conclusions,
    fatosUsados: inf.fatos_usados,
    situacaoInferida: inf.situacao_inferida,
  };
}

// ─── Graph Config (pixel positions, fixed layout) ─────────────────────────────

const G = {
  W: 880, H: 450, NW: 170, NH: 50,
  FX: 12,  // Facts left x
  RX: 250, // Int-rules left x
  CRX: 490,// Comp-rules left x
  KX: 710, // Conclusions left x
};
// Node centers (cx = left + NW/2, cy = top + NH/2)
const FACT_TOPS    = [12, 96, 180, 264, 348];
const INT_TOPS     = [52, 228];
const COMP_TOPS    = [130, 300];
const CONC_TOPS    = [72, 210, 348];

const fcx = G.FX  + G.NW/2; // 97
const rcx = G.RX  + G.NW/2; // 335  right edge = 250+170=420
const ccx = G.CRX + G.NW/2; // 575  right edge = 490+170=660
const kcx = G.KX  + G.NW/2; // 795

const fcy = FACT_TOPS.map(t => t + G.NH/2);  // [37,121,205,289,373]
const rcy = INT_TOPS.map(t => t + G.NH/2);   // [77,253]
const ccy = COMP_TOPS.map(t => t + G.NH/2);  // [155,325]
const kcy = CONC_TOPS.map(t => t + G.NH/2);  // [97,235,373]

const FR = G.FX + G.NW;   // 182
const RR = G.RX + G.NW;   // 420
const CR = G.CRX + G.NW;  // 660

interface SvgEdge { id:string; x1:number;y1:number; x2:number;y2:number; cp:number; negated:boolean; srcId:string; curved?:boolean }

const SVG_EDGES: SvgEdge[] = [
  { id:"e1",  x1:FR,  y1:fcy[0], x2:G.RX,  y2:rcy[0], cp:55, negated:false, srcId:"f_cred"  },
  { id:"e2",  x1:FR,  y1:fcy[2], x2:G.RX,  y2:rcy[1], cp:55, negated:false, srcId:"f_prod"  },
  { id:"e3",  x1:RR,  y1:rcy[0], x2:G.CRX, y2:ccy[0], cp:45, negated:true,  srcId:"r_cred"  },
  { id:"e4",  x1:FR,  y1:fcy[4], x2:G.CRX, y2:ccy[0], cp:120,negated:true,  srcId:"f_plano", curved:true },
  { id:"e5",  x1:RR,  y1:rcy[0], x2:G.CRX, y2:ccy[1], cp:80, negated:false, srcId:"r_cred"  },
  { id:"e6",  x1:FR,  y1:fcy[1], x2:G.CRX, y2:ccy[1], cp:130,negated:false, srcId:"f_qual",  curved:true },
  { id:"e7",  x1:RR,  y1:rcy[1], x2:G.CRX, y2:ccy[1], cp:45, negated:false, srcId:"r_prod"  },
  { id:"e8",  x1:FR,  y1:fcy[3], x2:G.CRX, y2:ccy[1], cp:120,negated:false, srcId:"f_prof",  curved:true },
  { id:"e9",  x1:FR,  y1:fcy[4], x2:G.CRX, y2:ccy[1], cp:120,negated:false, srcId:"f_plano", curved:true },
  { id:"e10", x1:CR,  y1:ccy[0], x2:G.KX,  y2:kcy[1], cp:55, negated:false, srcId:"r_risk"  },
  { id:"e11", x1:CR,  y1:ccy[1], x2:G.KX,  y2:kcy[0], cp:55, negated:false, srcId:"r_apto"  },
  { id:"e12", x1:RR,  y1:rcy[1], x2:G.KX,  y2:kcy[2], cp:140,negated:false, srcId:"r_prod",  curved:true },
];

const HIGHLIGHT_PATHS: Record<string, { nodes:string[]; edges:string[] }> = {
  c_risco: { nodes:["f_cred","f_plano","r_cred","r_risk","c_risco"], edges:["e1","e3","e4","e10"] },
  c_apto:  { nodes:["f_cred","f_qual","f_prod","f_prof","f_plano","r_cred","r_prod","r_risk","r_apto","c_apto"], edges:["e1","e2","e3","e4","e5","e6","e7","e8","e9","e11"] },
  c_prod:  { nodes:["f_prod","r_prod","c_prod"], edges:["e2","e12"] },
};

// ─── Query Console Data ───────────────────────────────────────────────────────

// As consultas refletem o resultado real do motor (sem tempos simulados): os
// fatos vêm do checklist e a query de situação lista os fatos_usados retornados.

const QUERIES = [
  {
    label: "Aluno apto à defesa?",
    cmd: "QUERY apto_defesa(?student)",
    output: (s: StudentProfile) => [
      `Consultando apto_defesa(?student)…`,
      `→ Créditos válidos     = ${s.rules[0].result ? "VERDADEIRO" : "FALSO"}`,
      `→ Produção suficiente   = ${s.rules[1].result ? "VERDADEIRO" : "FALSO"}`,
      `→ Qualificação          = ${s.facts[1].value ? "VERDADEIRO" : "FALSO"}`,
      `→ Proficiência          = ${s.facts[3].value ? "VERDADEIRO" : "FALSO"}`,
      `→ Plano concluído       = ${s.facts[4].value ? "VERDADEIRO" : "FALSO"}`,
      `──────────────────────────────────────`,
      `CONCLUSÃO: apto_defesa = ${s.rules[3].result ? "✓ VERDADEIRO" : "✗ FALSO"}`,
    ],
    result: (s: StudentProfile) => s.rules[3].result,
  },
  {
    label: "Créditos válidos?",
    cmd: "QUERY creditos_validos(?student)",
    output: (s: StudentProfile) => [
      `Consultando creditos_validos(?student)…`,
      `creditos_obtidos = ${s.facts[0].rawValue}${s.facts[0].threshold ? ` (meta ${s.facts[0].threshold})` : ""}`,
      `${s.facts[0].rawValue} ≥ ${s.facts[0].threshold ?? "?"}? → ${s.rules[0].result ? "VERDADEIRO" : "FALSO"}`,
      `──────────────────────────────────────`,
      `CONCLUSÃO: creditos_validos = ${s.rules[0].result ? "✓ VERDADEIRO" : "✗ FALSO"}`,
    ],
    result: (s: StudentProfile) => s.rules[0].result,
  },
  {
    label: "Situação acadêmica?",
    cmd: "QUERY situacao_academica(?student)",
    output: (s: StudentProfile) => [
      `Analisando situacao_academica(?student)…`,
      `Fatos usados pelo motor (${s.fatosUsados.length}):`,
      ...(s.fatosUsados.length ? s.fatosUsados.map(f => `  ${f}`) : ["  (nenhum fato retornado)"]),
      `──────────────────────────────────────`,
      `SITUAÇÃO INFERIDA: ${s.situacaoInferida}`,
    ],
    result: (s: StudentProfile) => s.overallRisk === "apto",
  },
];

// ─── Colors ───────────────────────────────────────────────────────────────────

const TRUE_CLR = "#10b981";
const FALSE_CLR = "#ef4444";
const NEG_CLR = "#f59e0b";
const FACT_CLR = "#3b82f6";
const RULE_CLR = "#8b5cf6";
const CONC_CLR = "#06b6d4";

function truthColor(v: boolean) { return v ? TRUE_CLR : FALSE_CLR; }
function truthBg(v: boolean) { return v ? "#022c22" : "#2c0a0a"; }
function truthBorder(v: boolean) { return v ? "#064e3b" : "#450a0a"; }

// ─── SVG Path helper ──────────────────────────────────────────────────────────

function edgePath(e: SvgEdge): string {
  const dx = (e.x2 - e.x1) / 2;
  if (e.curved) {
    return `M ${e.x1} ${e.y1} C ${e.x1 + e.cp} ${e.y1} ${e.x2 - e.cp} ${e.y2} ${e.x2} ${e.y2}`;
  }
  return `M ${e.x1} ${e.y1} C ${e.x1 + dx} ${e.y1} ${e.x2 - dx} ${e.y2} ${e.x2} ${e.y2}`;
}

function edgeColor(e: SvgEdge, s: StudentProfile, highlighted: Set<string>, hoveredEdge: string | null): string {
  const isHl = highlighted.has(e.id) || hoveredEdge === e.id;
  const allHighlighted = highlighted.size > 0;
  // find source node value
  const allNodes: Record<string, boolean> = {};
  s.facts.forEach(f => { allNodes[f.id] = f.value; });
  s.rules.forEach(r => { allNodes[r.id] = r.result; });
  const val = allNodes[e.srcId] ?? false;
  const base = e.negated ? (val ? "#6b7280" : NEG_CLR) : (val ? TRUE_CLR : FALSE_CLR);
  if (allHighlighted && !isHl) return "rgba(100,116,139,0.12)";
  return isHl ? base : (allHighlighted ? base + "30" : base + "80");
}

function edgeWidth(e: SvgEdge, highlighted: Set<string>, hoveredEdge: string | null): number {
  const isHl = highlighted.has(e.id) || hoveredEdge === e.id;
  return isHl ? 2.5 : 1.5;
}

// ─── Node Box ─────────────────────────────────────────────────────────────────

function NodeBox({ x, y, type, label, sub, value, id, highlighted, activeNode, onHover, onLeave, onClick, pulse }:{
  x:number; y:number; type:"fact"|"irule"|"crule"|"conc";
  label:string; sub:string; value:boolean; id:string;
  highlighted:Set<string>; activeNode:string|null;
  onHover:(id:string)=>void; onLeave:()=>void; onClick:(id:string)=>void;
  pulse?:boolean;
}) {
  const isHl = highlighted.has(id) || activeNode === id;
  const dimmed = highlighted.size > 0 && !isHl;
  const typeColor = type === "fact" ? FACT_CLR : type === "irule" ? RULE_CLR : type === "crule" ? "#a78bfa" : CONC_CLR;
  const glowColor = isHl ? truthColor(value) : typeColor;

  return (
    <g
      style={{ cursor: "pointer" }}
      onMouseEnter={() => onHover(id)}
      onMouseLeave={onLeave}
      onClick={() => onClick(id)}
    >
      {pulse && value && (
        <>
          <rect x={x-4} y={y-4} width={G.NW+8} height={G.NH+8} rx={10} fill="none" stroke={truthColor(value)} strokeWidth={1.5} opacity={0.3}>
            <animate attributeName="opacity" values="0.3;0.8;0.3" dur="2s" repeatCount="indefinite"/>
            <animate attributeName="rx" values="10;12;10" dur="2s" repeatCount="indefinite"/>
          </rect>
        </>
      )}
      <rect
        x={x} y={y} width={G.NW} height={G.NH} rx={8}
        fill={dimmed ? "#0f172a" : "#111827"}
        stroke={isHl ? glowColor : dimmed ? "#1e293b" : typeColor + "50"}
        strokeWidth={isHl ? 2 : 1}
        style={{ filter: isHl ? `drop-shadow(0 0 8px ${glowColor}80)` : "none", opacity: dimmed ? 0.35 : 1, transition: "all 0.2s" }}
      />
      {/* Type stripe */}
      <rect x={x} y={y} width={4} height={G.NH} rx={4} fill={typeColor} opacity={dimmed ? 0.2 : 0.8}/>
      {/* Label */}
      <text x={x+12} y={y+18} fontSize={11} fontWeight={700} fill={dimmed ? "#334155" : "#f8fafc"} fontFamily="system-ui">{label}</text>
      {/* Sub */}
      <text x={x+12} y={y+33} fontSize={9} fill={dimmed ? "#1e293b" : "#94a3b8"} fontFamily="'Courier New',monospace">{sub}</text>
      {/* Truth badge */}
      <rect x={x+G.NW-34} y={y+12} width={26} height={14} rx={4} fill={truthBg(value)} stroke={truthColor(value)} strokeWidth={1} opacity={dimmed ? 0.3 : 1}/>
      <text x={x+G.NW-21} y={y+22} fontSize={7.5} fontWeight={700} fill={truthColor(value)} textAnchor="middle" fontFamily="'Courier New',monospace">
        {value ? "TRUE" : "FALSE"}
      </text>
    </g>
  );
}

// ─── Inference Graph ──────────────────────────────────────────────────────────

function InferenceGraph({ student, activeConclusion, onConclusion }: {
  student: StudentProfile; activeConclusion: string | null; onConclusion: (id: string | null) => void;
}) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<string | null>(null);

  const highlighted: Set<string> = new Set();
  if (activeConclusion && HIGHLIGHT_PATHS[activeConclusion]) {
    HIGHLIGHT_PATHS[activeConclusion].nodes.forEach(n => highlighted.add(n));
    HIGHLIGHT_PATHS[activeConclusion].edges.forEach(e => highlighted.add(e));
  }
  if (hoveredNode && HIGHLIGHT_PATHS[hoveredNode]) {
    HIGHLIGHT_PATHS[hoveredNode].nodes.forEach(n => highlighted.add(n));
    HIGHLIGHT_PATHS[hoveredNode].edges.forEach(e => highlighted.add(e));
  }

  const handleNodeClick = (id: string) => {
    if (id.startsWith("c_")) onConclusion(activeConclusion === id ? null : id);
  };

  const nodeProps = { highlighted, activeNode: activeConclusion, onLeave: () => setHoveredNode(null) };

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg width={G.W} height={G.H} style={{ display: "block", minWidth: G.W }}>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map(f => (
          <line key={f} x1={G.W*f} y1={0} x2={G.W*f} y2={G.H} stroke="#1e293b" strokeWidth={1} strokeDasharray="4,8"/>
        ))}

        {/* Layer labels */}
        {[
          { x: G.FX,  label: "BASE DE FATOS" },
          { x: G.RX,  label: "REGRAS SIMPLES" },
          { x: G.CRX, label: "REGRAS COMPOSTAS" },
          { x: G.KX,  label: "CONCLUSÕES" },
        ].map(l => (
          <text key={l.x} x={l.x + G.NW/2} y={10} textAnchor="middle" fontSize={7.5} fontWeight={700} fill="#334155" fontFamily="'Courier New',monospace" letterSpacing={1}>{l.label}</text>
        ))}

        {/* Edges */}
        <defs>
          <marker id="arrowTrue"  markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill={TRUE_CLR}/></marker>
          <marker id="arrowFalse" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill={FALSE_CLR}/></marker>
          <marker id="arrowNeg"   markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill={NEG_CLR}/></marker>
        </defs>
        {SVG_EDGES.map(e => {
          const allNodes: Record<string, boolean> = {};
          student.facts.forEach(f => { allNodes[f.id] = f.value; });
          student.rules.forEach(r => { allNodes[r.id] = r.result; });
          const val = allNodes[e.srcId] ?? false;
          const color = edgeColor(e, student, highlighted, hoveredEdge);
          const arrowId = e.negated ? "arrowNeg" : val ? "arrowTrue" : "arrowFalse";
          return (
            <path key={e.id} d={edgePath(e)} fill="none"
              stroke={color} strokeWidth={edgeWidth(e, highlighted, hoveredEdge)}
              strokeDasharray={e.negated ? "4,3" : "none"}
              markerEnd={`url(#${arrowId})`}
              style={{ transition: "stroke 0.2s, stroke-width 0.2s", cursor: "pointer" }}
              onMouseEnter={() => setHoveredEdge(e.id)}
              onMouseLeave={() => setHoveredEdge(null)}
            />
          );
        })}

        {/* Fact nodes */}
        {student.facts.map((f, i) => (
          <NodeBox key={f.id} x={G.FX} y={FACT_TOPS[i]} type="fact" id={f.id}
            label={f.label} sub={f.rawValue + (f.threshold ? ` / ${f.threshold}` : "")}
            value={f.value} {...nodeProps} onHover={setHoveredNode} onClick={handleNodeClick} />
        ))}

        {/* Intermediate rule nodes */}
        {[student.rules[0], student.rules[1]].map((r, i) => (
          <NodeBox key={r.id} x={G.RX} y={INT_TOPS[i]} type="irule" id={r.id}
            label={r.label} sub={r.formula} value={r.result}
            {...nodeProps} onHover={setHoveredNode} onClick={handleNodeClick} />
        ))}

        {/* Composite rule nodes */}
        {[student.rules[2], student.rules[3]].map((r, i) => (
          <NodeBox key={r.id} x={G.CRX} y={COMP_TOPS[i]} type="crule" id={r.id}
            label={r.label} sub={r.formula} value={r.result}
            {...nodeProps} onHover={setHoveredNode} onClick={handleNodeClick} />
        ))}

        {/* Conclusion nodes */}
        {student.conclusions.map((c, i) => (
          <NodeBox key={c.id} x={G.KX} y={CONC_TOPS[i]} type="conc" id={c.id}
            label={c.label} sub={c.result ? "VERDADEIRO" : "FALSO"}
            value={c.result} {...nodeProps} onHover={setHoveredNode} onClick={handleNodeClick}
            pulse={c.result && (c.id === "c_risco" || c.id === "c_prod")} />
        ))}

        {/* Legend */}
        <g transform={`translate(${G.W - 200}, ${G.H - 60})`}>
          <rect width={190} height={55} rx={6} fill="#0f172a" stroke="#1e293b"/>
          <text x={8} y={13} fontSize={7} fontWeight={700} fill="#475569" fontFamily="'Courier New',monospace" letterSpacing={0.5}>LEGENDA</text>
          {[[TRUE_CLR,"TRUE / Satisfeito"],[FALSE_CLR,"FALSE / Não satisfeito"],[NEG_CLR,"Negação (¬)"]].map(([c,l],i)=>(
            <g key={i} transform={`translate(8, ${18+i*13})`}>
              <line x1={0} y1={4} x2={20} y2={4} stroke={c} strokeWidth={2}/>
              <text x={25} y={8} fontSize={8} fill="#64748b" fontFamily="system-ui">{l}</text>
            </g>
          ))}
        </g>
      </svg>
      <p style={{ textAlign:"center", fontSize:10, color:"#334155", marginTop:4, fontFamily:"monospace" }}>
        Clique em um nó de conclusão para destacar o caminho de inferência
      </p>
    </div>
  );
}

// ─── Query Console ────────────────────────────────────────────────────────────

function QueryConsole({ student }: { student: StudentProfile }) {
  const [selectedQuery, setSelectedQuery] = useState(0);
  const [state, setState] = useState<"idle" | "running" | "done">("idle");
  const [output, setOutput] = useState<string[]>([]);
  const outputRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { return () => { if (timerRef.current) clearTimeout(timerRef.current); }; }, []);

  useEffect(() => {
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [output]);

  function runQuery() {
    setOutput([]);
    setState("running");
    const steps = QUERIES[selectedQuery].output(student);
    let i = 0;
    const next = () => {
      if (i < steps.length) {
        setOutput(prev => [...prev, steps[i]]);
        i++;
        timerRef.current = setTimeout(next, 120 + Math.random() * 80);
      } else {
        setState("done");
      }
    };
    timerRef.current = setTimeout(next, 300);
  }

  function reset() { setState("idle"); setOutput([]); if (timerRef.current) clearTimeout(timerRef.current); }

  const q = QUERIES[selectedQuery];
  const result = q.result(student);

  return (
    <div className="flex flex-col h-full" style={{ background:"#030712", border:"1px solid #1e293b", borderRadius:16, overflow:"hidden" }}>
      {/* Console header */}
      <div className="flex items-center gap-2 px-4 py-3" style={{ background:"#0f172a", borderBottom:"1px solid #1e293b" }}>
        <div className="flex gap-1.5">
          <div className="rounded-full" style={{ width:10, height:10, background:"#ef4444" }}/>
          <div className="rounded-full" style={{ width:10, height:10, background:"#f59e0b" }}/>
          <div className="rounded-full" style={{ width:10, height:10, background:"#10b981" }}/>
        </div>
        <Terminal size={12} style={{ color:"#64748b" }}/>
        <span style={{ fontSize:11, color:"#64748b", fontFamily:"monospace" }}>console — motor de inferência</span>
        <div className="flex items-center gap-1 ml-auto">
          <div className="rounded-full" style={{ width:6, height:6, background:state==="running"?"#f59e0b":"#10b981" }}>
            {state==="running" && <div className="rounded-full w-full h-full" style={{ background:"#f59e0b", animation:"pulse 1s infinite" }}/>}
          </div>
          <span style={{ fontSize:9, color:state==="running"?"#f59e0b":"#475569", fontFamily:"monospace" }}>
            {state==="running" ? "EXECUTANDO" : state==="done" ? "CONCLUÍDO" : "PRONTO"}
          </span>
        </div>
      </div>

      {/* Query selector */}
      <div className="flex gap-1.5 p-3" style={{ borderBottom:"1px solid #0f172a" }}>
        {QUERIES.map((q, i) => (
          <button key={i} onClick={() => { setSelectedQuery(i); reset(); }}
            className="rounded-lg px-2.5 py-1.5 transition-all"
            style={{ background:selectedQuery===i?"#1e3a5f":"#0f172a", color:selectedQuery===i?"#60a5fa":"#475569", fontSize:10, fontWeight:700, border:`1px solid ${selectedQuery===i?"#2563eb30":"#1e293b"}`, fontFamily:"monospace" }}>
            {q.label}
          </button>
        ))}
      </div>

      {/* Input line */}
      <div className="flex items-center gap-2 px-4 py-2" style={{ borderBottom:"1px solid #0f172a" }}>
        <span style={{ color:"#10b981", fontSize:12, fontFamily:"monospace" }}>❯</span>
        <span style={{ color:"#60a5fa", fontSize:11, fontFamily:"monospace", flex:1 }}>{q.cmd}</span>
        <div className="flex gap-2">
          <button onClick={reset} className="rounded-lg p-1.5" style={{ background:"#1e293b", color:"#64748b" }} title="Limpar"><RotateCcw size={11}/></button>
          <button onClick={runQuery} disabled={state==="running"} className="flex items-center gap-1.5 rounded-lg px-3 py-1.5" style={{ background:state==="running"?"#1e293b":"#1e3a5f", color:state==="running"?"#475569":"#60a5fa", fontSize:11, fontWeight:700, fontFamily:"monospace" }}>
            <Play size={10}/> {state==="running" ? "..." : "Executar"}
          </button>
        </div>
      </div>

      {/* Output */}
      <div ref={outputRef} className="flex-1 overflow-y-auto p-4 space-y-0.5" style={{ minHeight:180, maxHeight:220 }}>
        {output.length === 0 && (
          <p style={{ color:"#334155", fontSize:11, fontFamily:"monospace" }}>// Clique em "Executar" para iniciar a inferência</p>
        )}
        {output.map((line, i) => {
          const isConc = line.includes("CONCLUSÃO") || line.includes("SITUAÇÃO");
          const isSep = line.includes("────");
          return (
            <div key={i} style={{ fontFamily:"'Courier New',monospace", fontSize:10.5, lineHeight:1.7,
              color: isConc ? (result ? "#10b981" : "#ef4444") : isSep ? "#1e293b" : line.includes("→") ? "#93c5fd" : "#64748b" }}>
              {line}
            </div>
          );
        })}
        {state === "running" && (
          <div style={{ fontFamily:"monospace", fontSize:10.5, color:"#f59e0b" }}>
            <span className="inline-block" style={{ animation:"pulse 0.8s infinite" }}>▌</span>
          </div>
        )}
        {state === "done" && (
          <div className="mt-3 rounded-lg px-3 py-2" style={{ background:result?"#022c22":"#2c0a0a", border:`1px solid ${result?"#064e3b":"#450a0a"}` }}>
            <span style={{ fontSize:11, fontWeight:700, color:result?"#10b981":"#ef4444", fontFamily:"monospace" }}>
              {result ? "✓ VERDADEIRO" : "✗ FALSO"}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Rule Execution Timeline ──────────────────────────────────────────────────

function RuleTimeline({ student, running, step }: { student: StudentProfile; running: boolean; step: number }) {
  const OPERATORS: Record<string, string> = { AND:"∧", OR:"∨", GTE:"≥" };

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-4 pb-2" style={{ minWidth: student.rules.length * 260 + 40 }}>
        {student.rules.map((rule, i) => {
          const active = step >= i;
          const current = step === i;
          return (
            <div key={rule.id} className="flex-1 rounded-xl p-4" style={{ background: active ? (rule.result ? "#022c22" : "#2c0a0a") : "#0f172a", border:`1px solid ${active ? truthBorder(rule.result) : "#1e293b"}`, minWidth:230, transition:"all 0.4s", opacity:step===-1?0.5:active?1:0.3 }}>
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="rounded-full flex items-center justify-center" style={{ width:22, height:22, background:active?truthBg(rule.result):"#1e293b", border:`1px solid ${active?truthBorder(rule.result):"#334155"}` }}>
                    <span style={{ fontSize:9, fontWeight:900, color:active?truthColor(rule.result):"#475569", fontFamily:"monospace" }}>R{i+1}</span>
                  </div>
                  <span style={{ fontSize:11, fontWeight:700, color:active?"#f8fafc":"#334155" }}>{rule.label}</span>
                </div>
                {active && (
                  <span style={{ fontSize:9, fontWeight:800, color:truthColor(rule.result), background:truthBg(rule.result), padding:"1px 6px", borderRadius:4, fontFamily:"monospace" }}>
                    {rule.result ? "TRUE" : "FALSE"}
                  </span>
                )}
              </div>

              {/* Timing */}
              <div className="flex items-center gap-2 mb-3">
                <span className="rounded-lg px-1.5 py-0.5" style={{ fontSize:8, fontWeight:700, background:"#1e293b", color:"#60a5fa", fontFamily:"monospace" }}>{OPERATORS[rule.operator]} {rule.operator}</span>
              </div>

              {/* Conditions */}
              <div className="space-y-1.5">
                {rule.conditions.map((c, j) => (
                  <div key={j} className="flex items-center gap-2 rounded-lg px-2 py-1" style={{ background:"#030712" }}>
                    <div className="rounded-full flex-shrink-0" style={{ width:6, height:6, background:active?(c.negated?NEG_CLR:truthColor(c.value)):"#334155" }}/>
                    <span style={{ fontSize:9, color:active?(c.negated?NEG_CLR:truthColor(c.value)):"#334155", fontFamily:"monospace", flex:1 }}>{c.label}</span>
                    {active && <span style={{ fontSize:8, fontWeight:700, color:c.value?TRUE_CLR:FALSE_CLR, fontFamily:"monospace" }}>{c.value?"T":"F"}</span>}
                  </div>
                ))}
              </div>

              {/* Arrow to next */}
              {i < student.rules.length - 1 && (
                <div className="flex justify-end mt-2">
                  <ChevronRight size={14} style={{ color: active ? "#475569" : "#1e293b" }}/>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Explainability Panel ─────────────────────────────────────────────────────

function ExplainPanel({ student, question }: { student: StudentProfile; question: string }) {
  const conc = student.conclusions.find(c => c.id === question);
  const rule = question === "c_risco" ? student.rules[2] : question === "c_apto" ? student.rules[3] : student.rules[1];
  if (!conc || !rule) return null;

  const REASON_LABEL: Record<string, string> = {
    c_risco: "Por que este aluno está Em Risco?",
    c_apto:  "Por que este aluno não está Apto à Defesa?",
    c_prod:  "Por que a Produção está Validada?",
  };

  return (
    <div className="space-y-3">
      <div className="rounded-xl p-3" style={{ background:truthBg(conc.result), border:`1px solid ${truthBorder(conc.result)}` }}>
        <div className="flex items-center gap-2 mb-1">
          {conc.result ? <CheckCircle2 size={14} style={{ color:TRUE_CLR }}/> : <XCircle size={14} style={{ color:FALSE_CLR }}/>}
          <span style={{ fontSize:12, fontWeight:700, color:truthColor(conc.result), fontFamily:"monospace" }}>{conc.result ? "VERDADEIRO" : "FALSO"}</span>
        </div>
        <p style={{ fontSize:11, color:"#94a3b8", lineHeight:1.6 }}>{conc.detail}</p>
      </div>

      {/* Logic tree */}
      <div className="rounded-xl p-4" style={{ background:"#0f172a", border:"1px solid #1e293b" }}>
        <p style={{ fontSize:9, fontWeight:700, color:"#475569", letterSpacing:1, marginBottom:12, fontFamily:"monospace" }}>ÁRVORE DE INFERÊNCIA</p>

        {/* Root */}
        <div className="flex items-center gap-2 mb-3">
          <div className="rounded-lg px-2 py-1" style={{ background:RULE_CLR+"20", border:`1px solid ${RULE_CLR}40` }}>
            <span style={{ fontSize:10, fontWeight:700, color:RULE_CLR, fontFamily:"monospace" }}>{rule.label}</span>
          </div>
          <ChevronRight size={12} style={{ color:"#334155" }}/>
          <span style={{ fontSize:10, fontWeight:700, color:truthColor(rule.result), fontFamily:"monospace" }}>
            {rule.result ? "VERDADEIRO" : "FALSO"}
          </span>
        </div>

        {/* Formula */}
        <div className="rounded-lg px-3 py-2 mb-3" style={{ background:"#030712", border:"1px solid #0f172a" }}>
          <span style={{ fontSize:9, color:"#60a5fa", fontFamily:"monospace" }}>{rule.formula}</span>
        </div>

        {/* Conditions tree */}
        <div className="space-y-2 pl-4">
          {rule.conditions.map((c, i) => (
            <div key={i} className="flex items-start gap-2">
              <div className="flex flex-col items-center" style={{ paddingTop:4 }}>
                <div className="rounded-full" style={{ width:6, height:6, background:c.negated?NEG_CLR:truthColor(c.value), flexShrink:0 }}/>
                {i < rule.conditions.length - 1 && <div style={{ width:1, height:16, background:"#1e293b", marginTop:2 }}/>}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  {c.negated && <span style={{ fontSize:9, color:NEG_CLR, fontFamily:"monospace" }}>¬</span>}
                  <span style={{ fontSize:10, color:"#cbd5e1", fontFamily:"monospace" }}>{c.label}</span>
                  <span className="rounded px-1.5" style={{ fontSize:8, fontWeight:800, color:c.negated?NEG_CLR:truthColor(c.value), background:c.negated?truthBg(!c.value):truthBg(c.value), fontFamily:"monospace" }}>
                    {c.value ? "TRUE" : "FALSE"}
                  </span>
                  {c.negated && <span style={{ fontSize:8, color:NEG_CLR, fontFamily:"monospace" }}>→ {!c.value ? "TRUE" : "FALSE"}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Operator result */}
        <div className="mt-3 pt-3 flex items-center gap-2" style={{ borderTop:"1px solid #1e293b" }}>
          <span style={{ fontSize:9, color:"#475569", fontFamily:"monospace" }}>OPERADOR {rule.operator}:</span>
          <span style={{ fontSize:10, fontWeight:700, color:truthColor(rule.result), fontFamily:"monospace" }}>{rule.result ? "VERDADEIRO" : "FALSO"}</span>
        </div>
      </div>

      {/* Action */}
      <div className="rounded-xl px-3 py-2.5" style={{ background:"#0c1829", border:"1px solid #1e3a5f" }}>
        <p style={{ fontSize:9, fontWeight:700, color:"#3b82f6", letterSpacing:1, marginBottom:4, fontFamily:"monospace" }}>AÇÃO RECOMENDADA</p>
        <p style={{ fontSize:11, color:"#93c5fd", lineHeight:1.6 }}>{conc.action}</p>
      </div>
    </div>
  );
}

// ─── Real Inference Panel (dados reais do backend) ────────────────────────────

const SITU_CLR: Record<string, string> = {
  em_fase_de_defesa: "#10b981",
  qualificado: "#3b82f6",
  regular: "#64748b",
  em_risco: "#f59e0b",
};

function BoolPill({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: value ? "#022c22" : "#2c0a0a", border: `1px solid ${value ? "#064e3b" : "#450a0a"}` }}>
      {value ? <CheckCircle2 size={14} style={{ color: "#10b981" }} /> : <XCircle size={14} style={{ color: "#ef4444" }} />}
      <span style={{ fontSize: 12, fontWeight: 700, color: value ? "#10b981" : "#ef4444", fontFamily: "monospace" }}>{label}</span>
    </div>
  );
}

function RealInferencePanel() {
  const { studentId, students, setStudentId } = useChecklistStudent();
  const { token } = useAuth();
  const [selectorOpen, setSelectorOpen] = useState(false);
  const [inf, setInf] = useState<InferenceResult | null>(null);
  const [chk, setChk] = useState<ChecklistResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFacts, setShowFacts] = useState(false);

  useEffect(() => {
    if (!studentId || !token) return;
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getInference(studentId, token), getChecklist(studentId, token)])
      .then(([i, c]) => { if (active) { setInf(i); setChk(c); } })
      .catch(() => { if (active) setError("Não foi possível carregar a inferência do backend."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  const selectedLabel = students?.find((s) => s.id === studentId)?.label;

  return (
    <div className="rounded-2xl p-5" style={{ background: "#030712", border: "1px solid #1e293b" }}>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-4">
        <div className="flex items-center gap-2">
          <Database size={14} style={{ color: "#3b82f6" }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: "#e2e8f0" }}>Inferência real (motor lógico + backend)</span>
        </div>

        {students && (
          <div className="relative">
            <button
              onClick={() => setSelectorOpen((o) => !o)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5"
              style={{ background: "#0f172a", border: "1px solid #1e293b", color: "#e2e8f0", fontSize: 11, fontWeight: 700, fontFamily: "monospace" }}
            >
              {selectedLabel ?? "Selecionar aluno"}
              <ChevronDown size={12} style={{ color: "#475569" }} />
            </button>
            {selectorOpen && (
              <div
                className="absolute right-0 mt-1 rounded-xl shadow-lg z-10 overflow-hidden"
                style={{ background: "#0f172a", border: "1px solid #1e293b", minWidth: 180 }}
              >
                {students.length === 0 ? (
                  <p className="px-4 py-3" style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>
                    Nenhum aluno encontrado
                  </p>
                ) : (
                  students.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => { setStudentId(s.id); setSelectorOpen(false); }}
                      className="w-full text-left px-4 py-2.5"
                      style={{
                        fontSize: 11,
                        fontWeight: s.id === studentId ? 700 : 400,
                        color: s.id === studentId ? "#60a5fa" : "#94a3b8",
                        background: s.id === studentId ? "#1e3a5f" : "transparent",
                        fontFamily: "monospace",
                      }}
                    >
                      {s.label}
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div className="flex items-center gap-2" style={{ color: "#64748b", fontSize: 12 }}>
          <Loader2 size={16} className="animate-spin" /> Consultando o motor…
        </div>
      )}
      {error && !loading && (
        <div className="rounded-lg p-3" style={{ background: "#2c0a0a", color: "#ef4444", fontSize: 12 }}>{error}</div>
      )}

      {inf && chk && !loading && (
        <div className="space-y-4">
          {/* Situação inferida vs registrada + conflito */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="rounded-lg px-3 py-1.5" style={{ background: "#0f172a", border: `1px solid ${(SITU_CLR[inf.situacao_inferida] ?? "#334155")}40`, color: SITU_CLR[inf.situacao_inferida] ?? "#94a3b8", fontSize: 12, fontWeight: 700, fontFamily: "monospace" }}>
              inferida: {inf.situacao_inferida}
            </span>
            <span className="rounded-lg px-3 py-1.5" style={{ background: "#0f172a", border: "1px solid #334155", color: "#94a3b8", fontSize: 12, fontFamily: "monospace" }}>
              registrada: {chk.situacao_registrada}
            </span>
            {chk.conflito_situacao && (
              <span className="flex items-center gap-1.5 rounded-lg px-3 py-1.5" style={{ background: "#2c0a0a", border: "1px solid #450a0a", color: "#f59e0b", fontSize: 12, fontWeight: 700 }}>
                <AlertTriangle size={14} /> conflito de situação
              </span>
            )}
          </div>

          {/* Conclusões booleanas */}
          <div className="flex gap-2 flex-wrap">
            <BoolPill label="apto_defesa" value={inf.apto_defesa} />
            <BoolPill label="creditos_validos" value={inf.creditos_validos} />
            <BoolPill label="em_risco" value={inf.em_risco} />
          </div>

          {/* Riscos detectados */}
          {inf.riscos_detectados.length > 0 && (
            <div className="rounded-lg p-3 space-y-1" style={{ background: "#1c1002", border: "1px solid #451a03" }}>
              {inf.riscos_detectados.map((r, i) => (
                <div key={i} className="flex items-center gap-2" style={{ fontSize: 12, color: "#fbbf24" }}><AlertTriangle size={12} /> {r}</div>
              ))}
            </div>
          )}

          {/* Pontuações de produção (RL05) */}
          {inf.pontuacoes_producoes.length > 0 && (
            <div>
              <p style={{ fontSize: 10, fontWeight: 700, color: "#475569", letterSpacing: 1, marginBottom: 6, fontFamily: "monospace" }}>PONTUAÇÕES DE PRODUÇÃO (RL05)</p>
              <div className="flex gap-2 flex-wrap">
                {inf.pontuacoes_producoes.map((p) => (
                  <span key={p.producao_id} className="rounded-lg px-2.5 py-1" style={{ background: "#0f172a", border: "1px solid #1e293b", color: "#93c5fd", fontSize: 11, fontFamily: "monospace" }}>
                    {p.producao_id}: {p.score} ({p.nivel_veiculo} ×{p.peso_aplicado})
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Fatos usados pelo motor */}
          <div>
            <button onClick={() => setShowFacts((v) => !v)} className="flex items-center gap-1.5" style={{ fontSize: 11, color: "#60a5fa", fontFamily: "monospace" }}>
              <ChevronRight size={12} style={{ transform: showFacts ? "rotate(90deg)" : "none", transition: "transform .2s" }} />
              {inf.fatos_usados.length} fatos usados pelo motor
            </button>
            {showFacts && (
              <div className="mt-2 rounded-lg p-3 space-y-0.5" style={{ background: "#0b1220", border: "1px solid #1e293b", maxHeight: 200, overflowY: "auto" }}>
                {inf.fatos_usados.map((f, i) => (
                  <div key={i} style={{ fontSize: 10.5, color: "#64748b", fontFamily: "'Courier New',monospace" }}>{f}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const RISK_CFG = {
  apto:     { label:"Apto à Defesa",  color:"#10b981", bg:"#022c22", border:"#064e3b" },
  regular:  { label:"Regular",        color:"#60a5fa", bg:"#0c1829", border:"#1e3a5f" },
  "em-risco":{ label:"Em Risco",      color:"#f59e0b", bg:"#1c1002", border:"#451a03" },
  critico:  { label:"Desligado",      color:"#ef4444", bg:"#2c0a0a", border:"#450a0a" },
};

export function InferencePage() {
  const { token } = useAuth();
  const { studentId, students, setStudentId } = useChecklistStudent();
  const [allStudents, setAllStudents] = useState<Student[]>([]);
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [inf, setInf] = useState<InferenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeConclusion, setActiveConclusion] = useState<string | null>(null);
  const [explainQ, setExplainQ] = useState<string>("c_risco");
  const [timelineRunning, setTimelineRunning] = useState(false);
  const [timelineStep, setTimelineStep] = useState(-1);
  const tlRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Lista real de alunos (metadados dos cards do seletor).
  useEffect(() => {
    if (!token) return;
    getStudents(token).then(setAllStudents).catch(() => setAllStudents([]));
  }, [token]);

  // Inferência real + dados do aluno selecionado — alimentam toda a visualização.
  // Busca o aluno por id (GET /students/{id}, acessível também ao próprio aluno),
  // já que a lista GET /students é restrita a coordenação/orientador.
  useEffect(() => {
    if (!studentId || !token) return;
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getInference(studentId, token), getStudent(token, studentId)])
      .then(([result, record]) => { if (active) { setInf(result); setSelectedStudent(record); } })
      .catch(() => { if (active) { setInf(null); setSelectedStudent(null); setError("Não foi possível carregar a inferência do backend."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [studentId, token]);

  const student: StudentProfile | null =
    selectedStudent && inf && inf.student_id === studentId && selectedStudent.id === studentId
      ? deriveProfile(selectedStudent, inf)
      : null;

  useEffect(() => {
    setActiveConclusion(null);
    setTimelineStep(-1);
    setTimelineRunning(false);
  }, [studentId]);

  useEffect(() => {
    if (student) setExplainQ(student.overallRisk === "apto" ? "c_apto" : "c_risco");
  }, [studentId, student?.overallRisk]);

  useEffect(() => {
    return () => { if (tlRef.current) clearTimeout(tlRef.current); };
  }, []);

  function runTimeline() {
    if (timelineRunning || !student) return;
    setTimelineStep(-1);
    setTimelineRunning(true);
    let i = 0;
    const ruleCount = student.rules.length;
    const tick = () => {
      setTimelineStep(i);
      i++;
      if (i < ruleCount) {
        tlRef.current = setTimeout(tick, 700);
      } else {
        setTimelineRunning(false);
      }
    };
    tlRef.current = setTimeout(tick, 400);
  }

  const risk = student ? RISK_CFG[student.overallRisk] : RISK_CFG.apto;
  const approvedFacts = student ? student.facts.filter((f) => f.value).length : 0;

  return (
    <div className="space-y-5 inference-root" style={{ color:"var(--foreground)" }}>

      {/* ── Painel de inferência real (motor + backend) ── */}
      <RealInferencePanel />

      {/* ── Seletor de aluno (lista real via GET /students) ── */}
      {students && allStudents.length > 0 && (
        <div className="rounded-2xl p-4" style={{ background:"#030712", border:"1px solid #1e293b" }}>
          <p style={{ fontSize:10, fontWeight:700, color:"#475569", letterSpacing:1, marginBottom:12, fontFamily:"monospace" }}>SELECIONAR ALUNO PARA INFERÊNCIA</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {allStudents.map(s => {
              const r = RISK_CFG[cardRisk(s.situacao_inferida)];
              const isSelected = studentId === s.id;
              return (
                <button key={s.id} onClick={() => setStudentId(s.id)}
                  className="rounded-xl p-4 text-left transition-all"
                  style={{ background:isSelected?"#0a1628":"#0f172a", border:`2px solid ${isSelected?r.color+"60":"#1e293b"}`, boxShadow:isSelected?`0 0 20px ${r.color}20`:"none" }}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="rounded-lg flex items-center justify-center" style={{ width:32, height:32, background:r.bg, border:`1px solid ${r.border}` }}>
                      <span style={{ fontSize:13, fontWeight:800, color:r.color }}>{s.nome.trim()[0]?.toUpperCase()}</span>
                    </div>
                    <span className="rounded-lg px-2 py-0.5" style={{ background:r.bg, color:r.color, fontSize:9, fontWeight:800, border:`1px solid ${r.border}`, fontFamily:"monospace" }}>{r.label}</span>
                  </div>
                  <p style={{ fontSize:12, fontWeight:700, color:"#f8fafc" }}>{s.nome}</p>
                  <p style={{ fontSize:10, color:"#475569", marginTop:2, fontFamily:"monospace" }}>{s.matricula}</p>
                  <div className="flex items-center gap-1.5 mt-3">
                    <div className="rounded-full" style={{ width:6, height:6, background:r.color }}/>
                    <span style={{ fontSize:9, color:"#475569", fontFamily:"monospace" }}>{s.situacao_inferida}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b", color:"#64748b", fontSize:13 }}>
          <Loader2 size={16} className="animate-spin" /> Consultando o motor de inferência…
        </div>
      )}
      {error && !loading && (
        <div className="rounded-2xl p-4" style={{ background:"#2c0a0a", border:"1px solid #450a0a", color:"#ef4444", fontSize:13 }}>{error}</div>
      )}

      {student && (
      <>
      {/* ── Header ── */}
      <div className="rounded-2xl p-6 relative overflow-hidden" style={{ background:"linear-gradient(135deg, #030712 0%, #0a1628 50%, #0d0a1f 100%)", border:"1px solid #1e293b", boxShadow:"0 20px 60px rgba(0,0,0,0.5)" }}>
        {/* Animated grid bg */}
        <div style={{ position:"absolute", inset:0, backgroundImage:"linear-gradient(rgba(59,130,246,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.04) 1px, transparent 1px)", backgroundSize:"40px 40px", pointerEvents:"none" }}/>
        <div className="relative flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="rounded-xl p-2.5" style={{ background:"#0f172a", border:"1px solid #3b82f620", boxShadow:"0 0 20px rgba(59,130,246,0.2)" }}>
                <Brain size={22} style={{ color:"#3b82f6" }}/>
              </div>
              <div>
                <h1 style={{ color:"#f8fafc", fontSize:20, fontWeight:900, letterSpacing:-0.5 }}>Motor de Inferência Acadêmica</h1>
                <p style={{ color:"#475569", fontSize:13 }}>Sistema Especialista de Lógica Proposicional para Análise de Situação Acadêmica</p>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {[{ icon:<Database size={11}/>, label:`Base de Fatos: ${student.facts.length} predicados` },{ icon:<GitBranch size={11}/>, label:`${student.rules.length} regras lógicas` },{ icon:<Cpu size={11}/>, label:"Encadeamento progressivo" }].map((item,i) => (
                <div key={i} className="flex items-center gap-1.5 rounded-lg px-2.5 py-1" style={{ background:"#0f172a", border:"1px solid #1e293b" }}>
                  <span style={{ color:"#475569" }}>{item.icon}</span>
                  <span style={{ fontSize:10, color:"#64748b", fontFamily:"monospace" }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Status */}
          <div className="flex items-center gap-3 flex-wrap">
            {[{ n: student.facts.filter(f=>f.value).length, l:"Fatos TRUE", c:"#10b981" },{ n: student.facts.filter(f=>!f.value).length, l:"Fatos FALSE", c:"#ef4444" },{ n: student.rules.filter(r=>r.result).length, l:"Regras OK", c:"#8b5cf6" }].map((s,i)=>(
              <div key={i} className="text-center rounded-xl p-3" style={{ background:"#0f172a", border:"1px solid #1e293b", minWidth:72 }}>
                <p style={{ fontSize:24, fontWeight:900, color:s.c, lineHeight:1 }}>{s.n}</p>
                <p style={{ fontSize:9, color:"#475569", marginTop:3, fontFamily:"monospace" }}>{s.l}</p>
              </div>
            ))}
            <div className="rounded-xl p-3 text-center flex items-center justify-center" style={{ background:risk.bg, border:`1px solid ${risk.border}`, minWidth:90 }}>
              <span style={{ fontSize:11, fontWeight:800, color:risk.color }}>{risk.label}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 1: Facts + Rules ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Facts Database */}
        <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-lg p-2" style={{ background:"#0f172a", border:`1px solid ${FACT_CLR}30` }}>
              <Database size={15} style={{ color:FACT_CLR }}/>
            </div>
            <div>
              <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Base de Fatos</p>
              <p style={{ fontSize:10, color:"#475569", fontFamily:"monospace" }}>Predicados atômicos do estado do aluno</p>
            </div>
            <div className="ml-auto rounded-lg px-2 py-1" style={{ background:"#0f172a", border:"1px solid #1e293b" }}>
              <span style={{ fontSize:10, fontWeight:700, color:FACT_CLR, fontFamily:"monospace" }}>{approvedFacts}/{student.facts.length} TRUE</span>
            </div>
          </div>
          <div className="space-y-2">
            {student.facts.map(f => (
              <div key={f.id} className="rounded-xl p-3 flex items-center gap-3"
                style={{ background:f.value?"#022c22":"#2c0a0a", border:`1px solid ${f.value?"#064e3b":"#450a0a"}`, transition:"all 0.3s" }}>
                <div className="rounded-lg p-2 flex-shrink-0" style={{ background:f.value?"#064e3b":"#450a0a" }}>
                  {f.value ? <CheckCircle2 size={14} style={{ color:TRUE_CLR }}/> : <XCircle size={14} style={{ color:FALSE_CLR }}/>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p style={{ fontSize:12, fontWeight:700, color:"#f8fafc" }}>{f.label}</p>
                    <span className="rounded-full px-1.5" style={{ fontSize:8, fontWeight:700, background:f.value?"#064e3b":"#450a0a", color:truthColor(f.value), fontFamily:"monospace" }}>{f.category}</span>
                  </div>
                  <p style={{ fontSize:10, color:"#64748b", fontFamily:"monospace", marginTop:1 }}>{f.detail}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p style={{ fontSize:13, fontWeight:800, color:truthColor(f.value), fontFamily:"monospace" }}>{f.rawValue}</p>
                  {f.threshold && <p style={{ fontSize:9, color:"#475569", fontFamily:"monospace" }}>meta: {f.threshold}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Rules Database */}
        <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-lg p-2" style={{ background:"#0f172a", border:`1px solid ${RULE_CLR}30` }}>
              <Code2 size={15} style={{ color:RULE_CLR }}/>
            </div>
            <div>
              <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Base de Regras</p>
              <p style={{ fontSize:10, color:"#475569", fontFamily:"monospace" }}>Regras de produção lógica do sistema</p>
            </div>
          </div>
          <div className="space-y-3">
            {student.rules.map((rule, i) => (
              <div key={rule.id} className="rounded-xl p-3" style={{ background:rule.result?"#022c22":"#0f172a", border:`1px solid ${rule.result?"#064e3b":"#1e293b"}` }}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize:9, fontWeight:800, color:RULE_CLR, background:RULE_CLR+"20", padding:"1px 6px", borderRadius:4, fontFamily:"monospace" }}>R{i+1}</span>
                    <p style={{ fontSize:12, fontWeight:700, color:"#f8fafc" }}>{rule.label}</p>
                  </div>
                  <span style={{ fontSize:9, fontWeight:800, color:truthColor(rule.result), background:truthBg(rule.result), padding:"1px 8px", borderRadius:4, border:`1px solid ${truthBorder(rule.result)}`, fontFamily:"monospace", flexShrink:0 }}>
                    {rule.result ? "TRUE" : "FALSE"}
                  </span>
                </div>
                <div className="rounded-lg px-2.5 py-1.5 mb-2" style={{ background:"#030712" }}>
                  <span style={{ fontSize:9, color:"#60a5fa", fontFamily:"monospace" }}>{rule.formula}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {rule.conditions.map((c, j) => (
                    <span key={j} className="rounded-lg px-2 py-0.5" style={{ fontSize:9, background:c.negated?truthBg(!c.value):truthBg(c.value), color:c.negated?NEG_CLR:truthColor(c.value), border:`1px solid ${c.negated?NEG_CLR+"30":truthBorder(c.value)}`, fontFamily:"monospace" }}>
                      {c.negated?"¬":""}{c.label} = {c.negated?(!c.value?"T":"F"):(c.value?"T":"F")}
                    </span>
                  ))}
                </div>
                <p style={{ fontSize:9, color:"#475569", marginTop:6, lineHeight:1.5 }}>{rule.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Inference Graph ── */}
      <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b", boxShadow:"0 0 40px rgba(59,130,246,0.05)" }}>
        <div className="flex items-center justify-between gap-4 mb-5 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="rounded-lg p-2" style={{ background:"#0f172a", border:"1px solid #3b82f630" }}>
              <Network size={15} style={{ color:"#3b82f6" }}/>
            </div>
            <div>
              <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Grafo de Inferência</p>
              <p style={{ fontSize:10, color:"#475569", fontFamily:"monospace" }}>Fatos → Regras → Conclusões · Clique para rastrear</p>
            </div>
          </div>
          <div className="flex gap-2">
            {[{ id:"fact", c:FACT_CLR, l:"Fato" },{ id:"irule", c:RULE_CLR, l:"Regra" },{ id:"crule", c:"#a78bfa", l:"Composta" },{ id:"conc", c:CONC_CLR, l:"Conclusão" }].map(t=>(
              <div key={t.id} className="flex items-center gap-1.5 rounded-lg px-2 py-1" style={{ background:"#0f172a", border:`1px solid ${t.c}30` }}>
                <div className="rounded-sm" style={{ width:8, height:8, background:t.c }}/>
                <span style={{ fontSize:9, color:t.c, fontFamily:"monospace" }}>{t.l}</span>
              </div>
            ))}
          </div>
        </div>
        <InferenceGraph student={student} activeConclusion={activeConclusion} onConclusion={setActiveConclusion}/>
      </div>

      {/* ── Conclusions Panel ── */}
      <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b" }}>
        <div className="flex items-center gap-3 mb-4">
          <div className="rounded-lg p-2" style={{ background:"#0f172a", border:`1px solid ${CONC_CLR}30` }}>
            <Shield size={15} style={{ color:CONC_CLR }}/>
          </div>
          <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Conclusões Derivadas</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {student.conclusions.map(c => (
            <button key={c.id} onClick={() => setExplainQ(c.id)}
              className="rounded-xl p-4 text-left transition-all"
              style={{ background:explainQ===c.id?(c.result?"#022c22":"#2c0a0a"):truthBg(c.result), border:`2px solid ${explainQ===c.id?truthColor(c.result)+"60":truthBorder(c.result)}`, boxShadow:explainQ===c.id?`0 0 20px ${truthColor(c.result)}20`:"none" }}>
              <div className="flex items-center justify-between mb-3">
                <span style={{ fontSize:9, fontWeight:700, color:"#475569", fontFamily:"monospace" }}>CONCLUSÃO</span>
                {c.result ? <CheckCircle2 size={16} style={{ color:TRUE_CLR }}/> : <XCircle size={16} style={{ color:FALSE_CLR }}/>}
              </div>
              <p style={{ fontSize:13, fontWeight:700, color:"#f8fafc", marginBottom:6 }}>{c.label}</p>
              <div className="rounded-lg px-2.5 py-1.5" style={{ background:"#030712" }}>
                <span style={{ fontSize:11, fontWeight:900, color:truthColor(c.result), fontFamily:"monospace" }}>{c.result ? "✓ VERDADEIRO" : "✗ FALSO"}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Explainability + Query Console ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Explainability */}
        <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="rounded-lg p-2" style={{ background:"#0f172a", border:"1px solid #f59e0b30" }}>
              <Search size={15} style={{ color:"#f59e0b" }}/>
            </div>
            <div>
              <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Painel de Explicabilidade</p>
              <p style={{ fontSize:10, color:"#475569", fontFamily:"monospace" }}>Rastreamento causal da inferência</p>
            </div>
          </div>
          {/* Question selector */}
          <div className="flex gap-2 mb-4 flex-wrap">
            {student.conclusions.map(c => (
              <button key={c.id} onClick={() => setExplainQ(c.id)}
                className="rounded-lg px-3 py-1.5 transition-all"
                style={{ background:explainQ===c.id?"#1e3a5f":"#0f172a", color:explainQ===c.id?"#60a5fa":"#475569", fontSize:10, fontWeight:700, border:`1px solid ${explainQ===c.id?"#2563eb30":"#1e293b"}`, fontFamily:"monospace" }}>
                {c.label}?
              </button>
            ))}
          </div>
          <ExplainPanel student={student} question={explainQ}/>
        </div>

        {/* Query Console */}
        <div className="rounded-2xl overflow-hidden" style={{ minHeight:400 }}>
          <QueryConsole student={student}/>
        </div>
      </div>

      {/* ── Rule Execution Timeline ── */}
      <div className="rounded-2xl p-5" style={{ background:"#030712", border:"1px solid #1e293b" }}>
        <div className="flex items-center justify-between gap-4 mb-5 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="rounded-lg p-2" style={{ background:"#0f172a", border:"1px solid #a78bfa30" }}>
              <Activity size={15} style={{ color:"#a78bfa" }}/>
            </div>
            <div>
              <p style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>Linha do Tempo de Execução</p>
              <p style={{ fontSize:10, color:"#475569", fontFamily:"monospace" }}>Sequência de disparo das regras com encadeamento progressivo</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setTimelineStep(-1); setTimelineRunning(false); }}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2"
              style={{ background:"#0f172a", color:"#475569", fontSize:11, fontWeight:700, border:"1px solid #1e293b", fontFamily:"monospace" }}>
              <RotateCcw size={11}/> Reset
            </button>
            <button onClick={runTimeline} disabled={timelineRunning}
              className="flex items-center gap-2 rounded-lg px-4 py-2"
              style={{ background:timelineRunning?"#1e293b":"#1e3a5f", color:timelineRunning?"#475569":"#60a5fa", fontSize:11, fontWeight:700, fontFamily:"monospace" }}>
              <Play size={11}/> {timelineRunning ? "Executando..." : "Executar Inferência"}
            </button>
          </div>
        </div>
        {/* Progress bar */}
        {timelineStep >= 0 && (
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5">
              <span style={{ fontSize:9, color:"#475569", fontFamily:"monospace" }}>PROGRESSO DA INFERÊNCIA</span>
              <span style={{ fontSize:9, color:"#60a5fa", fontFamily:"monospace" }}>{timelineStep+1}/{student.rules.length} regras</span>
            </div>
            <div className="rounded-full overflow-hidden" style={{ height:4, background:"#0f172a" }}>
              <div className="h-full rounded-full transition-all" style={{ width:`${((timelineStep+1)/student.rules.length)*100}%`, background:"linear-gradient(90deg, #3b82f6, #8b5cf6)" }}/>
            </div>
          </div>
        )}
        <RuleTimeline student={student} running={timelineRunning} step={timelineStep}/>
        {timelineStep === student.rules.length - 1 && (
          <div className="mt-4 rounded-xl px-4 py-3 flex items-center gap-3" style={{ background:student.rules[3].result?"#022c22":"#2c0a0a", border:`1px solid ${student.rules[3].result?"#064e3b":"#450a0a"}` }}>
            {student.rules[3].result ? <CheckCircle2 size={16} style={{ color:TRUE_CLR }}/> : <AlertTriangle size={16} style={{ color:FALSE_CLR }}/>}
            <span style={{ fontSize:12, fontWeight:700, color:truthColor(student.rules[3].result), fontFamily:"monospace" }}>
              INFERÊNCIA CONCLUÍDA · {student.name} — {student.rules[3].result ? "APTO À DEFESA" : "NÃO APTO À DEFESA"}
            </span>
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}

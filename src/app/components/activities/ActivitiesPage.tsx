import React, { useState, useMemo } from "react";
import {
  Plus, X, Check, Upload, FileText, Award, BookOpen, Users,
  GraduationCap, Code2, Lightbulb, Clock, Search, CheckCircle2,
  XCircle, Circle, AlertCircle, Eye, Download, Star, MessageSquare,
  ArrowRight, ChevronDown, ChevronUp, Shield, Paperclip, Filter,
  BarChart2, Layers, Clipboard,
} from "lucide-react";
import { useApp } from "../../context/AppContext";

// ─── Types ────────────────────────────────────────────────────────────────────

type ActivityType =
  | "artigo-publicado"
  | "artigo-submetido"
  | "software"
  | "patente"
  | "banca"
  | "estagio-docencia"
  | "disciplina";

type ActivityStatus = "rascunho" | "enviado" | "em-validacao" | "aprovado" | "rejeitado";
type RelevanceLevel = "A1" | "A2" | "A3" | "A4" | "B1" | "B2" | "B3" | "B4" | "C" | "N/A";
type StepStatus = "concluido" | "em-andamento" | "pendente" | "rejeitado";
type TabKey = "registro" | "validacao" | "aprovadas" | "rejeitadas";
type ModalState =
  | { kind: "register"; editing?: Activity }
  | { kind: "detail"; activity: Activity }
  | { kind: "validate"; activity: Activity }
  | null;

interface ValidationStep {
  stage: "envio" | "orientador" | "coordenacao" | "conclusao";
  label: string;
  responsavel: string;
  status: StepStatus;
  data?: string;
  comentario?: string;
}

interface Activity {
  id: string;
  tipo: ActivityType;
  titulo: string;
  veiculo: string;
  nivelRelevancia: RelevanceLevel;
  observacao: string;
  comprovante: string | null;
  creditos: number;
  semestre: string;
  status: ActivityStatus;
  dataSubmissao: string;
  dataAprovacao?: string;
  steps: ValidationStep[];
  motivoRejeicao?: string;
  coautores: string[];
  doi?: string;
  nota?: number;
}

// ─── Config ───────────────────────────────────────────────────────────────────

const TIPO_CFG: Record<ActivityType, { label: string; color: string; bg: string; border: string; icon: React.ReactNode; creditosPadrao: number }> = {
  "artigo-publicado":  { label: "Artigo Publicado",   color: "#123C7A", bg: "#eef3fc", border: "#b8cef7", icon: <BookOpen size={14} />,      creditosPadrao: 4 },
  "artigo-submetido":  { label: "Artigo Submetido",   color: "#7c3aed", bg: "#ede9fe", border: "#c4b5fd", icon: <FileText size={14} />,       creditosPadrao: 1 },
  "software":          { label: "Software Registrado", color: "#0891b2", bg: "#e0f7fa", border: "#99d8e8", icon: <Code2 size={14} />,          creditosPadrao: 2 },
  "patente":           { label: "Patente",             color: "#D4A017", bg: "#fef9c3", border: "#fde68a", icon: <Lightbulb size={14} />,      creditosPadrao: 3 },
  "banca":             { label: "Banca",               color: "#db2777", bg: "#fce7f3", border: "#fbcfe8", icon: <Users size={14} />,          creditosPadrao: 1 },
  "estagio-docencia":  { label: "Estágio Docência",   color: "#1F8A70", bg: "#dcfce7", border: "#86efac", icon: <GraduationCap size={14} />,  creditosPadrao: 2 },
  "disciplina":        { label: "Disciplina",          color: "#ea580c", bg: "#fff7ed", border: "#fdba74", icon: <Award size={14} />,          creditosPadrao: 4 },
};

const STATUS_CFG: Record<ActivityStatus, { label: string; color: string; bg: string; border: string; icon: React.ReactNode }> = {
  rascunho:      { label: "Rascunho",       color: "#64748b", bg: "#f1f5f9", border: "#cbd5e1", icon: <Circle size={11} /> },
  enviado:       { label: "Enviado",         color: "#0891b2", bg: "#e0f7fa", border: "#99d8e8", icon: <ArrowRight size={11} /> },
  "em-validacao":{ label: "Em Validação",   color: "#D4A017", bg: "#fef9c3", border: "#fde68a", icon: <Clock size={11} /> },
  aprovado:      { label: "Aprovado",        color: "#1F8A70", bg: "#dcfce7", border: "#86efac", icon: <CheckCircle2 size={11} /> },
  rejeitado:     { label: "Rejeitado",       color: "#dc2626", bg: "#fee2e2", border: "#fca5a5", icon: <XCircle size={11} /> },
};

const RELEVANCE_CFG: Record<RelevanceLevel, { color: string; bg: string; points: number }> = {
  A1: { color: "#123C7A", bg: "#eef3fc", points: 4 },
  A2: { color: "#1F8A70", bg: "#dcfce7", points: 3 },
  A3: { color: "#0891b2", bg: "#e0f7fa", points: 3 },
  A4: { color: "#7c3aed", bg: "#ede9fe", points: 2 },
  B1: { color: "#D4A017", bg: "#fef9c3", points: 2 },
  B2: { color: "#ea580c", bg: "#fff7ed", points: 2 },
  B3: { color: "#db2777", bg: "#fce7f3", points: 1 },
  B4: { color: "#64748b", bg: "#f1f5f9", points: 1 },
  C:  { color: "#9ca3af", bg: "#f9fafb", points: 0 },
  "N/A": { color: "#94a3b8", bg: "#f8fafc", points: 0 },
};

const CREDITS_META = 60;

// ─── Mock Data ────────────────────────────────────────────────────────────────

function makeSteps(orientStatus: StepStatus, coordStatus: StepStatus, orientDate?: string, coordDate?: string, orientComment?: string, coordComment?: string): ValidationStep[] {
  return [
    { stage: "envio",       label: "Envio pelo Aluno",          responsavel: "Lucas Ferreira Silva", status: "concluido",   data: "15/01/2026" },
    { stage: "orientador",  label: "Análise do Orientador",     responsavel: "Profa. Dra. Carla Mendes", status: orientStatus, data: orientDate, comentario: orientComment },
    { stage: "coordenacao", label: "Análise da Coordenação",    responsavel: "Prof. Dr. Roberto Almeida", status: coordStatus, data: coordDate, comentario: coordComment },
    { stage: "conclusao",   label: "Conclusão",                 responsavel: "Sistema",                  status: coordStatus === "concluido" ? "concluido" : coordStatus === "rejeitado" ? "rejeitado" : "pendente" },
  ];
}

const INITIAL_ACTIVITIES: Activity[] = [
  {
    id: "a1", tipo: "artigo-publicado", titulo: "Efficient Neural Network Compression via Structured Pruning and Knowledge Distillation",
    veiculo: "IEEE Transactions on Neural Networks and Learning Systems (TNNLS)", nivelRelevancia: "A1",
    observacao: "Artigo principal do doutorado, revisado por 3 pareceristas.", comprovante: "tnnls_acceptance_2025.pdf",
    creditos: 4, semestre: "2025/1", status: "aprovado", dataSubmissao: "10/02/2025", dataAprovacao: "18/03/2025",
    coautores: ["Profa. Dra. Carla Mendes", "Dr. Rafael Oliveira"], doi: "10.1109/TNNLS.2025.1234567",
    steps: makeSteps("concluido","concluido","20/02/2025","18/03/2025","Artigo de excelente qualidade. Recomendo aprovação.","Aprovado com louvor. Créditos máximos concedidos."),
  },
  {
    id: "a2", tipo: "artigo-publicado", titulo: "Adaptive Quantization Strategies for Edge AI Deployment",
    veiculo: "ACM Computing Surveys", nivelRelevancia: "A1",
    observacao: "Artigo de survey sobre quantização de redes neurais.", comprovante: "acm_survey_2025.pdf",
    creditos: 4, semestre: "2025/2", status: "aprovado", dataSubmissao: "05/06/2025", dataAprovacao: "22/07/2025",
    coautores: ["Profa. Dra. Carla Mendes"], doi: "10.1145/3589334.2025",
    steps: makeSteps("concluido","concluido","15/06/2025","22/07/2025","Importante contribuição para a área.","Aprovado. Créditos concedidos conforme tabela A1."),
  },
  {
    id: "a3", tipo: "artigo-submetido", titulo: "Real-time Neural Architecture Search for Resource-Constrained Devices",
    veiculo: "International Conference on Machine Learning (ICML 2026)", nivelRelevancia: "A1",
    observacao: "Aguardando revisão. Submetido em outubro de 2025.", comprovante: "icml2026_submission.pdf",
    creditos: 1, semestre: "2025/2", status: "em-validacao", dataSubmissao: "20/10/2025",
    coautores: ["Profa. Dra. Carla Mendes", "Lucas Gomes", "Fernanda Castro"],
    steps: makeSteps("concluido","em-andamento","30/10/2025",undefined,"Submetido para conferência de alto impacto. Aprovação recomendada."),
  },
  {
    id: "a4", tipo: "software", titulo: "NeuralCompress SDK — Biblioteca de Compressão Neural para Edge Devices",
    veiculo: "INPI — Instituto Nacional da Propriedade Industrial", nivelRelevancia: "N/A",
    observacao: "Registro de software BR512025001234-0.", comprovante: "inpi_registro_software.pdf",
    creditos: 2, semestre: "2025/1", status: "aprovado", dataSubmissao: "08/03/2025", dataAprovacao: "15/04/2025",
    coautores: ["Profa. Dra. Carla Mendes"],
    steps: makeSteps("concluido","concluido","18/03/2025","15/04/2025","Software com documentação completa. Aprovado.","Registro válido. Créditos concedidos."),
  },
  {
    id: "a5", tipo: "patente", titulo: "Método e Sistema para Compressão Adaptativa de Modelos de Aprendizado Profundo",
    veiculo: "INPI — Instituto Nacional da Propriedade Industrial", nivelRelevancia: "N/A",
    observacao: "Patente de invenção em fase de análise. Protocolo PI2025/073421.", comprovante: "patente_pi2025.pdf",
    creditos: 3, semestre: "2025/2", status: "em-validacao", dataSubmissao: "12/11/2025",
    coautores: ["Profa. Dra. Carla Mendes", "Prof. Dr. Roberto Almeida"],
    steps: makeSteps("em-andamento","pendente"),
  },
  {
    id: "a6", tipo: "banca", titulo: "Banca de Defesa de Dissertação — Marcelo Augusto Santos",
    veiculo: "PPGCC — Programa de Pós-Graduação em Ciência da Computação", nivelRelevancia: "N/A",
    observacao: "Dissertação sobre redes neurais recorrentes.", comprovante: "ata_banca_marcelo.pdf",
    creditos: 1, semestre: "2024/2", status: "aprovado", dataSubmissao: "05/10/2024", dataAprovacao: "20/10/2024",
    coautores: [],
    steps: makeSteps("concluido","concluido","12/10/2024","20/10/2024","Participação confirmada na ata.","Aprovado. 1 crédito concedido."),
  },
  {
    id: "a7", tipo: "banca", titulo: "Banca de Qualificação — Ana Paula Ribeiro",
    veiculo: "PPGCC — Programa de Pós-Graduação em Ciência da Computação", nivelRelevancia: "N/A",
    observacao: "Qualificação de doutorado sobre visão computacional.", comprovante: null,
    creditos: 1, semestre: "2026/1", status: "em-validacao", dataSubmissao: "15/04/2026",
    coautores: [],
    steps: makeSteps("em-andamento","pendente"),
  },
  {
    id: "a8", tipo: "estagio-docencia", titulo: "Estágio de Docência — Estruturas de Dados e Algoritmos",
    veiculo: "Departamento de Ciência da Computação — UFCC", nivelRelevancia: "N/A",
    observacao: "Ministrei 30h de aulas, 2024/2. Avaliação do docente responsável: Ótimo.", comprovante: "estagio_docencia_2024_2.pdf",
    creditos: 2, semestre: "2024/2", status: "aprovado", dataSubmissao: "10/12/2024", dataAprovacao: "18/12/2024",
    coautores: [], nota: 9.8,
    steps: makeSteps("concluido","concluido","12/12/2024","18/12/2024","Relatório de docência exemplar.","Aprovado. 2 créditos concedidos."),
  },
  {
    id: "a9", tipo: "estagio-docencia", titulo: "Estágio de Docência — Inteligência Artificial",
    veiculo: "Departamento de Ciência da Computação — UFCC", nivelRelevancia: "N/A",
    observacao: "Estágio em andamento, 2025/1. 20h realizadas de 30h previstas.", comprovante: null,
    creditos: 2, semestre: "2025/1", status: "enviado", dataSubmissao: "20/03/2025",
    coautores: [],
    steps: makeSteps("pendente","pendente"),
  },
  {
    id: "a10", tipo: "disciplina", titulo: "Aprendizado de Máquina Avançado",
    veiculo: "PPGCC — Programa de Pós-Graduação em Ciência da Computação", nivelRelevancia: "N/A",
    observacao: "Disciplina obrigatória do doutorado.", comprovante: "historico_2024_1.pdf",
    creditos: 4, semestre: "2024/1", status: "aprovado", dataSubmissao: "20/07/2024", dataAprovacao: "10/08/2024",
    coautores: [], nota: 9.5,
    steps: makeSteps("concluido","concluido","25/07/2024","10/08/2024","Aprovado com histórico escolar.","Registrado no sistema."),
  },
  {
    id: "a11", tipo: "disciplina", titulo: "Metodologia Científica e Redação Acadêmica",
    veiculo: "PPGCC — Programa de Pós-Graduação em Ciência da Computação", nivelRelevancia: "N/A",
    observacao: "", comprovante: "historico_2024_1.pdf",
    creditos: 2, semestre: "2024/1", status: "aprovado", dataSubmissao: "20/07/2024", dataAprovacao: "10/08/2024",
    coautores: [], nota: 10.0,
    steps: makeSteps("concluido","concluido","25/07/2024","10/08/2024","Aprovado.","Registrado."),
  },
  {
    id: "a12", tipo: "disciplina", titulo: "Computação em Nuvem e Sistemas Distribuídos",
    veiculo: "PPGCC — Programa de Pós-Graduação em Ciência da Computação", nivelRelevancia: "N/A",
    observacao: "Disciplina em andamento, aguardando nota final.", comprovante: null,
    creditos: 4, semestre: "2025/1", status: "rascunho", dataSubmissao: "—",
    coautores: [],
    steps: makeSteps("pendente","pendente"),
  },
  {
    id: "a13", tipo: "artigo-publicado", titulo: "Lightweight Federated Learning for IoT Networks",
    veiculo: "Computer Networks (Elsevier)", nivelRelevancia: "B1",
    observacao: "Artigo rejeitado por ausência de comprovante válido de aceitação.", comprovante: null,
    creditos: 0, semestre: "2024/2", status: "rejeitado", dataSubmissao: "14/11/2024",
    coautores: ["Lucas Gomes"], doi: "pending",
    motivoRejeicao: "Comprovante de publicação não reconhecido como carta de aceitação oficial. Necessário enviar documento emitido pelo editor-chefe com ISSN e número do artigo.",
    steps: [
      { stage: "envio",       label: "Envio pelo Aluno",       responsavel: "Lucas Ferreira Silva",     status: "concluido", data: "14/11/2024" },
      { stage: "orientador",  label: "Análise do Orientador",  responsavel: "Profa. Dra. Carla Mendes", status: "concluido", data: "20/11/2024", comentario: "Encaminhado para análise da coordenação." },
      { stage: "coordenacao", label: "Análise da Coordenação", responsavel: "Prof. Dr. Roberto Almeida",status: "rejeitado", data: "28/11/2024", comentario: "Comprovante inválido. Solicitar documento oficial." },
      { stage: "conclusao",   label: "Conclusão",              responsavel: "Sistema",                  status: "rejeitado", data: "28/11/2024" },
    ],
  },
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Badge({ children, color, bg, border }: { children: React.ReactNode; color: string; bg: string; border: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg" style={{ background: bg, color, border: `1px solid ${border}`, fontSize: 10, fontWeight: 700, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function StatusBadge({ status }: { status: ActivityStatus }) {
  const cfg = STATUS_CFG[status];
  return <Badge color={cfg.color} bg={cfg.bg} border={cfg.border}>{cfg.icon}{cfg.label}</Badge>;
}

function TipoBadge({ tipo }: { tipo: ActivityType }) {
  const cfg = TIPO_CFG[tipo];
  return <Badge color={cfg.color} bg={cfg.bg} border={cfg.border}>{cfg.icon}{cfg.label}</Badge>;
}

function RelevanceBadge({ level }: { level: RelevanceLevel }) {
  const cfg = RELEVANCE_CFG[level];
  return <Badge color={cfg.color} bg={cfg.bg} border={`${cfg.color}40`}><Star size={9}/>{level}</Badge>;
}

function PBar({ value, color, h = 6 }: { value: number; color: string; h?: number }) {
  return (
    <div className="rounded-full overflow-hidden w-full" style={{ height: h, background: `${color}20` }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(value, 100)}%`, background: color }} />
    </div>
  );
}

function stepColor(s: StepStatus): string {
  return s === "concluido" ? "#1F8A70" : s === "em-andamento" ? "#D4A017" : s === "rejeitado" ? "#dc2626" : "#cbd5e1";
}

function stepBg(s: StepStatus): string {
  return s === "concluido" ? "#dcfce7" : s === "em-andamento" ? "#fef9c3" : s === "rejeitado" ? "#fee2e2" : "#f1f5f9";
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "concluido")   return <CheckCircle2 size={16} />;
  if (status === "rejeitado")   return <XCircle size={16} />;
  if (status === "em-andamento") return <Clock size={16} />;
  return <Circle size={16} />;
}

// ─── Validation Workflow ──────────────────────────────────────────────────────

function ValidationWorkflow({ steps }: { steps: ValidationStep[] }) {
  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
      <p style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", letterSpacing: 1, marginBottom: 16 }}>FLUXO DE VALIDAÇÃO</p>
      <div className="relative">
        {steps.map((step, i) => (
          <div key={step.stage} className="flex gap-4" style={{ marginBottom: i < steps.length - 1 ? 0 : 0 }}>
            {/* Spine */}
            <div className="flex flex-col items-center" style={{ minWidth: 32 }}>
              <div className="rounded-full flex items-center justify-center flex-shrink-0"
                style={{ width: 32, height: 32, background: stepBg(step.status), color: stepColor(step.status), border: `2px solid ${stepColor(step.status)}` }}>
                <StepIcon status={step.status} />
              </div>
              {i < steps.length - 1 && (
                <div style={{ width: 2, flexGrow: 1, minHeight: 24, background: step.status === "concluido" ? "#1F8A70" : "#e2e8f0", marginTop: 2, marginBottom: 2 }} />
              )}
            </div>
            {/* Content */}
            <div style={{ paddingBottom: i < steps.length - 1 ? 20 : 0, minWidth: 0, flex: 1 }}>
              <div className="flex items-center gap-2 flex-wrap">
                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)" }}>{step.label}</p>
                <span style={{ fontSize: 10, fontWeight: 700, color: stepColor(step.status), background: stepBg(step.status), padding: "2px 8px", borderRadius: 6, border: `1px solid ${stepColor(step.status)}40` }}>
                  {step.status === "concluido" ? "Concluído" : step.status === "em-andamento" ? "Em Andamento" : step.status === "rejeitado" ? "Rejeitado" : "Pendente"}
                </span>
              </div>
              <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 2 }}>{step.responsavel}{step.data ? ` · ${step.data}` : ""}</p>
              {step.comentario && (
                <div className="mt-2 rounded-xl px-3 py-2" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                  <div className="flex items-start gap-1.5">
                    <MessageSquare size={11} style={{ color: "var(--muted-foreground)", marginTop: 1, flexShrink: 0 }} />
                    <p style={{ fontSize: 11, color: "var(--foreground)", lineHeight: 1.5 }}>{step.comentario}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function DetailModal({ activity, onClose, onValidate, canValidate }: {
  activity: Activity; onClose: () => void; onValidate: () => void; canValidate: boolean;
}) {
  const tipo = TIPO_CFG[activity.tipo];
  const status = STATUS_CFG[activity.status];
  const [tab, setTab] = useState<"info" | "workflow" | "comprovante">("info");

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4" style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(2px)" }} onClick={onClose}>
      <div className="w-full md:max-w-2xl rounded-t-2xl md:rounded-2xl flex flex-col" style={{ background: "var(--card)", boxShadow: "0 -8px 40px rgba(0,0,0,0.2)", maxHeight: "92vh" }} onClick={e => e.stopPropagation()}>
        {/* Mobile drag handle */}
        <div className="md:hidden flex justify-center pt-3 pb-1">
          <div style={{ width: 36, height: 4, borderRadius: 2, background: "var(--border)" }} />
        </div>
        {/* Header */}
        <div className="flex items-start justify-between p-4 md:p-6 pb-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex-1 min-w-0 pr-4">
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <TipoBadge tipo={activity.tipo} />
              <StatusBadge status={activity.status} />
              {activity.nivelRelevancia !== "N/A" && <RelevanceBadge level={activity.nivelRelevancia} />}
            </div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--foreground)", lineHeight: 1.4 }}>{activity.titulo}</h2>
          </div>
          <button onClick={onClose} className="rounded-xl p-2 flex-shrink-0" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}><X size={16} /></button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 pt-4">
          {[{ id: "info", label: "Informações" }, { id: "workflow", label: "Validação" }, { id: "comprovante", label: "Comprovante" }].map(t => (
            <button key={t.id} onClick={() => setTab(t.id as typeof tab)}
              className="px-4 py-2 rounded-lg transition-all"
              style={{ background: tab === t.id ? "#123C7A" : "transparent", color: tab === t.id ? "#fff" : "var(--muted-foreground)", fontSize: 12, fontWeight: 700, border: tab === t.id ? "none" : "1px solid transparent" }}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {tab === "info" && (
            <>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Veículo / Instituição" value={activity.veiculo} />
                <Field label="Semestre" value={activity.semestre} />
                <Field label="Créditos" value={`${activity.creditos} crédito${activity.creditos !== 1 ? "s" : ""}`} />
                <Field label="Data de Submissão" value={activity.dataSubmissao} />
                {activity.dataAprovacao && <Field label="Data de Aprovação" value={activity.dataAprovacao} />}
                {activity.nota !== undefined && <Field label="Nota" value={`${activity.nota}`} />}
                {activity.doi && <Field label="DOI" value={activity.doi} />}
              </div>
              {activity.coautores.length > 0 && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", marginBottom: 8 }}>COAUTORES</p>
                  <div className="flex flex-wrap gap-2">
                    {activity.coautores.map((c, i) => (
                      <span key={i} className="px-2.5 py-1 rounded-lg" style={{ background: "var(--muted)", color: "var(--foreground)", fontSize: 12, fontWeight: 600 }}>{c}</span>
                    ))}
                  </div>
                </div>
              )}
              {activity.observacao && (
                <div>
                  <p style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", marginBottom: 6 }}>OBSERVAÇÃO</p>
                  <p style={{ fontSize: 13, color: "var(--foreground)", lineHeight: 1.6, background: "var(--muted)", padding: "10px 14px", borderRadius: 10 }}>{activity.observacao}</p>
                </div>
              )}
              {activity.motivoRejeicao && (
                <div className="rounded-xl p-4" style={{ background: "#fee2e2", border: "1px solid #fca5a5" }}>
                  <div className="flex items-start gap-2">
                    <XCircle size={15} style={{ color: "#dc2626", flexShrink: 0, marginTop: 1 }} />
                    <div>
                      <p style={{ fontSize: 12, fontWeight: 700, color: "#dc2626", marginBottom: 4 }}>Motivo da Rejeição</p>
                      <p style={{ fontSize: 12, color: "#991b1b", lineHeight: 1.6 }}>{activity.motivoRejeicao}</p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          {tab === "workflow" && <ValidationWorkflow steps={activity.steps} />}
          {tab === "comprovante" && (
            <div className="flex flex-col items-center justify-center py-10">
              {activity.comprovante ? (
                <div className="text-center">
                  <div className="rounded-2xl p-8 mb-4" style={{ background: "var(--muted)" }}>
                    <Paperclip size={40} style={{ color: "#123C7A", margin: "0 auto 12px" }} />
                    <p style={{ fontSize: 14, fontWeight: 700, color: "var(--foreground)" }}>{activity.comprovante}</p>
                    <p style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 4 }}>Documento enviado</p>
                  </div>
                  <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl mx-auto" style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 700 }}>
                    <Download size={14} /> Baixar Comprovante
                  </button>
                </div>
              ) : (
                <div className="text-center">
                  <div className="rounded-2xl p-8 mb-4 border-2 border-dashed" style={{ borderColor: "var(--border)" }}>
                    <Upload size={40} style={{ color: "var(--muted-foreground)", margin: "0 auto 12px" }} />
                    <p style={{ fontSize: 14, fontWeight: 600, color: "var(--foreground)" }}>Nenhum comprovante enviado</p>
                    <p style={{ fontSize: 12, color: "var(--muted-foreground)", marginTop: 4 }}>Envie o comprovante para iniciar a validação</p>
                  </div>
                  <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl mx-auto" style={{ background: "#D4A017", color: "#fff", fontSize: 13, fontWeight: 700 }}>
                    <Upload size={14} /> Enviar Comprovante
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {canValidate && activity.status === "em-validacao" && (
          <div className="flex gap-3 p-6 pt-0">
            <button onClick={onValidate} className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5" style={{ background: "#123C7A", color: "#fff", fontSize: 13, fontWeight: 700 }}>
              <Shield size={14} /> Iniciar Validação
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)", letterSpacing: 0.5, marginBottom: 4 }}>{label.toUpperCase()}</p>
      <p style={{ fontSize: 13, color: "var(--foreground)", fontWeight: 500 }}>{value}</p>
    </div>
  );
}

// ─── Validate Modal ───────────────────────────────────────────────────────────

function ValidateModal({ activity, onClose, onApprove, onReject }: {
  activity: Activity; onClose: () => void;
  onApprove: (comment: string) => void; onReject: (reason: string) => void;
}) {
  const [comment, setComment] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [mode, setMode] = useState<"idle" | "approve" | "reject">("idle");

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4" style={{ background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)" }} onClick={onClose}>
      <div className="w-full md:max-w-lg rounded-t-2xl md:rounded-2xl overflow-y-auto" style={{ background: "var(--card)", boxShadow: "0 -8px 40px rgba(0,0,0,0.25)", maxHeight: "90vh" }} onClick={e => e.stopPropagation()}>
        <div className="md:hidden flex justify-center pt-3 pb-1"><div style={{ width: 36, height: 4, borderRadius: 2, background: "var(--border)" }} /></div>
        <div className="p-5 md:p-6" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="rounded-xl p-2" style={{ background: "#eef3fc" }}><Shield size={16} style={{ color: "#123C7A" }} /></div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--foreground)" }}>Validar Atividade</h2>
            </div>
            <button onClick={onClose} className="rounded-xl p-2" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}><X size={16} /></button>
          </div>
          <div className="rounded-xl p-3" style={{ background: "var(--muted)", border: "1px solid var(--border)" }}>
            <TipoBadge tipo={activity.tipo} />
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)", marginTop: 6, lineHeight: 1.4 }}>{activity.titulo}</p>
            <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 4 }}>{activity.veiculo}</p>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <ValidationWorkflow steps={activity.steps} />

          {mode === "idle" && (
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setMode("approve")} className="flex items-center justify-center gap-2 rounded-xl py-3" style={{ background: "#dcfce7", color: "#1F8A70", border: "1px solid #86efac", fontWeight: 700, fontSize: 13 }}>
                <Check size={15} /> Aprovar
              </button>
              <button onClick={() => setMode("reject")} className="flex items-center justify-center gap-2 rounded-xl py-3" style={{ background: "#fee2e2", color: "#dc2626", border: "1px solid #fca5a5", fontWeight: 700, fontSize: 13 }}>
                <X size={15} /> Rejeitar
              </button>
            </div>
          )}

          {mode === "approve" && (
            <div className="space-y-3">
              <div className="rounded-xl p-3" style={{ background: "#dcfce7", border: "1px solid #86efac" }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: "#1F8A70" }}>Aprovação de {activity.creditos} crédito(s)</p>
              </div>
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>COMENTÁRIO (OPCIONAL)</label>
                <textarea value={comment} onChange={e => setComment(e.target.value)} rows={3} placeholder="Adicione um comentário sobre a aprovação..."
                  className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: 12, color: "var(--foreground)" }} />
              </div>
              <div className="flex gap-2">
                <button onClick={() => setMode("idle")} className="px-4 py-2.5 rounded-xl" style={{ background: "var(--muted)", color: "var(--foreground)", fontSize: 12, fontWeight: 700 }}>Voltar</button>
                <button onClick={() => onApprove(comment)} className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5" style={{ background: "#1F8A70", color: "#fff", fontSize: 13, fontWeight: 700 }}>
                  <CheckCircle2 size={14} /> Confirmar Aprovação
                </button>
              </div>
            </div>
          )}

          {mode === "reject" && (
            <div className="space-y-3">
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "#dc2626", display: "block", marginBottom: 6 }}>MOTIVO DA REJEIÇÃO *</label>
                <textarea value={rejectReason} onChange={e => setRejectReason(e.target.value)} rows={4} placeholder="Descreva o motivo da rejeição e o que deve ser corrigido..."
                  className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
                  style={{ border: "1px solid #fca5a5", background: "#fff5f5", fontSize: 12, color: "var(--foreground)" }} />
              </div>
              <div className="flex gap-2">
                <button onClick={() => setMode("idle")} className="px-4 py-2.5 rounded-xl" style={{ background: "var(--muted)", color: "var(--foreground)", fontSize: 12, fontWeight: 700 }}>Voltar</button>
                <button onClick={() => rejectReason.trim() && onReject(rejectReason)} className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5" style={{ background: rejectReason.trim() ? "#dc2626" : "#e5e7eb", color: rejectReason.trim() ? "#fff" : "#9ca3af", fontSize: 13, fontWeight: 700 }}>
                  <XCircle size={14} /> Confirmar Rejeição
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Register Modal ───────────────────────────────────────────────────────────

const RELEVANCE_OPTIONS: RelevanceLevel[] = ["A1","A2","A3","A4","B1","B2","B3","B4","C","N/A"];

function RegisterModal({ editing, onClose, onSave }: {
  editing?: Activity; onClose: () => void; onSave: (a: Omit<Activity, "id" | "steps">) => void;
}) {
  const [tipo, setTipo] = useState<ActivityType>(editing?.tipo ?? "artigo-publicado");
  const [titulo, setTitulo] = useState(editing?.titulo ?? "");
  const [veiculo, setVeiculo] = useState(editing?.veiculo ?? "");
  const [relevancia, setRelevancia] = useState<RelevanceLevel>(editing?.nivelRelevancia ?? "A1");
  const [creditos, setCreditos] = useState(editing?.creditos ?? TIPO_CFG["artigo-publicado"].creditosPadrao);
  const [semestre, setSemestre] = useState(editing?.semestre ?? "2026/1");
  const [observacao, setObservacao] = useState(editing?.observacao ?? "");
  const [coautores, setCoautores] = useState(editing?.coautores.join(", ") ?? "");
  const [doi, setDoi] = useState(editing?.doi ?? "");
  const [hasFile, setHasFile] = useState(!!editing?.comprovante);
  const [fileName, setFileName] = useState(editing?.comprovante ?? "");

  const needsRelevance = tipo === "artigo-publicado" || tipo === "artigo-submetido";

  const handleTipoChange = (t: ActivityType) => {
    setTipo(t);
    setCreditos(TIPO_CFG[t].creditosPadrao);
    if (t !== "artigo-publicado" && t !== "artigo-submetido") setRelevancia("N/A");
    else setRelevancia("A1");
  };

  const handleSubmit = () => {
    if (!titulo.trim()) return;
    onSave({
      tipo, titulo, veiculo, nivelRelevancia: relevancia, observacao,
      comprovante: hasFile ? (fileName || "comprovante.pdf") : null,
      creditos, semestre, status: hasFile ? "enviado" : "rascunho",
      dataSubmissao: new Date().toLocaleDateString("pt-BR"),
      coautores: coautores.split(",").map(s => s.trim()).filter(Boolean),
      doi: doi || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-4" style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(2px)" }} onClick={onClose}>
      <div className="w-full md:max-w-2xl rounded-t-2xl md:rounded-2xl flex flex-col" style={{ background: "var(--card)", boxShadow: "0 -8px 40px rgba(0,0,0,0.2)", maxHeight: "92vh" }} onClick={e => e.stopPropagation()}>
        <div className="md:hidden flex justify-center pt-3 pb-1"><div style={{ width: 36, height: 4, borderRadius: 2, background: "var(--border)" }} /></div>
        <div className="flex items-center justify-between p-4 md:p-6 pb-4" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-3">
            <div className="rounded-xl p-2" style={{ background: "#eef3fc" }}><Plus size={16} style={{ color: "#123C7A" }} /></div>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--foreground)" }}>{editing ? "Editar Atividade" : "Registrar Atividade"}</h2>
          </div>
          <button onClick={onClose} className="rounded-xl p-2" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }}><X size={16} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Tipo */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 8 }}>TIPO DE ATIVIDADE *</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {(Object.keys(TIPO_CFG) as ActivityType[]).map(t => {
                const cfg = TIPO_CFG[t];
                return (
                  <button key={t} onClick={() => handleTipoChange(t)}
                    className="flex flex-col items-center gap-1.5 rounded-xl p-3 transition-all"
                    style={{ background: tipo === t ? cfg.bg : "var(--muted)", border: `2px solid ${tipo === t ? cfg.border : "transparent"}`, color: tipo === t ? cfg.color : "var(--muted-foreground)" }}>
                    <span style={{ color: tipo === t ? cfg.color : "var(--muted-foreground)" }}>{cfg.icon}</span>
                    <span style={{ fontSize: 10, fontWeight: 700, textAlign: "center", lineHeight: 1.3 }}>{cfg.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Título */}
          <FInput label="TÍTULO / DESCRIÇÃO *" value={titulo} onChange={setTitulo} placeholder="Título do artigo, nome da disciplina, tipo de banca..." />

          {/* Veículo */}
          <FInput label="VEÍCULO / INSTITUIÇÃO" value={veiculo} onChange={setVeiculo} placeholder="Nome do periódico, conferência, departamento..." />

          <div className="grid grid-cols-2 gap-4">
            {/* Relevância */}
            {needsRelevance && (
              <div>
                <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>NÍVEL DE RELEVÂNCIA</label>
                <div className="flex flex-wrap gap-1.5">
                  {RELEVANCE_OPTIONS.map(r => {
                    const cfg = RELEVANCE_CFG[r];
                    return (
                      <button key={r} onClick={() => setRelevancia(r)}
                        className="rounded-lg px-2.5 py-1 transition-all"
                        style={{ background: relevancia === r ? cfg.bg : "var(--muted)", color: relevancia === r ? cfg.color : "var(--muted-foreground)", border: `1px solid ${relevancia === r ? cfg.color + "60" : "var(--border)"}`, fontSize: 11, fontWeight: 700 }}>
                        {r}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {/* Créditos & Semestre */}
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <FInput label="CRÉDITOS" value={String(creditos)} onChange={v => setCreditos(Number(v))} type="number" placeholder="0" />
                <FInput label="SEMESTRE" value={semestre} onChange={setSemestre} placeholder="2026/1" />
              </div>
            </div>
          </div>

          {/* DOI / Coautores */}
          <div className="grid grid-cols-2 gap-4">
            <FInput label="DOI / NÚMERO DE REGISTRO" value={doi} onChange={setDoi} placeholder="10.xxxx/..." />
            <FInput label="COAUTORES (SEPARADOS POR VÍRGULA)" value={coautores} onChange={setCoautores} placeholder="Nome 1, Nome 2..." />
          </div>

          {/* Observação */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>OBSERVAÇÃO</label>
            <textarea value={observacao} onChange={e => setObservacao(e.target.value)} rows={3} placeholder="Informações adicionais relevantes para validação..."
              className="w-full rounded-xl px-3 py-2.5 outline-none resize-none"
              style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: 12, color: "var(--foreground)" }} />
          </div>

          {/* Comprovante */}
          <div>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>COMPROVANTE</label>
            {hasFile ? (
              <div className="flex items-center gap-3 rounded-xl px-4 py-3" style={{ background: "#dcfce7", border: "1px solid #86efac" }}>
                <Paperclip size={16} style={{ color: "#1F8A70" }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: "#1F8A70", flex: 1 }}>{fileName || "comprovante.pdf"}</span>
                <button onClick={() => setHasFile(false)} style={{ color: "#dc2626" }}><X size={14} /></button>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center rounded-xl p-6 border-2 border-dashed cursor-pointer transition-all" style={{ borderColor: "var(--border)", background: "var(--muted)" }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = "#123C7A")}
                onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}>
                <Upload size={24} style={{ color: "var(--muted-foreground)", marginBottom: 8 }} />
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)" }}>Arraste ou clique para enviar</p>
                <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 4 }}>PDF, JPG ou PNG · Máx. 10MB</p>
                <input type="file" className="hidden" onChange={e => { if (e.target.files?.[0]) { setHasFile(true); setFileName(e.target.files[0].name); } }} />
              </label>
            )}
          </div>

          {!hasFile && (
            <div className="rounded-xl px-4 py-3 flex items-start gap-2" style={{ background: "#fef9c3", border: "1px solid #fde68a" }}>
              <AlertCircle size={14} style={{ color: "#D4A017", flexShrink: 0, marginTop: 1 }} />
              <p style={{ fontSize: 11, color: "#92400e" }}>Sem comprovante, a atividade será salva como <strong>Rascunho</strong> e não entrará na fila de validação.</p>
            </div>
          )}
        </div>

        <div className="flex gap-3 p-6 pt-0">
          <button onClick={onClose} className="px-5 rounded-xl py-2.5" style={{ background: "var(--muted)", color: "var(--foreground)", fontWeight: 700, fontSize: 13 }}>Cancelar</button>
          <button onClick={handleSubmit} disabled={!titulo.trim()} className="flex-1 flex items-center justify-center gap-2 rounded-xl py-2.5" style={{ background: titulo.trim() ? "#123C7A" : "#e5e7eb", color: titulo.trim() ? "#fff" : "#9ca3af", fontWeight: 700, fontSize: 13 }}>
            <Check size={14} /> {editing ? "Salvar Alterações" : hasFile ? "Registrar e Enviar" : "Salvar Rascunho"}
          </button>
        </div>
      </div>
    </div>
  );
}

function FInput({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string }) {
  return (
    <div>
      <label style={{ fontSize: 11, fontWeight: 700, color: "var(--muted-foreground)", display: "block", marginBottom: 6 }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full rounded-xl px-3 py-2.5 outline-none"
        style={{ border: "1px solid var(--border)", background: "var(--muted)", fontSize: 12, color: "var(--foreground)" }}
        onFocus={e => (e.currentTarget.style.borderColor = "#123C7A")}
        onBlur={e => (e.currentTarget.style.borderColor = "var(--border)")} />
    </div>
  );
}

// ─── Activity Row ─────────────────────────────────────────────────────────────

function ActivityRow({ activity, onDetail, onEdit }: { activity: Activity; onDetail: () => void; onEdit: () => void }) {
  const tipo = TIPO_CFG[activity.tipo];
  const currentStep = activity.steps.find(s => s.status === "em-andamento" || (s.status === "pendente" && activity.steps.some(p => p.status !== "pendente")));

  return (
    <tr className="transition-colors" style={{ borderBottom: "1px solid var(--border)" }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--muted)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
      <td className="px-4 py-3" style={{ minWidth: 140 }}>
        <TipoBadge tipo={activity.tipo} />
      </td>
      <td className="px-4 py-3" style={{ minWidth: 260 }}>
        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--foreground)", lineHeight: 1.4, maxWidth: 320 }} className="line-clamp-2">{activity.titulo}</p>
        {activity.veiculo && <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 2, maxWidth: 300 }} className="truncate">{activity.veiculo}</p>}
      </td>
      <td className="px-4 py-3">
        {activity.nivelRelevancia !== "N/A" ? <RelevanceBadge level={activity.nivelRelevancia} /> : <span style={{ fontSize: 11, color: "var(--muted-foreground)" }}>—</span>}
      </td>
      <td className="px-4 py-3 text-center">
        <span style={{ fontSize: 14, fontWeight: 800, color: "#123C7A" }}>{activity.creditos}</span>
        <span style={{ fontSize: 10, color: "var(--muted-foreground)", marginLeft: 2 }}>cr</span>
      </td>
      <td className="px-4 py-3">
        <span style={{ fontSize: 12, color: "var(--muted-foreground)", whiteSpace: "nowrap" }}>{activity.semestre}</span>
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={activity.status} />
      </td>
      <td className="px-4 py-3 text-center">
        {activity.comprovante
          ? <CheckCircle2 size={16} style={{ color: "#1F8A70" }} title={activity.comprovante} />
          : <Upload size={14} style={{ color: "var(--muted-foreground)" }} title="Sem comprovante" />}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <button onClick={onDetail} className="rounded-lg p-1.5 transition-all" style={{ background: "#eef3fc", color: "#123C7A" }} title="Ver detalhes"><Eye size={13} /></button>
          <button onClick={onEdit} className="rounded-lg p-1.5 transition-all" style={{ background: "var(--muted)", color: "var(--muted-foreground)" }} title="Editar"><Clipboard size={13} /></button>
        </div>
      </td>
    </tr>
  );
}

// ─── Validation Queue Card ────────────────────────────────────────────────────

function ValidationCard({ activity, onDetail, onValidate, canValidate }: {
  activity: Activity; onDetail: () => void; onValidate: () => void; canValidate: boolean;
}) {
  const tipo = TIPO_CFG[activity.tipo];
  const activeStep = activity.steps.find(s => s.status === "em-andamento");
  const completedSteps = activity.steps.filter(s => s.status === "concluido").length;
  const progress = (completedSteps / activity.steps.length) * 100;

  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
      <div className="flex items-start gap-3 mb-4">
        <div className="rounded-xl p-2.5 flex-shrink-0" style={{ background: tipo.bg }}>
          <span style={{ color: tipo.color }}>{tipo.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <TipoBadge tipo={activity.tipo} />
            <StatusBadge status={activity.status} />
          </div>
          <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", lineHeight: 1.4 }}>{activity.titulo}</p>
          <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 2 }} className="truncate">{activity.veiculo}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p style={{ fontSize: 18, fontWeight: 800, color: "#123C7A" }}>{activity.creditos}</p>
          <p style={{ fontSize: 10, color: "var(--muted-foreground)" }}>créditos</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1.5">
          <p style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)" }}>PROGRESSO DA VALIDAÇÃO</p>
          <p style={{ fontSize: 10, fontWeight: 700, color: "#123C7A" }}>{completedSteps}/{activity.steps.length} etapas</p>
        </div>
        <PBar value={progress} color="#123C7A" h={5} />
      </div>

      {/* Steps mini */}
      <div className="flex gap-1.5 mb-4">
        {activity.steps.map(step => (
          <div key={step.stage} title={step.label}
            className="flex-1 rounded-md flex items-center justify-center"
            style={{ height: 24, background: stepBg(step.status), border: `1px solid ${stepColor(step.status)}40` }}>
            <span style={{ color: stepColor(step.status) }}><StepIcon status={step.status} /></span>
          </div>
        ))}
      </div>

      {activeStep && (
        <div className="rounded-xl px-3 py-2 mb-3" style={{ background: "#fef9c3", border: "1px solid #fde68a" }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: "#92400e" }}>AGUARDANDO</p>
          <p style={{ fontSize: 12, color: "#92400e" }}>{activeStep.label} — {activeStep.responsavel}</p>
        </div>
      )}

      <div className="flex gap-2">
        <button onClick={onDetail} className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2" style={{ background: "var(--muted)", color: "var(--foreground)", fontSize: 12, fontWeight: 700, border: "1px solid var(--border)" }}>
          <Eye size={12} /> Detalhes
        </button>
        {canValidate && (
          <button onClick={onValidate} className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2" style={{ background: "#123C7A", color: "#fff", fontSize: 12, fontWeight: 700 }}>
            <Shield size={12} /> Validar
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS: { id: TabKey; label: string; icon: React.ReactNode }[] = [
  { id: "registro",   label: "Registro de Atividades", icon: <Layers size={14} /> },
  { id: "validacao",  label: "Fila de Validação",      icon: <Clock size={14} /> },
  { id: "aprovadas",  label: "Aprovadas",              icon: <CheckCircle2 size={14} /> },
  { id: "rejeitadas", label: "Rejeitadas",             icon: <XCircle size={14} /> },
];

export function ActivitiesPage() {
  const { currentUser } = useApp();
  const [activities, setActivities] = useState<Activity[]>(INITIAL_ACTIVITIES);
  const [tab, setTab] = useState<TabKey>("registro");
  const [modal, setModal] = useState<ModalState>(null);
  const [search, setSearch] = useState("");
  const [filterTipo, setFilterTipo] = useState<ActivityType | "todos">("todos");
  const [expandedStats, setExpandedStats] = useState(false);

  const isCoord = currentUser?.role === "coordenacao";
  const isOrientador = currentUser?.role === "orientador";
  const canValidate = isCoord || isOrientador;

  // Credit summary
  const approved = useMemo(() => activities.filter(a => a.status === "aprovado"), [activities]);
  const totalCredits = useMemo(() => approved.reduce((s, a) => s + a.creditos, 0), [approved]);
  const creditsByType = useMemo(() => {
    const map: Partial<Record<ActivityType, number>> = {};
    approved.forEach(a => { map[a.tipo] = (map[a.tipo] ?? 0) + a.creditos; });
    return map;
  }, [approved]);

  // Tab counts
  const tabCounts = useMemo(() => ({
    registro:   activities.length,
    validacao:  activities.filter(a => a.status === "em-validacao" || a.status === "enviado").length,
    aprovadas:  activities.filter(a => a.status === "aprovado").length,
    rejeitadas: activities.filter(a => a.status === "rejeitado").length,
  }), [activities]);

  // Filtered list
  const filtered = useMemo(() => {
    let list = activities;
    if (tab === "validacao")  list = list.filter(a => a.status === "em-validacao" || a.status === "enviado");
    if (tab === "aprovadas")  list = list.filter(a => a.status === "aprovado");
    if (tab === "rejeitadas") list = list.filter(a => a.status === "rejeitado");
    if (filterTipo !== "todos") list = list.filter(a => a.tipo === filterTipo);
    if (search) list = list.filter(a => a.titulo.toLowerCase().includes(search.toLowerCase()) || a.veiculo.toLowerCase().includes(search.toLowerCase()));
    return list;
  }, [activities, tab, filterTipo, search]);

  // Actions
  function saveActivity(data: Omit<Activity, "id" | "steps">) {
    const newSteps: ValidationStep[] = [
      { stage: "envio",       label: "Envio pelo Aluno",       responsavel: currentUser?.name ?? "Aluno", status: data.status === "rascunho" ? "pendente" : "concluido", data: data.dataSubmissao },
      { stage: "orientador",  label: "Análise do Orientador",  responsavel: "Profa. Dra. Carla Mendes",  status: "pendente" },
      { stage: "coordenacao", label: "Análise da Coordenação", responsavel: "Prof. Dr. Roberto Almeida", status: "pendente" },
      { stage: "conclusao",   label: "Conclusão",              responsavel: "Sistema",                   status: "pendente" },
    ];
    if (modal?.kind === "register" && modal.editing) {
      setActivities(prev => prev.map(a => a.id === modal.editing!.id ? { ...a, ...data } : a));
    } else {
      const newActivity: Activity = { id: `a${Date.now()}`, ...data, steps: data.status === "enviado" ? [{ ...newSteps[0], status: "concluido" }, { ...newSteps[1], status: "em-andamento" }, newSteps[2], newSteps[3]] : newSteps };
      setActivities(prev => [newActivity, ...prev]);
    }
    if (data.status === "enviado") showToast("Atividade enviada para validação!");
    setModal(null);
  }

  function handleApprove(activityId: string, comment: string) {
    setActivities(prev => prev.map(a => {
      if (a.id !== activityId) return a;
      const steps = a.steps.map((s, i) => {
        if (s.status === "em-andamento") return { ...s, status: "concluido" as StepStatus, data: new Date().toLocaleDateString("pt-BR"), comentario: comment || undefined };
        if (s.status === "pendente" && a.steps[i - 1]?.status === "em-andamento") return { ...s, status: "em-andamento" as StepStatus };
        return s;
      });
      const allDone = steps.slice(0, 3).every(s => s.status === "concluido");
      return { ...a, steps: allDone ? steps.map((s, i) => i === 3 ? { ...s, status: "concluido" as StepStatus, data: new Date().toLocaleDateString("pt-BR") } : s) : steps, status: allDone ? "aprovado" : "em-validacao", dataAprovacao: allDone ? new Date().toLocaleDateString("pt-BR") : undefined };
    }));
    showToast("Atividade aprovada com sucesso!");
    setModal(null);
  }

  function handleReject(activityId: string, reason: string) {
    setActivities(prev => prev.map(a => {
      if (a.id !== activityId) return a;
      const steps = a.steps.map(s => s.status === "em-andamento" ? { ...s, status: "rejeitado" as StepStatus, data: new Date().toLocaleDateString("pt-BR"), comentario: reason } : s === a.steps[3] ? { ...s, status: "rejeitado" as StepStatus } : s);
      return { ...a, steps, status: "rejeitado", motivoRejeicao: reason };
    }));
    showToast("Atividade rejeitada.", "#dc2626");
    setModal(null);
  }

  function showToast(msg: string, bg = "#1F8A70") {
    const el = document.createElement("div");
    el.textContent = msg;
    Object.assign(el.style, { position: "fixed", bottom: "24px", right: "24px", zIndex: "9999", background: bg, color: "#fff", padding: "12px 20px", borderRadius: "12px", fontSize: "13px", fontWeight: "700", boxShadow: "0 8px 24px rgba(0,0,0,0.2)", transition: "opacity 0.3s", opacity: "1" });
    document.body.appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; }, 2000);
    setTimeout(() => { document.body.removeChild(el); }, 2300);
  }

  return (
    <div className="space-y-4 md:space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h1 style={{ color: "var(--foreground)", marginBottom: 4, fontSize: "clamp(16px, 4vw, 22px)" }}>Atividades Creditáveis</h1>
          <p className="hidden sm:block" style={{ color: "var(--muted-foreground)", fontSize: 14 }}>Registro, validação e controle de créditos acadêmicos</p>
        </div>
        <button onClick={() => setModal({ kind: "register" })} className="flex items-center gap-2 rounded-xl px-3 py-2.5 flex-shrink-0 md:px-4" style={{ background: "#123C7A", color: "#fff", fontWeight: 700, fontSize: 13 }}>
          <Plus size={15} /> <span className="hidden sm:inline">Registrar </span>Atividade
        </button>
      </div>

      {/* Credit Banner */}
      <div className="rounded-2xl overflow-hidden" style={{ background: "linear-gradient(135deg, #123C7A 0%, #0f2f5e 100%)" }}>
        <div className="p-4 md:p-6">
          <div className="flex items-start justify-between gap-6 mb-5">
            <div>
              <p style={{ color: "rgba(255,255,255,0.65)", fontSize: 12, marginBottom: 4 }}>Total de Créditos Aprovados</p>
              <div className="flex items-end gap-2">
                <span style={{ color: "#fff", fontSize: 42, fontWeight: 900, lineHeight: 1 }}>{totalCredits}</span>
                <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 22, marginBottom: 4 }}>/ {CREDITS_META}</span>
              </div>
            </div>
            <div className="text-right">
              <p style={{ color: "rgba(255,255,255,0.65)", fontSize: 12, marginBottom: 4 }}>Progresso Geral</p>
              <p style={{ color: "#D4A017", fontSize: 36, fontWeight: 900, lineHeight: 1 }}>{Math.round((totalCredits / CREDITS_META) * 100)}%</p>
            </div>
          </div>
          <div className="mb-5">
            <PBar value={(totalCredits / CREDITS_META) * 100} color="#D4A017" h={8} />
            <div className="flex justify-between mt-1.5">
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>0</span>
              <span style={{ fontSize: 10, color: "rgba(255,255,255,0.5)" }}>{CREDITS_META} créditos necessários</span>
            </div>
          </div>

          {/* By type — scroll on mobile */}
          <div className="flex gap-2 overflow-x-auto pb-1 sm:grid sm:grid-cols-7" style={{ scrollbarWidth: "none" }}>
            {(Object.keys(TIPO_CFG) as ActivityType[]).map(t => {
              const cfg = TIPO_CFG[t];
              const cr = creditsByType[t] ?? 0;
              return (
                <div key={t} className="rounded-xl p-2.5 text-center flex-shrink-0 sm:flex-shrink" style={{ background: "rgba(255,255,255,0.08)", minWidth: 72 }}>
                  <div className="flex justify-center mb-1" style={{ color: "rgba(255,255,255,0.7)" }}>{cfg.icon}</div>
                  <p style={{ color: "#fff", fontSize: 16, fontWeight: 800, lineHeight: 1 }}>{cr}</p>
                  <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 9, marginTop: 2, lineHeight: 1.3 }}>{cfg.label.split(" ").slice(0, 2).join(" ")}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Stats toggle */}
        <button onClick={() => setExpandedStats(!expandedStats)} className="w-full flex items-center justify-center gap-2 py-2.5 transition-all" style={{ background: "rgba(0,0,0,0.2)", color: "rgba(255,255,255,0.7)", fontSize: 11, fontWeight: 700 }}>
          <BarChart2 size={12} />
          {expandedStats ? "Ocultar estatísticas" : "Ver estatísticas detalhadas"}
          {expandedStats ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {expandedStats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-0" style={{ borderTop: "1px solid rgba(255,255,255,0.1)" }}>
            {[
              { label: "Em Validação",  value: tabCounts.validacao,  color: "#D4A017" },
              { label: "Aprovadas",     value: tabCounts.aprovadas,   color: "#1F8A70" },
              { label: "Rejeitadas",    value: tabCounts.rejeitadas,  color: "#dc2626" },
              { label: "Total Reg.",    value: tabCounts.registro,    color: "rgba(255,255,255,0.7)" },
            ].map(s => (
              <div key={s.label} className="p-4 text-center" style={{ borderRight: "1px solid rgba(255,255,255,0.08)" }}>
                <p style={{ fontSize: 22, fontWeight: 900, color: s.color }}>{s.value}</p>
                <p style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", marginTop: 2 }}>{s.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs — horizontal scroll on mobile */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className="flex items-center gap-2 px-3 md:px-4 py-2.5 rounded-xl transition-all flex-shrink-0"
            style={{ background: tab === t.id ? "#123C7A" : "var(--card)", color: tab === t.id ? "#fff" : "var(--muted-foreground)", border: `1px solid ${tab === t.id ? "#123C7A" : "var(--border)"}`, fontSize: 12, fontWeight: 700, minHeight: "44px" }}>
            {t.icon}
            <span className="hidden sm:inline">{t.label}</span>
            <span className="sm:hidden">{t.label.split(" ")[0]}</span>
            <span className="rounded-full px-1.5 py-0.5" style={{ background: tab === t.id ? "rgba(255,255,255,0.2)" : "var(--muted)", color: tab === t.id ? "#fff" : "var(--muted-foreground)", fontSize: 10, fontWeight: 800 }}>
              {tabCounts[t.id]}
            </span>
          </button>
        ))}
      </div>

      {/* Search + Filter */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex items-center gap-2 rounded-xl px-3 py-2.5 flex-1" style={{ background: "var(--card)", border: "1px solid var(--border)", minWidth: 200 }}>
          <Search size={13} style={{ color: "var(--muted-foreground)", flexShrink: 0 }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar por título ou veículo..."
            style={{ background: "transparent", border: "none", fontSize: 12, color: "var(--foreground)", outline: "none", flex: 1 }} />
          {search && <button onClick={() => setSearch("")} style={{ color: "var(--muted-foreground)" }}><X size={12} /></button>}
        </div>
        <div className="flex items-center gap-2 rounded-xl px-3 py-2.5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <Filter size={13} style={{ color: "var(--muted-foreground)" }} />
          <select value={filterTipo} onChange={e => setFilterTipo(e.target.value as typeof filterTipo)}
            style={{ background: "transparent", border: "none", fontSize: 12, color: "var(--foreground)", outline: "none" }}>
            <option value="todos">Todos os tipos</option>
            {(Object.keys(TIPO_CFG) as ActivityType[]).map(t => <option key={t} value={t}>{TIPO_CFG[t].label}</option>)}
          </select>
        </div>
        <span style={{ fontSize: 11, color: "var(--muted-foreground)", display: "flex", alignItems: "center" }}>{filtered.length} atividade{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Validation Queue — card grid */}
      {tab === "validacao" && (
        <div>
          {filtered.length === 0 ? (
            <EmptyState icon={<Clock size={32} />} title="Nenhuma atividade em validação" desc="Todas as atividades foram processadas." />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {filtered.map(a => (
                <ValidationCard key={a.id} activity={a}
                  onDetail={() => setModal({ kind: "detail", activity: a })}
                  onValidate={() => setModal({ kind: "validate", activity: a })}
                  canValidate={canValidate} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Table / Cards for other tabs */}
      {tab !== "validacao" && (
        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          {filtered.length === 0 ? (
            <EmptyState
              icon={tab === "aprovadas" ? <CheckCircle2 size={32} /> : tab === "rejeitadas" ? <XCircle size={32} /> : <Layers size={32} />}
              title={tab === "aprovadas" ? "Nenhuma atividade aprovada" : tab === "rejeitadas" ? "Nenhuma atividade rejeitada" : "Nenhuma atividade encontrada"}
              desc={search ? "Tente outros termos de busca." : "Registre sua primeira atividade clicando em '+ Registrar Atividade'."}
            />
          ) : (
            <>
              {/* Mobile: card list */}
              <div className="md:hidden">
                {filtered.map(a => {
                  const tipo = TIPO_CFG[a.tipo];
                  const sc = STATUS_CFG[a.status];
                  return (
                    <button key={a.id} onClick={() => setModal({ kind: "detail", activity: a })}
                      className="w-full text-left flex items-start gap-3 p-4 transition-all"
                      style={{ background: "transparent", minHeight: "64px", borderBottom: "1px solid var(--border)" }}>
                      <div className="rounded-xl p-2 flex-shrink-0" style={{ background: tipo.bg }}>
                        <span style={{ color: tipo.color }}>{tipo.icon}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--foreground)", lineHeight: 1.3 }} className="line-clamp-2">{a.titulo}</p>
                        {a.veiculo && <p style={{ fontSize: 11, color: "var(--muted-foreground)", marginTop: 2 }} className="truncate">{a.veiculo}</p>}
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                          <span className="rounded-full px-2 py-0.5" style={{ fontSize: 10, fontWeight: 700, color: sc.color, background: sc.bg }}>{sc.label}</span>
                          <span style={{ fontSize: 11, color: "var(--muted-foreground)" }}>{a.semestre}</span>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p style={{ fontSize: 16, fontWeight: 800, color: "#123C7A" }}>{a.creditos}</p>
                        <p style={{ fontSize: 9, color: "var(--muted-foreground)" }}>créditos</p>
                        {a.nivelRelevancia !== "N/A" && (
                          <span className="inline-block rounded px-1.5 mt-1" style={{ fontSize: 10, fontWeight: 800, color: RELEVANCE_CFG[a.nivelRelevancia].color, background: RELEVANCE_CFG[a.nivelRelevancia].bg }}>{a.nivelRelevancia}</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Desktop: table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full" style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "var(--muted)", borderBottom: "1px solid var(--border)" }}>
                      {["Tipo", "Título / Veículo", "Relevância", "Créd.", "Semestre", "Status", "Comprov.", ""].map(h => (
                        <th key={h} className="px-4 py-3 text-left" style={{ fontSize: 10, fontWeight: 700, color: "var(--muted-foreground)", letterSpacing: 0.5, whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map(a => (
                      <ActivityRow key={a.id} activity={a}
                        onDetail={() => setModal({ kind: "detail", activity: a })}
                        onEdit={() => setModal({ kind: "register", editing: a })} />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Rejected — extra motivo section */}
      {tab === "rejeitadas" && filtered.length > 0 && (
        <div className="rounded-2xl p-5 mt-2" style={{ background: "var(--card)", border: "1px solid var(--tint-danger-border)", boxShadow: "var(--elevation-card-shadow)" }}>
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle size={16} style={{ color: "var(--tint-danger-text)" }} />
            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--tint-danger-text)" }}>Ações Necessárias</p>
          </div>
          <div className="space-y-3">
            {filtered.map(a => a.motivoRejeicao ? (
              <div key={a.id} className="rounded-xl p-3.5" style={{ background: "var(--tint-danger-bg)", border: "1px solid var(--tint-danger-border)" }}>
                <div className="flex items-start gap-3">
                  <XCircle size={15} style={{ color: "var(--tint-danger-text)", flexShrink: 0, marginTop: 1 }} />
                  <div className="flex-1 min-w-0">
                    <p style={{ fontSize: 12, fontWeight: 700, color: "var(--foreground)" }}>{a.titulo}</p>
                    <p style={{ fontSize: 11, color: "var(--tint-danger-text)", marginTop: 4, lineHeight: 1.5 }}>{a.motivoRejeicao}</p>
                    <button onClick={() => setModal({ kind: "register", editing: a })} className="flex items-center gap-1.5 mt-2 rounded-lg px-3 py-1.5" style={{ background: "var(--destructive)", color: "var(--destructive-foreground)", fontSize: 11, fontWeight: 700 }}>
                      <Clipboard size={11} /> Corrigir e Reenviar
                    </button>
                  </div>
                </div>
              </div>
            ) : null)}
          </div>
        </div>
      )}

      {/* Modals */}
      {modal?.kind === "register" && (
        <RegisterModal editing={modal.editing} onClose={() => setModal(null)} onSave={saveActivity} />
      )}
      {modal?.kind === "detail" && (
        <DetailModal activity={modal.activity} onClose={() => setModal(null)}
          onValidate={() => setModal({ kind: "validate", activity: modal.activity })}
          canValidate={canValidate} />
      )}
      {modal?.kind === "validate" && (
        <ValidateModal activity={modal.activity} onClose={() => setModal(null)}
          onApprove={comment => handleApprove(modal.activity.id, comment)}
          onReject={reason => handleReject(modal.activity.id, reason)} />
      )}
    </div>
  );
}

function EmptyState({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <div className="mb-4" style={{ color: "var(--muted-foreground)", opacity: 0.5 }}>{icon}</div>
      <p style={{ fontSize: 14, fontWeight: 700, color: "var(--foreground)", marginBottom: 6 }}>{title}</p>
      <p style={{ fontSize: 12, color: "var(--muted-foreground)", maxWidth: 280 }}>{desc}</p>
    </div>
  );
}

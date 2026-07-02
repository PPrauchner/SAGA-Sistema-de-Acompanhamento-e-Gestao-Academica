/**
 * Hook React para a lista detalhada de orientandos de um orientador (dashboard).
 *
 * Responsabilidades:
 * - useOrientandos(advisorId): carrega os orientandos via GET /students (o backend já
 *   escopa por papel; o orientador recebe apenas os próprios) e, para cada aluno, funde
 *   GET /dashboard/aluno/{id} (créditos, produções, progresso, situação inferida) e
 *   GET /work-plan/{id} (etapas reais → fase atual e próximo marco).
 * - Filtra client-side por advisorId como rede de segurança para o caso da coordenação
 *   abrir o dashboard de um orientador via toggle de visão (quando /students devolve todos).
 * - Expõe um OrientandoView[] com a forma que os componentes do dashboard já consomem,
 *   além de loading/error. O token vem do useAuth() via AppContext.
 */

import { useEffect, useState } from "react";
import { useAuth } from "./useAuth";
import { getStudents, type Student } from "@/api/studentsApi";
import { getAlunoDashboard, type AlunoDashboardData } from "@/api/dashboardApi";
import { getWorkPlan, type WorkPlan } from "@/api/workPlanApi";

export type StudentStatus =
  | "regular"
  | "em-risco"
  | "qualificado"
  | "fase-defesa"
  | "prorrogacao"
  | "concluido"
  | "desligado";

export interface OrientandoView {
  id: string;
  name: string;
  init: string;
  nivel: "Mestrado" | "Doutorado";
  ingresso: string;
  prazo: string;
  prazoMeses: number;
  progress: number;
  creditos: number;
  creditosMax: number;
  producoes: number;
  producoesMin: number;
  status: StudentStatus;
  fase: string;
  ultimaAtual: string;
  proximo: string;
}

interface UseOrientandosResult {
  data: OrientandoView[] | null;
  loading: boolean;
  error: string | null;
}

// Mapeia a situação inferida do backend (enum de 7 valores) para o status visual do dashboard.
const SITUACAO_TO_STATUS: Record<string, StudentStatus> = {
  regular: "regular",
  em_risco: "em-risco",
  qualificado: "qualificado",
  em_fase_de_defesa: "fase-defesa",
  em_prorrogacao: "prorrogacao",
  concluido: "concluido",
  desligado: "desligado",
};

// Rótulos humanos das etapas do plano de trabalho (enum → exibição).
const STAGE_LABEL: Record<string, string> = {
  revisao_bibliografica: "Revisão Bibliográfica",
  definicao_problema: "Definição do Problema",
  desenvolvimento: "Desenvolvimento",
  experimentos: "Experimentos",
  escrita: "Escrita da Tese",
  qualificacao: "Qualificação",
  defesa: "Defesa",
};

const MESES_ABREV = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];

function initials(nome: string): string {
  const parts = nome.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

// Extrai ano/mês/dia de uma data ISO sem deslocar por fuso (date-only "AAAA-MM-DD" seria
// interpretado como UTC por new Date, mudando o dia em fusos negativos — ver formatDataBR).
function parseYMD(iso: string): { year: number; month: number; day: number } | null {
  const match = iso.slice(0, 10).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (match) {
    return { year: Number(match[1]), month: Number(match[2]) - 1, day: Number(match[3]) };
  }
  const date = new Date(iso);
  if (isNaN(date.getTime())) return null;
  return { year: date.getFullYear(), month: date.getMonth(), day: date.getDate() };
}

function formatMesAno(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ymd = parseYMD(iso);
  return ymd ? `${MESES_ABREV[ymd.month]}/${ymd.year}` : "—";
}

// Meses inteiros entre agora e a data alvo; negativo quando o prazo já venceu.
function monthsUntil(iso: string | null | undefined): number {
  if (!iso) return 0;
  const target = parseYMD(iso);
  if (!target) return 0;
  const now = new Date();
  let months =
    (target.year - now.getFullYear()) * 12 + (target.month - now.getMonth());
  if (target.day < now.getDate()) months -= 1;
  return months;
}

function yearOf(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ymd = parseYMD(iso);
  return ymd ? String(ymd.year) : "—";
}

// Fase atual = primeira etapa (por ordem) não concluída; próximo marco = 1ª task pendente.
function deriveFaseProximo(plan: WorkPlan | null): { fase: string; proximo: string } {
  if (!plan || plan.stages.length === 0) return { fase: "—", proximo: "—" };
  const stages = [...plan.stages].sort((a, b) => a.ordem - b.ordem);
  const current =
    stages.find((s) => s.status !== "concluido") ?? stages[stages.length - 1];
  const fase = STAGE_LABEL[current.nome] ?? current.nome;

  let proximo = current.tasks.find((t) => t.status !== "concluido")?.titulo ?? "—";
  if (proximo === "—") {
    for (const stage of stages) {
      const pending = stage.tasks.find((t) => t.status !== "concluido");
      if (pending) {
        proximo = pending.titulo;
        break;
      }
    }
  }
  return { fase, proximo };
}

// Tempo relativo da atualização de progresso mais recente entre todas as tasks do plano.
function deriveUltimaAtual(plan: WorkPlan | null): string {
  if (!plan) return "—";
  let latest = 0;
  for (const stage of plan.stages) {
    for (const task of stage.tasks) {
      const criado = task.ultima_atualizacao?.criado_em;
      if (!criado) continue;
      const ts = new Date(criado).getTime();
      if (!isNaN(ts) && ts > latest) latest = ts;
    }
  }
  if (latest === 0) return "—";
  const days = Math.floor((Date.now() - latest) / 86_400_000);
  if (days <= 0) return "hoje";
  if (days === 1) return "ontem";
  if (days < 7) return `há ${days} dias`;
  const weeks = Math.floor(days / 7);
  return weeks === 1 ? "há 1 semana" : `há ${weeks} semanas`;
}

function buildView(
  student: Student,
  dash: AlunoDashboardData | null,
  plan: WorkPlan | null,
): OrientandoView {
  const situacao = dash?.situacao_inferida ?? student.situacao_inferida;
  const { fase, proximo } = deriveFaseProximo(plan);
  return {
    id: student.id,
    name: student.nome,
    init: initials(student.nome),
    nivel: student.nivel === "doutorado" ? "Doutorado" : "Mestrado",
    ingresso: yearOf(student.data_ingresso),
    prazo: formatMesAno(student.prazo_final),
    prazoMeses: monthsUntil(student.prazo_final),
    progress: Math.round(
      plan?.progresso_percentual ?? dash?.progresso_plano_percentual ?? 0,
    ),
    creditos: dash?.creditos.total ?? 0,
    creditosMax: dash?.creditos.minimo_requerido ?? 0,
    producoes: dash?.producoes_aprovadas ?? 0,
    // Mínimo de produções não é exposto por aluno na API — heurística por nível (defesa RL01).
    producoesMin: student.nivel === "doutorado" ? 3 : 1,
    status: SITUACAO_TO_STATUS[situacao] ?? "regular",
    fase,
    ultimaAtual: deriveUltimaAtual(plan),
    proximo,
  };
}

export function useOrientandos(advisorId: string | undefined): UseOrientandosResult {
  const { token } = useAuth();
  const [data, setData] = useState<OrientandoView[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);

    getStudents(token)
      .then(async (students) => {
        const orientandos = advisorId
          ? students.filter((s) => s.orientador_id === advisorId)
          : students;
        const views = await Promise.all(
          orientandos.map(async (student) => {
            const [dash, plan] = await Promise.all([
              getAlunoDashboard(student.id, token).catch(() => null),
              getWorkPlan(student.id, token).catch(() => null),
            ]);
            return buildView(student, dash, plan);
          }),
        );
        if (!cancelled) setData(views);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, advisorId]);

  return { data, loading, error };
}

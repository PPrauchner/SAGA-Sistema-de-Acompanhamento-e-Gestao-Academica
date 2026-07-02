/**
 * Camada de acesso à API REST para os relatórios gerenciais da coordenação.
 *
 * Responsabilidades:
 * - getStudentsAtRisk(): GET /api/v1/reports/students-at-risk — alunos em risco com as
 *   razões do risco. Alimenta o relatório de alunos em risco da ReportsPage.
 * - getStudentsByStatus(): GET /api/v1/reports/students-by-status.
 * - getStudentsByAdvisor(): GET /api/v1/reports/students-by-advisor.
 * - getCompletionTime(): GET /api/v1/reports/completion-time.
 * - getProductionsReport(): GET /api/v1/reports/productions.
 * - getProductionsByMonth(): GET /api/v1/reports/productions-by-month — série mensal de
 *   produções validadas para o gráfico de produção do dashboard da coordenação.
 * - Todas as funções incluem Authorization: Bearer <token> quando fornecido.
 * - Exclusivo da coordenação — useAuth().role deve ser verificado antes de chamar.
 *
 * As interfaces espelham os response models de backend/app/models/report.py.
 */

import { apiGet } from "@/api/http";

export type SituacaoRegistrada =
    | "regular"
    | "em_prorrogacao"
    | "em_risco"
    | "qualificado"
    | "em_fase_de_defesa"
    | "concluido"
    | "desligado";


export interface StudentAtRiskItem {
    student_id: string;
    nome: string;
    orientador_nome: string;
    situacao_inferida: string;
    dias_restantes_prazo: number | null;
    razoes_risco: string[];
}

export interface StudentsAtRiskResponse {
    total: number;
    items: StudentAtRiskItem[];
}


export interface StudentStatusSummary {
    student_id: string;
    nome: string;
    orientador_nome: string;
    nivel: string;
}

export interface StatusGroup {
    total: number;
    alunos: StudentStatusSummary[];
}

export interface StudentsByStatusResponse {
    por_situacao: Partial<Record<SituacaoRegistrada, StatusGroup>>;
}


export interface AdvisorGroupItem {
    advisor_id: string;
    advisor_nome: string;
    total_orientandos: number;
    em_risco: number;
    regulares: number;
}

export interface StudentsByAdvisorResponse {
    items: AdvisorGroupItem[];
}


export interface CompletionTimeItem {
    student_nome: string;
    meses: number;
    ano_conclusao: number;
}

export interface CompletionTimeResponse {
    media_meses: number | null;
    total_concluidos: number;
    minimo_meses: number | null;
    maximo_meses: number | null;
    historico: CompletionTimeItem[];
}



export interface ProductionLevelBreakdown {
    A1: number;
    A2: number;
    A3: number;
    A4: number;
    A5: number;
    A6: number;
    A7: number;
    A8: number;
    SC: number;
}

export interface ProductionByStudentItem {
    student_id: string;
    student_nome: string;
    total: number;
    pontuacao_total: number;
    por_nivel: ProductionLevelBreakdown;
}

export interface ProductionByAdvisorItem {
    advisor_id: string;
    advisor_nome: string;
    total: number;
    pontuacao_media_orientandos: number;
}

export interface ProductionsReportResponse {
    total_producoes_aprovadas: number;
    por_aluno: ProductionByStudentItem[];
    por_orientador: ProductionByAdvisorItem[];
}


export interface ProductionByMonthItem {
    mes: string;
    total: number;
}



export function getStudentsAtRisk(token?: string): Promise<StudentsAtRiskResponse> {
    return apiGet<StudentsAtRiskResponse>("/reports/students-at-risk", token);
}

export function getStudentsByStatus(token?: string): Promise<StudentsByStatusResponse> {
    return apiGet<StudentsByStatusResponse>("/reports/students-by-status", token);
}

export function getStudentsByAdvisor(token?: string): Promise<StudentsByAdvisorResponse> {
    return apiGet<StudentsByAdvisorResponse>("/reports/students-by-advisor", token);
}

export function getCompletionTime(token?: string): Promise<CompletionTimeResponse> {
    return apiGet<CompletionTimeResponse>("/reports/completion-time", token);
}

export function getProductionsReport(token?: string): Promise<ProductionsReportResponse> {
    return apiGet<ProductionsReportResponse>("/reports/productions", token);
}

export function getProductionsByMonth(
    token?: string,
    meses?: number,
): Promise<ProductionByMonthItem[]> {
    const query = meses !== undefined ? `?meses=${meses}` : "";
    return apiGet<ProductionByMonthItem[]>(`/reports/productions-by-month${query}`, token);
}

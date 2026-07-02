import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from "@/api/http";

export type StageStatus = "pendente" | "em_andamento" | "concluido" | "atrasado";
export type TaskStatus = "pendente" | "em_andamento" | "concluido" | "atrasado";
export type TaskPriority = "baixa" | "media" | "alta";

export interface ProgressUpdate {
  update_id: string;
  task_id: string;
  conteudo: string;
  percentual: number;
  autor_id: string;
  autor_nome: string;
  criado_em: string;
}

export interface WorkPlanTask {
  task_id: string;
  stage_id: string;
  titulo: string;
  descricao: string;
  prazo: string;
  status: TaskStatus;
  prioridade: TaskPriority;
  progresso_percentual: number;
  ultima_atualizacao: {
    conteudo: string;
    percentual: number;
    criado_em: string;
    autor_nome?: string;
  } | null;
}

export interface WorkPlanStage {
  stage_id: string;
  nome: string;
  ordem: number;
  data_inicio: string;
  data_fim: string;
  status: StageStatus;
  progresso_percentual: number;
  tasks: WorkPlanTask[];
}

export interface WorkPlan {
  plan_id: string;
  student_id: string;
  titulo: string;
  data_inicio: string;
  data_fim_prevista: string;
  descricao: string | null;
  progresso_percentual: number;
  status_geral: StageStatus;
  plano_concluido: boolean;
  fato_plano_concluido: string | null;
  stages: WorkPlanStage[];
}

export interface WorkPlanCreate {
  titulo: string;
  data_inicio: string;
  data_fim_prevista: string;
  descricao?: string;
}

export interface StageCreate {
  nome: string;
  ordem: number;
  data_inicio: string;
  data_fim: string;
}

export interface TaskCreate {
  titulo: string;
  descricao: string;
  prazo: string;
  prioridade: TaskPriority;
}

export interface ProgressUpdateCreate {
  conteudo: string;
  percentual: number;
}

export function getWorkPlan(studentId: string, token?: string): Promise<WorkPlan> {
  return apiGet<WorkPlan>(`/work-plan/${studentId}`, token);
}

export function createWorkPlan(studentId: string, data: WorkPlanCreate, token?: string): Promise<{ plan_id: string; message: string }> {
  return apiPost(`/work-plan/${studentId}`, data, token);
}

export function updateWorkPlan(planId: string, data: Partial<WorkPlanCreate>, token?: string): Promise<{ message: string; historico_criado: boolean }> {
  return apiPut(`/work-plan/${planId}`, data, token);
}

export function createStage(planId: string, data: StageCreate, token?: string): Promise<{ stage_id: string }> {
  return apiPost(`/work-plan/${planId}/stages`, data, token);
}

export function createTask(stageId: string, data: TaskCreate, token?: string): Promise<{ task_id: string }> {
  return apiPost(`/stages/${stageId}/tasks`, data, token);
}

export function updateTaskStatus(
  taskId: string,
  status: TaskStatus,
  token?: string,
): Promise<{ message: string; fato_motor_gerado: string | null; plano_concluido: boolean; fato_plano_concluido: string | null }> {
  return apiPatch(`/tasks/${taskId}/status`, { status }, token);
}

export function updateTask(taskId: string, data: Partial<TaskCreate> & { status?: TaskStatus }, token?: string): Promise<{ message: string }> {
  return apiPatch(`/tasks/${taskId}`, data, token);
}

export function deleteTask(taskId: string, token?: string): Promise<{ message: string }> {
  return apiDelete(`/tasks/${taskId}`, token);
}

export function addProgressUpdate(
  taskId: string,
  data: ProgressUpdateCreate,
  token?: string,
): Promise<{ update_id: string; alerta_prazo: boolean; notificacao_enviada_ao_orientador: boolean; progresso_percentual: number }> {
  return apiPost(`/tasks/${taskId}/updates`, data, token);
}

export function getTaskUpdates(taskId: string, token?: string): Promise<{ items: ProgressUpdate[] }> {
  return apiGet(`/tasks/${taskId}/updates`, token);
}

"""Modelos Pydantic para plano de trabalho, etapas, tarefas e progresso."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

StageStatus = Literal["pendente", "em_andamento", "concluido", "atrasado"]
TaskStatus = Literal["pendente", "em_andamento", "concluido", "atrasado"]
TaskPriority = Literal["baixa", "media", "alta"]

_LEGACY_STATUS = {"concluida": "concluido", "atrasada": "atrasado"}


def _normalize_status(value: str | None) -> str | None:
    return _LEGACY_STATUS.get(value, value)


class WorkPlanCreate(BaseModel):
    titulo: str = Field(..., min_length=1)
    data_inicio: datetime
    data_fim_prevista: datetime
    descricao: str | None = None


class WorkPlanUpdate(BaseModel):
    titulo: str | None = None
    data_fim_prevista: datetime | None = None
    descricao: str | None = None


class StageCreate(BaseModel):
    nome: str = Field(..., min_length=1)
    ordem: int = Field(..., ge=1)
    data_inicio: datetime
    data_fim: datetime


class StageUpdate(BaseModel):
    nome: str | None = None
    ordem: int | None = Field(default=None, ge=1)
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    status: StageStatus | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_stage_status(cls, value: str | None) -> str | None:
        return _normalize_status(value)


class TaskCreate(BaseModel):
    titulo: str = Field(..., min_length=1)
    descricao: str = ""
    prazo: datetime
    prioridade: TaskPriority = "media"


class TaskUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    prazo: datetime | None = None
    prioridade: TaskPriority | None = None
    status: TaskStatus | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_task_status(cls, value: str | None) -> str | None:
        return _normalize_status(value)


class TaskStatusPatch(BaseModel):
    status: TaskStatus

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_patch_status(cls, value: str | None) -> str | None:
        return _normalize_status(value)


class ProgressUpdateCreate(BaseModel):
    conteudo: str = Field(..., min_length=1)
    percentual: float = Field(..., ge=0, le=100)


class ProgressUpdateResponse(BaseModel):
    update_id: str
    task_id: str
    conteudo: str
    percentual: float
    autor_id: str
    autor_nome: str
    criado_em: datetime


class ProgressUpdateList(BaseModel):
    items: list[ProgressUpdateResponse]


class LatestProgressUpdate(BaseModel):
    conteudo: str
    percentual: float
    criado_em: datetime
    autor_nome: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    stage_id: str
    titulo: str
    descricao: str = ""
    prazo: datetime
    status: TaskStatus = "pendente"
    prioridade: TaskPriority = "media"
    progresso_percentual: float = 0
    ultima_atualizacao: LatestProgressUpdate | None = None


class StageResponse(BaseModel):
    stage_id: str
    nome: str
    ordem: int
    data_inicio: datetime
    data_fim: datetime
    status: StageStatus = "pendente"
    progresso_percentual: float = 0
    tasks: list[TaskResponse] = []


class WorkPlanFull(BaseModel):
    plan_id: str
    student_id: str
    titulo: str
    data_inicio: datetime
    data_fim_prevista: datetime
    descricao: str | None = None
    progresso_percentual: float = 0
    status_geral: StageStatus = "pendente"
    plano_concluido: bool = False
    fato_plano_concluido: str | None = None
    stages: list[StageResponse] = []


class MutationMessage(BaseModel):
    message: str


class CreatePlanResponse(MutationMessage):
    plan_id: str


class CreateStageResponse(BaseModel):
    stage_id: str


class CreateTaskResponse(BaseModel):
    task_id: str


class TaskStatusResponse(MutationMessage):
    fato_motor_gerado: str | None = None
    plano_concluido: bool = False
    fato_plano_concluido: str | None = None


class ProgressUpdateCreated(BaseModel):
    update_id: str
    alerta_prazo: bool
    notificacao_enviada_ao_orientador: bool
    progresso_percentual: float


class WorkPlanFact(BaseModel):
    student_id: str
    plano_concluido: bool
    fato: str | None = None


class ActorContext(BaseModel):
    uid: str = "system"
    nome: str = "Sistema"
    role: Literal["aluno", "orientador", "coordenacao", "system"] = "system"

    @field_validator("nome")
    @classmethod
    def _fallback_nome(cls, value: str) -> str:
        return value or "Sistema"

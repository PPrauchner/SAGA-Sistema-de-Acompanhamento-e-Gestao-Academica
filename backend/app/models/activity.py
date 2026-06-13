"""
Modelos Pydantic para atividades creditáveis e tipos de atividade.

Responsabilidades:
- ActivityCreate: corpo de POST /api/v1/activities.
- ActivityResponse: resposta com campos calculados pelo motor RL04.
- ActivityValidateRequest: corpo de PATCH /api/v1/activities/{id}/validate.
- ActivityTypeCreate/ActivityTypeUpdate/ActivityTypeResponse: CRUD de tipos de atividade.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ─── Activity Types ────────────────────────────────────────────────────────────

class ActivityTypeCreate(BaseModel):
    nome: str
    categoria: Literal["basico", "especifico", "tecnologico"]
    pontuacao_base: float = Field(gt=0)
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool = True
    permite_multiplas: bool = True


class ActivityTypeUpdate(BaseModel):
    nome: str | None = None
    pontuacao_base: float | None = Field(default=None, gt=0)
    limite_maximo_creditos: float | None = None
    exige_comprovante: bool | None = None
    permite_multiplas: bool | None = None


class ActivityTypeResponse(BaseModel):
    id: str
    nome: str
    categoria: str
    pontuacao_base: float
    limite_maximo_creditos: float | None
    exige_comprovante: bool
    permite_multiplas: bool
    ativo: bool


# ─── Activities ────────────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    tipo_id: str
    descricao: str
    data_realizacao: str = Field(..., description="Data ISO8601 (YYYY-MM-DD)")
    comprovante_url: str | None = None
    status: Literal["rascunho", "enviado"] = "enviado"


class ActivityValidateRequest(BaseModel):
    acao: Literal["parecer_orientador", "aprovar", "rejeitar"]
    observacao: str | None = None
    creditos_concedidos: float | None = None


class ActivityResponse(BaseModel):
    id: str
    student_id: str
    tipo_id: str
    tipo_nome: str | None = None
    categoria: str | None = None
    descricao: str
    data_realizacao: str
    comprovante_url: str | None
    creditos_gerados: float
    status: str
    parecer_orientador: str | None = None
    observacao_coordenacao: str | None = None
    elegivel: bool | None = None


class ActivitySubmitResponse(BaseModel):
    id: str
    elegibilidade_preliminar: bool
    notificacao_enviada: bool


class ActivityValidateResponse(BaseModel):
    message: str
    novo_status: str
    creditos_contabilizados: float | None
    motor_inferencia_executado: bool
    fato_gerado: str | None

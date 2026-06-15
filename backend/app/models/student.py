"""
Modelos Pydantic para a entidade Student (discente).

Responsabilidades:
- Definir StudentBase com campos: uid, matricula, nome, email, orientador_id,
  coorientador_id, programa_id, nivel, data_ingresso, prazo_final.
- Definir StudentCreate para POST /api/v1/students (campos obrigatórios de cadastro).
- Definir StudentUpdate para PUT /api/v1/students/{id} (campos opcionais editáveis).
- Definir StudentResponse para leitura, incluindo situacao_registrada, situacao_inferida,
  proficiencia_comprovada, qualificacao_aprovada e campos de data.
- Definir modelos de patch para qualificacao, proficiencia e situacao (PATCH endpoints).
- Mapear o documento Firestore da coleção students/ — entidade central do sistema.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

StudentLevel = Literal["mestrado", "doutorado"]

SituacaoRegistrada = Literal[
    "regular",
    "em_prorrogacao",
    "em_risco",
    "qualificado",
    "fase_defesa",
    "concluido",
    "desligado",
]


class StudentCreateRequest(BaseModel):
    nome: str
    email: str
    matricula: str

    orientador_id: str
    coorientador_id: str | None = None

    nivel: StudentLevel
    data_ingresso: datetime
    programa_id: str


class StudentUpdateRequest(BaseModel):
    nome: str | None = None
    orientador_id: str | None = None
    coorientador_id: str | None = None
    prazo_final: datetime | None = None


class QualificacaoRequest(BaseModel):
    aprovada: bool
    data_qualificacao: datetime


class ProficienciaRequest(BaseModel):
    comprovada: bool
    data_proficiencia: datetime | None = None


class SituacaoRequest(BaseModel):
    situacao_registrada: SituacaoRegistrada
    observacao: str | None = None


class StudentResponse(BaseModel):
    id: str

    nome: str
    email: str
    matricula: str

    orientador_id: str
    coorientador_id: str | None = None

    programa_id: str
    nivel: StudentLevel

    situacao_registrada: SituacaoRegistrada
    situacao_inferida: str

    data_ingresso: datetime
    prazo_final: datetime | None = None

    qualificacao_aprovada: bool = False
    proficiencia_comprovada: bool = False

    qualificacao_data: datetime | None = None
    proficiencia_data: datetime | None = None

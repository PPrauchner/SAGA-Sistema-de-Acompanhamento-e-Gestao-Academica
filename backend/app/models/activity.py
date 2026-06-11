"""
Modelos Pydantic para a entidade Activity (atividade creditável).

Responsabilidades:
- Definir ActivityCreate para POST /api/v1/activities com campos: tipo_id, descricao,
  data_realizacao, comprovante_url, status inicial.
- Definir ActivityResponse para leitura incluindo tipo_nome, categoria, creditos_gerados,
  status do fluxo de validação, parecer_orientador, observacao_coordenacao e campo
  elegivel calculado pelo motor RL04 quando status='aprovado'.
- Definir ValidateActivityRequest para PATCH /api/v1/activities/{id}/validate com campos:
  acao (parecer_orientador | aprovar | rejeitar), observacao e creditos_concedidos.
- Definir ValidateActivityResponse para retorno da operação de validação pela coordenação,
  incluindo novo_status, creditos_contabilizados, motor_inferencia_executado e fato_gerado.
- Mapear a sub-coleção Firestore students/{id}/activities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActivityStatus(str, Enum):
    pendente = "pendente"
    parecer_emitido = "parecer_emitido"
    aprovada = "aprovada"
    rejeitada = "rejeitada"


class ValidateAction(str, Enum):
    parecer_orientador = "parecer_orientador"
    aprovar = "aprovar"
    rejeitar = "rejeitar"


class ParecerOrientador(BaseModel):
    texto: str = Field(..., min_length=1, description="Texto do parecer do orientador")
    recomendacao: str = Field(..., description="aprovar | rejeitar | aguardar")


class ValidateActivityRequest(BaseModel):
    acao: ValidateAction
    parecer_orientador: Optional[ParecerOrientador] = None
    observacao: Optional[str] = Field(
        default=None,
        description="Observação da coordenação ao aprovar ou rejeitar",
    )
    creditos_concedidos: Optional[float] = Field(
        default=None,
        description="Coordenação pode ajustar créditos ao aprovar",
    )


class ActivityResponse(BaseModel):
    id: str
    student_id: str
    tipo_id: str
    descricao: str
    data_realizacao: str
    comprovante_url: Optional[str] = None
    status: ActivityStatus
    creditos_gerados: Optional[float] = None
    parecer_orientador: Optional[ParecerOrientador] = None
    parecer_orientador_em: Optional[datetime] = None
    parecer_orientador_por: Optional[str] = None
    observacao_coordenacao: Optional[str] = None
    aprovado_por: Optional[str] = None
    aprovado_em: Optional[datetime] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class ValidateActivityResponse(BaseModel):
    """Resposta específica para operações de aprovação/rejeição pela coordenação."""

    message: str
    novo_status: ActivityStatus
    creditos_contabilizados: Optional[float] = None
    motor_inferencia_executado: bool = False
    fato_gerado: Optional[str] = None
"""
Modelos Pydantic para a agregação de solicitações (Requests Inbox).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


TipoSolicitacao = Literal[
    "atividade",
    "prorrogacao",
    "trancamento",
    "transferencia",
    "transferencia_coordenacao",
]

OrigemSolicitacao = Literal["formulario", "agregado"]


class RequestItem(BaseModel):
    """
    Representa um item normalizado na caixa de entrada unificada de solicitações.

    `origem` distingue a proveniência do subtipo (ver CONTEXT.md → Solicitação):
    - "formulario": criado pelo formulário "Nova Solicitação" (prorrogacao,
      trancamento, transferencia de orientando).
    - "agregado": nasce de outro fluxo e é apenas agregado nesta lista
      (validação de atividade/produção, transferência de coordenação).
    """
    id: str
    tipo: TipoSolicitacao
    origem: OrigemSolicitacao
    solicitante_nome: str
    data_solicitacao: datetime
    status: str
    payload_original: dict[str, Any]

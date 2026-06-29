"""
Modelos Pydantic para a agregação de solicitações (Requests Inbox).
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


TipoSolicitacao = Literal[
    "atividade", "prorrogacao", "transferencia", "transferencia_coordenacao"
]


class RequestItem(BaseModel):
    """
    Representa um item normalizado na caixa de entrada unificada de solicitações.
    """
    id: str
    tipo: TipoSolicitacao
    solicitante_nome: str
    data_solicitacao: datetime
    status: str
    payload_original: dict[str, Any]

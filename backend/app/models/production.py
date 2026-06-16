"""
Modelos Pydantic para a entidade Production (produção bibliográfica).

Responsabilidades:
- Definir ProductionCreate para POST /api/v1/productions com campos: titulo, doi,
  veiculo_id, tipo_producao, status_publicacao, observacao, data_realizacao,
  comprovante_url.
- Definir ProductionResponse para leitura incluindo veiculo_nome, nivel_veiculo (de
  vehicle_levels do programa), pontuacao_calculada (resultado do motor RL05), peso_aplicado
  e status_atividade (do documento activity associado).
- Produção é subtipo de atividade: cada produção referencia um activity_id e herda o
  fluxo de validação (rascunho → enviado → aprovado | rejeitado).
- Mapear a sub-coleção Firestore students/{id}/productions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TipoProducao = Literal["artigo_publicado", "artigo_submetido", "livro", "capitulo"]

StatusPublicacao = Literal["publicado", "submetido", "aceito"]


class ProductionCreate(BaseModel):
    titulo: str
    doi: str | None = None
    veiculo_id: str
    tipo_producao: TipoProducao
    status_publicacao: StatusPublicacao
    observacao: str | None = None
    data_realizacao: datetime
    comprovante_url: str | None = None


class ProductionResponse(BaseModel):
    id: str
    titulo: str
    doi: str | None = None
    veiculo_nome: str
    nivel_veiculo: str
    tipo_producao: TipoProducao
    status_publicacao: StatusPublicacao
    observacao: str | None = None
    pontuacao_calculada: float
    peso_aplicado: float
    status_atividade: str

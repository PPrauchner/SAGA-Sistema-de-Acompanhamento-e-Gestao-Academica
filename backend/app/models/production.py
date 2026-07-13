"""
Modelos Pydantic para a entidade Production (produção bibliográfica).

Responsabilidades:
- Definir ProductionCreate para POST /api/v1/productions com campos: titulo, doi,
  veiculo_id, tipo_producao, status_publicacao, observacao, autores, data_realizacao,
  comprovante_url.
- Definir ProductionResponse para leitura incluindo veiculo_nome, nivel_veiculo (de
  vehicle_levels do programa), pontuacao_calculada (resultado do motor RL05), peso_aplicado
  e status_atividade (do documento activity associado).
- Produção é coleção raiz Firestore (productions/{id}); a FK é invertida: cada aluno autor
  tem um documento students/{id}/activities com activities.producao_id → productions/{id},
  por onde herda o fluxo de validação (rascunho → enviado → aprovado | rejeitado).
- autores admite uids de alunos cadastrados e strings livres (autores externos).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from backend.app.models.validators import DataEventoRealizacao

# tipo_producao descreve apenas a NATUREZA da produção; a situação de publicação
# (publicado/submetido/aceito) vive exclusivamente em status_publicacao.
TipoProducao = Literal["artigo", "livro", "capitulo"]

StatusPublicacao = Literal["publicado", "submetido", "aceito"]


class ProductionCreate(BaseModel):
    titulo: str
    doi: str | None = None
    veiculo_id: str
    tipo_producao: TipoProducao
    status_publicacao: StatusPublicacao
    observacao: str | None = None
    # uids de alunos cadastrados e/ou strings livres (autores externos). O autor que registra
    # é sempre incluído pelo service; cada uid cadastrado recebe uma activity dedicada.
    autores: list[str] = []
    data_realizacao: DataEventoRealizacao
    comprovante_url: str | None = None


class ProductionResponse(BaseModel):
    id: str
    aluno_id: str
    aluno_nome: str
    titulo: str
    doi: str | None = None
    veiculo_nome: str
    nivel_veiculo: str
    tipo_producao: TipoProducao
    status_publicacao: StatusPublicacao
    observacao: str | None = None
    autores: list[str] = []
    pontuacao_calculada: float
    peso_aplicado: float
    status_atividade: str

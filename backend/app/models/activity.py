"""
Modelos Pydantic para a entidade Activity (atividade creditável).

Responsabilidades:
- Definir ActivityCreate para POST /api/v1/activities com campos: tipo_id, descricao,
  data_realizacao, comprovante_url, status inicial.
- Definir ActivityResponse para leitura incluindo tipo_nome, categoria, creditos_gerados,
  status do fluxo de validação, parecer_orientador, observacao_coordenacao e campo
  elegivel calculado pelo motor RL04 quando status='aprovado'.
- Definir ActivityValidateRequest para PATCH /api/v1/activities/{id}/validate com campos:
  acao (parecer_orientador | aprovar | rejeitar), observacao e creditos_concedidos.
- Definir ComprovanteUploadResponse para POST /api/v1/activities/{activity_id}/comprovante
  com a URL de download tokenizada e o path no bucket do Storage.
- Mapear a sub-coleção Firestore students/{id}/activities.
"""

from __future__ import annotations

from pydantic import BaseModel


class ComprovanteUploadResponse(BaseModel):
    comprovante_url: str
    path_bucket: str

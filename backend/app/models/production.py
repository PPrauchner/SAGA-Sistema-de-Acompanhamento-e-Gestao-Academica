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

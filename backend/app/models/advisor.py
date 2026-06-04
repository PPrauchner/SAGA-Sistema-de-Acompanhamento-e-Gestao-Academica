"""
Modelos Pydantic para a entidade Advisor (orientador).

Responsabilidades:
- Definir AdvisorBase com campos: uid, nome, email, departamento, lattes, programa_id,
  limite_orientandos.
- Definir AdvisorCreate para POST /api/v1/advisors.
- Definir AdvisorUpdate para PUT /api/v1/advisors/{id} (campos opcionais).
- Definir AdvisorResponse para leitura, incluindo orientandos_ativos (calculado por query
  na coleção students/ filtrando por orientador_id).
- Mapear o documento Firestore da coleção advisors/.
"""

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

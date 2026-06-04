"""
Serviço de negócio para gestão de orientadores.

Responsabilidades:
- Implementar CRUD de orientadores delegando persistência ao AdvisorRepository.
- create_advisor(): cria orientador no Firestore e dispara convite de primeiro acesso via
  AuthService. Decorado com @requires_role('coordenacao') e @audit_operation.
- update_advisor(): atualiza dados do orientador (nome, departamento, lattes, limite).
  Decorado com @requires_role('coordenacao') e @audit_operation.
- get_advisors_with_count(): lista orientadores enriquecendo cada registro com contagem
  de orientandos_ativos calculada por query na coleção students/.
- Verificar limite_orientandos antes de permitir associação de novo orientando ao orientador.
"""

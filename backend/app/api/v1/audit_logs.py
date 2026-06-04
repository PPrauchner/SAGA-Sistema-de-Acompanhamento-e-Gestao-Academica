"""
Router FastAPI para o endpoint de consulta paginada de logs de auditoria.

Responsabilidades:
- GET /api/v1/audit-logs: retorna lista paginada de documentos da coleção audit_logs/ com
  filtros opcionais por usuario_id, operacao, modulo, data_inicio, data_fim e
  resultado_status. Suporta paginação via parâmetros page e page_size (max: 100). Dados
  gerados pelo aspecto A02 (@audit_operation). Exclusivo de @requires_role('coordenacao').
  Alimenta a AuditPage do frontend com dados reais em substituição aos dados hardcoded.
"""

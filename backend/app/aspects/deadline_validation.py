"""
Aspecto A04 — Validação de Prazos (Before + After advice).

Responsabilidades:
- Implementar o decorador @check_deadlines usando mecanismos nativos do Python, sem
  bibliotecas externas de AOP.
- Before: extrai aluno_id do contexto; carrega prazo_final, data_ingresso e status do
  Firestore. Calcula dias_restantes = prazo_final - date.today(). Se prazo estourado,
  insere fato prazo_estourado na FactBase. Se dentro de DIAS_ALERTA_PRAZO_QUALIFICACAO
  (configurado em aspect_config), insere fato prazo_qualificacao_proximo.
- Executa a função original.
- After: se situacao_inferida mudou, persiste atualização em students/{id}. Se prazo
  crítico detectado, delega criação de notificação ao aspecto A05 (alerts.py).
- Join points: POST /api/v1/tasks/{id}/updates, POST /api/v1/activities, POST
  /api/v1/extensions, GET /api/v1/students (listagem), GET /api/v1/inference/{student_id}.
"""

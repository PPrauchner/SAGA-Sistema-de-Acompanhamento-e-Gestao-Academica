"""
Aspecto A05 — Geração de Alertas e Notificações (After advice).

Responsabilidades:
- Implementar o decorador @trigger_alerts usando mecanismos nativos do Python, sem
  bibliotecas externas de AOP.
- After: verifica flag ALERTS_ENABLED em aspect_config. Extrai resultado da função original;
  determina destinatários (aluno_id → orientador_id via Firestore lookup). Monta documento
  Notification com {tipo, titulo, mensagem, destinatario_id, entidade_id, lida: false,
  timestamp} e persiste em notifications/{auto_id} no Firestore.
- Join points e alertas:
    - POST tasks/{id}/updates → notifica orientador (progresso registrado).
    - PATCH activities/{id}/validate → notifica aluno (aprovada|rejeitada).
    - PATCH extensions/{id}/approve → notifica aluno (resultado e novo prazo).
    - Delegação do A04 para prazo crítico → notifica aluno + orientador.
    - POST activities → notifica orientador (atividade submetida para validação).
- Frontend assina onSnapshot em notifications/ filtrado por destinatario_id para receber
  alertas em tempo real.
"""

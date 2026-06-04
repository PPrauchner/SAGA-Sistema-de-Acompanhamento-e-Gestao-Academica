"""
Aspecto A02 — Auditoria das Operações (Around advice).

Responsabilidades:
- Implementar o decorador @audit_operation usando inspect para captura de metadados em
  tempo de execução, sem bibliotecas externas de AOP.
- Before (captura): usa inspect.signature(func).bind(*args, **kwargs).arguments para
  extrair parâmetros nomeados; registra timestamp_inicio, usuario_id, role, operacao e
  entidade_afetada_id.
- Executa a função original (await func(*args, **kwargs)).
- After (persiste): monta documento AuditLog com {usuario_id, role, operacao, modulo
  (via inspect.getmodule), recurso, valor_entrada, resultado_status, erro_mensagem,
  timestamp, duracao_ms} e persiste em audit_logs/{auto_id} no Firestore.
- Em caso de exceção: registra erro no AuditLog e re-lança a exceção.
- Paradigma AOP: decorador Python + inspect como mecanismo de weaving explícito.
"""

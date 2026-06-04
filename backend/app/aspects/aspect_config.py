"""
Flags de configuração e constantes para todos os aspectos AOP do sistema.

Responsabilidades:
- Definir flags booleanas que ativam ou desativam cada aspecto sem alterar a lógica de
  negócio: AUTHORIZATION_ENABLED, AUDIT_ENABLED, HISTORY_ENABLED,
  DEADLINE_VALIDATION_ENABLED, ALERTS_ENABLED.
- Centralizar constantes de prazo utilizadas pelo aspecto A04 (deadline_validation.py):
  DIAS_ALERTA_PRAZO_QUALIFICACAO (default: 90) e DIAS_ALERTA_PRAZO_FINAL (default: 60).
- Servir como ponto único de configuração operacional — ligar ou desligar um aspecto
  em ambiente de teste requer apenas alterar a flag aqui.
"""

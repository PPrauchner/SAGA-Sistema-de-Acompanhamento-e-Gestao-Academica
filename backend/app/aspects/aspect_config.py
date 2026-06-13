"""
Flags de configuração e constantes para todos os aspectos AOP do sistema.

Responsabilidades:
- Definir flags booleanas que ativam/desativam cada aspecto sem alterar lógica de negócio.
- Centralizar constantes de prazo usadas pelo aspecto A04.
"""

AUTHORIZATION_ENABLED: bool = True
AUDIT_ENABLED: bool = True
HISTORY_ENABLED: bool = True
DEADLINE_VALIDATION_ENABLED: bool = True
ALERTS_ENABLED: bool = True

DIAS_ALERTA_PRAZO_QUALIFICACAO: int = 90
DIAS_ALERTA_PRAZO_FINAL: int = 60

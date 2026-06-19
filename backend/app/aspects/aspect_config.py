"""
Flags de configuração e constantes para todos os aspectos AOP do sistema.

Responsabilidades:
- Definir flags booleanas que ativam ou desativam cada aspecto.
"""

from __future__ import annotations

# --- Flags de ativação dos aspectos --------------------------------------
# Cada aspecto consulta sua flag antes de executar o advice. Desligar um
# aspecto (ex: em teste) não exige alterar a lógica de negócio decorada.
AUTHORIZATION_ENABLED: bool = True
AUDIT_ENABLED: bool = True
HISTORY_ENABLED: bool = True
DEADLINE_VALIDATION_ENABLED: bool = True
ALERTS_ENABLED: bool = True

# --- Constantes de prazo (aspecto A04 — deadline_validation.py) -----------
# Quantos dias antes do prazo de qualificação um alerta deve ser disparado.
DIAS_ALERTA_PRAZO_QUALIFICACAO: int = 90
# Quantos dias antes do prazo final um alerta deve ser disparado.
DIAS_ALERTA_PRAZO_FINAL: int = 60

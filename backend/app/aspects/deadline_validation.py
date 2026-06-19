"""
Aspecto A04 — Validação de Prazos (Before + After advice).

Estado: SKELETON flag-gated. O decorador @check_deadlines já existe, é transparente e
respeita a flag DEADLINE_VALIDATION_ENABLED — habilitando a cobertura de teste da flag
exigida pela issue de aspectos. O advice em si (`_apply_deadline_advice`) é, por ora, um
no-op.

PENDENTE (issue própria, acoplada ao motor de inferência) — implementar em
`_apply_deadline_advice`:
- Before: extrair aluno_id do contexto; carregar prazo_final, data_ingresso e situacao do
  Firestore; calcular dias_restantes = prazo_final - date.today(); se prazo estourado,
  inserir fato prazo_estourado na FactBase; se dentro de DIAS_ALERTA_PRAZO_QUALIFICACAO,
  inserir fato prazo_qualificacao_proximo.
- After: se situacao_inferida mudou, persistir atualização em students/{id}; se prazo
  crítico detectado, delegar criação de notificação ao aspecto A05 (alerts.py).

Join Point: endpoints/serviços temporalmente sensíveis decorados com @check_deadlines
    (POST tasks/{id}/updates, POST activities, POST extensions, GET students, GET
    inference/{student_id}).
Advice: Before + After (verifica datas antes; atualiza fato de risco depois).
Weaving: decorador Python aplicado explicitamente, na ordem canônica entre @audit_operation
    e @trigger_alerts.

Mecanismo: decorador Python nativo, sem bibliotecas externas de AOP.
"""

from __future__ import annotations

import functools
from typing import Any

from backend.app.aspects import aspect_config


async def _apply_deadline_advice(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: Any,
) -> None:
    """Seam do advice de prazo do A04 — no-op por ora.

    Ponto único onde a lógica de prazo PENDENTE (ver docstring do módulo) será
    implementada. Mantido isolado para que a fiação e a flag não precisem mudar
    quando a lógica for adicionada.
    """
    return None


def check_deadlines(func):
    """Aspecto A04 — Validação de Prazos (skeleton flag-gated).

    Quando DEADLINE_VALIDATION_ENABLED é False, é totalmente transparente. Quando True,
    executa a função original e em seguida o advice de prazo (`_apply_deadline_advice`).
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not aspect_config.DEADLINE_VALIDATION_ENABLED:
            return await func(*args, **kwargs)

        result = await func(*args, **kwargs)
        await _apply_deadline_advice(args, kwargs, result)
        return result

    return wrapper

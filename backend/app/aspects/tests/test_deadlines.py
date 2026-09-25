"""
Testes do aspecto A04 — @check_deadlines (skeleton flag-gated).

Verifica que o decorador é transparente (preserva o retorno) e que a flag
DEADLINE_VALIDATION_ENABLED liga/desliga o advice: o seam `_apply_deadline_advice` é
chamado quando habilitado e ignorado quando desabilitado.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.aspects import aspect_config
from backend.app.aspects import deadline_validation as deadline_module
from backend.app.aspects.deadline_validation import check_deadlines


def _spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[Any, ...], dict[str, Any], Any]]:
    chamadas: list[tuple[tuple[Any, ...], dict[str, Any], Any]] = []

    async def fake_advice(func: Any, args: tuple[Any, ...], kwargs: dict[str, Any], result: Any) -> None:
        chamadas.append((args, kwargs, result))

    monkeypatch.setattr(deadline_module, "_apply_deadline_advice", fake_advice)
    return chamadas


async def test_flag_ativa_executa_advice_e_preserva_retorno(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas = _spy(monkeypatch)

    @check_deadlines
    async def operacao(student_id: str) -> dict[str, str]:
        return {"id": student_id}

    assert await operacao("s1") == {"id": "s1"}
    assert len(chamadas) == 1
    assert chamadas[0][2] == {"id": "s1"}


async def test_flag_desativada_passa_direto_sem_advice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(aspect_config, "DEADLINE_VALIDATION_ENABLED", False)
    chamadas = _spy(monkeypatch)

    @check_deadlines
    async def operacao(student_id: str) -> str:
        return "ok"

    assert await operacao("s1") == "ok"
    assert chamadas == []

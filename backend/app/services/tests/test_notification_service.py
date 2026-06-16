"""
Testes do NotificationService — marcação de notificação como lida.

Usa um repositório fake em memória (sem Firestore) para verificar a marcação pelo
destinatário, o 404 para notificação inexistente e o 403 quando o usuário não é o dono.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.services import notification_service as notification_service_module
from backend.app.services.notification_service import NotificationService


class _Repo:
    store: dict[str, dict[str, Any]] = {}

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store.setdefault(doc_id, {}).update(data)


def _user(uid: str = "u1") -> CurrentUser:
    return CurrentUser(uid=uid, role="aluno", programa_id="prog_default", email="a@b.com")


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> NotificationService:
    _Repo.store = {
        "n1": {"destinatario_id": "u1", "lida": False},
        "n2": {"destinatario_id": "outro", "lida": False},
    }
    monkeypatch.setattr(notification_service_module, "FirebaseRepository", _Repo)
    return NotificationService()


async def test_destinatario_marca_como_lida(service: NotificationService) -> None:
    resp = await service.mark_as_read("n1", _user("u1"))

    assert resp.lida is True
    assert resp.id == "n1"
    assert _Repo.store["n1"]["lida"] is True


async def test_notificacao_inexistente_404(service: NotificationService) -> None:
    with pytest.raises(HTTPException) as exc:
        await service.mark_as_read("nao-existe", _user("u1"))

    assert exc.value.status_code == 404


async def test_nao_dono_403(service: NotificationService) -> None:
    with pytest.raises(HTTPException) as exc:
        await service.mark_as_read("n2", _user("u1"))

    assert exc.value.status_code == 403
    assert _Repo.store["n2"]["lida"] is False

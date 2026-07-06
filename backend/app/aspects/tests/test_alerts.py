"""
Testes do aspecto A05 — @trigger_alerts (geração de alertas e notificações).

Usa um repositório fake em memória (sem Firestore) para verificar: persistência da
notificação após sucesso, defaults transversais (lida/timestamp), respeito à flag
ALERTS_ENABLED, suporte a builder síncrono e assíncrono, builder vazio (None), múltiplas
notificações e ausência de alerta quando a operação levanta exceção.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.aspects import alerts as alerts_module
from backend.app.aspects import aspect_config
from backend.app.aspects.alerts import trigger_alerts


class _NotifRepo:
    created: list[dict[str, Any]] = []

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        type(self).created.append(dict(data))
        return f"n{len(type(self).created)}"


class _UserPrefsRepo:
    store: dict[str, dict[str, Any]] = {}

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        return self.store.get(doc_id)


def _spec(destinatario_id: str) -> dict[str, str]:
    return {
        "tipo": "atividade_validada",
        "titulo": "Título",
        "mensagem": "Mensagem",
        "destinatario_id": destinatario_id,
    }


async def test_trigger_alerts_persiste_e_aplica_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> dict[str, str]:
        return {"id": "a1"}

    assert await op() == {"id": "a1"}

    assert len(_NotifRepo.created) == 1
    doc = _NotifRepo.created[0]
    assert doc["destinatario_id"] == "u1"
    assert doc["lida"] is False
    assert doc["timestamp"] is not None


async def test_trigger_alerts_respeita_flag_desativada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(aspect_config, "ALERTS_ENABLED", False)
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> str:
        return "ok"

    assert await op() == "ok"
    assert _NotifRepo.created == []


async def test_trigger_alerts_suporta_builder_assincrono(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    async def build(result: Any, args: tuple, kwargs: dict) -> dict[str, str]:
        return _spec("u2")

    @trigger_alerts(build)
    async def op() -> None:
        return None

    await op()
    assert _NotifRepo.created[0]["destinatario_id"] == "u2"


async def test_trigger_alerts_builder_none_nao_persiste(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    @trigger_alerts(lambda result, args, kwargs: None)
    async def op() -> str:
        return "ok"

    await op()
    assert _NotifRepo.created == []


async def test_trigger_alerts_lista_persiste_varias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    @trigger_alerts(lambda result, args, kwargs: [_spec("aluno"), _spec("orientador")])
    async def op() -> dict:
        return {}

    await op()
    assert {doc["destinatario_id"] for doc in _NotifRepo.created} == {"aluno", "orientador"}


async def test_trigger_alerts_nao_dispara_em_excecao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)
    _UserPrefsRepo.store = {}

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> None:
        raise ValueError("falha")

    with pytest.raises(ValueError):
        await op()

    assert _NotifRepo.created == []


async def test_trigger_alerts_respeita_preferencia_desabilitada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    _UserPrefsRepo.store = {
        "u1": {"notification_preferences": {"activities": False}},
    }
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> str:
        return "ok"

    await op()

    assert _NotifRepo.created == []


async def test_trigger_alerts_envia_quando_preferencia_habilitada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    _UserPrefsRepo.store = {
        "u1": {"notification_preferences": {"activities": True}},
    }
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)
    monkeypatch.setattr(alerts_module, "UserPreferencesRepository", _UserPrefsRepo)

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> str:
        return "ok"

    await op()

    assert len(_NotifRepo.created) == 1

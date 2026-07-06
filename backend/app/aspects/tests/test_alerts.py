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

    @trigger_alerts(lambda result, args, kwargs: [_spec("aluno"), _spec("orientador")])
    async def op() -> dict:
        return {}

    await op()
    assert {doc["destinatario_id"] for doc in _NotifRepo.created} == {"aluno", "orientador"}


async def test_notifica_coordenacao_na_criacao_pelo_orientador(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Prova a fiação da issue #263: quando a função retorna o dict do service (com
    # coord_uids), o builder emite uma notificação por coordenador. O endpoint
    # submit_activity_by_advisor retorna esse dict justamente para o advice enxergar.
    from backend.app.api.v1.activities import _build_notificacao_criacao_orientador

    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)

    @trigger_alerts(_build_notificacao_criacao_orientador)
    async def op() -> dict[str, Any]:
        return {
            "id": "a1",
            "aluno_nome": "Maria",
            "programa_id": "prog_default",
            "coord_uids": ["c1", "c2"],
        }

    await op()

    assert {doc["destinatario_id"] for doc in _NotifRepo.created} == {"c1", "c2"}
    assert all(doc["tipo"] == "atividade_submetida" for doc in _NotifRepo.created)
    assert all(doc["entidade_id"] == "a1" for doc in _NotifRepo.created)


async def test_trigger_alerts_nao_dispara_em_excecao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _NotifRepo.created = []
    monkeypatch.setattr(alerts_module, "FirebaseRepository", _NotifRepo)

    @trigger_alerts(lambda result, args, kwargs: _spec("u1"))
    async def op() -> None:
        raise ValueError("falha")

    with pytest.raises(ValueError):
        await op()

    assert _NotifRepo.created == []

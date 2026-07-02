"""
Testes do UserNameResolver — traducao uid -> nome de exibicao no read path.

Usa um repositório fake em memória (sem Firestore) para verificar a resolucao em lote,
o fallback nome -> email -> uid e o tratamento de uids desconhecidos/vazios.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.app.services.user_name_resolver import UserNameResolver

_USERS: list[dict[str, Any]] = [
    {"uid": "u1", "nome": "Ana Souza", "email": "ana@x.com"},
    {"uid": "u2", "nome": "", "email": "bruno@x.com"},
    {"uid": "u3", "email": "carla@x.com"},
    {"uid": "u4"},
]


class _FakeUsersRepo:
    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(user) for user in _USERS]


@pytest.fixture
def resolver() -> UserNameResolver:
    return UserNameResolver(user_repo=_FakeUsersRepo())


async def test_resolve_usa_nome_quando_presente(resolver: UserNameResolver) -> None:
    assert await resolver.resolve(["u1"]) == {"u1": "Ana Souza"}


async def test_resolve_cai_para_email_quando_nome_vazio_ou_ausente(
    resolver: UserNameResolver,
) -> None:
    resolved = await resolver.resolve(["u2", "u3"])

    assert resolved == {"u2": "bruno@x.com", "u3": "carla@x.com"}


async def test_resolve_cai_para_uid_quando_sem_nome_e_email(
    resolver: UserNameResolver,
) -> None:
    assert await resolver.resolve(["u4"]) == {"u4": "u4"}


async def test_resolve_em_lote_apenas_uids_pedidos(resolver: UserNameResolver) -> None:
    resolved = await resolver.resolve(["u1", "u3"])

    assert resolved == {"u1": "Ana Souza", "u3": "carla@x.com"}


async def test_resolve_ignora_desconhecidos_e_vazios(resolver: UserNameResolver) -> None:
    resolved = await resolver.resolve(["u1", "inexistente", "", None])  # type: ignore[list-item]

    assert resolved == {"u1": "Ana Souza"}


async def test_resolve_sem_uids_nao_consulta(resolver: UserNameResolver) -> None:
    assert await resolver.resolve([]) == {}

"""
Testes do QualisWeightsService e da resolução pura de pesos por data (ADR-0003).

Cobre:
- resolve_weights_at: seleção da versão de maior vigente_desde <= data; None sem versão.
- set_weights: cria nova versão sem sobrescrever a anterior (a coleção é o histórico).
- list_history: ordena da versão mais recente para a mais antiga.
- get_weights_at/get_active_weights: resolução por data com fallback para PESO_POR_NIVEL.
- escopo por programa: versões de um programa não vazam para outro.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.models.qualis_weights import QualisWeightsUpdate
from backend.app.models.vehicle import PESO_POR_NIVEL
from backend.app.services import qualis_weights_service as qws_module
from backend.app.services.qualis_weights_service import (
    QualisWeightsService,
    resolve_weights_at,
)


def _full(**overrides: float) -> dict[str, float]:
    """Conjunto completo de pesos (default) com sobrescritas pontuais."""
    pesos = dict(PESO_POR_NIVEL)
    pesos.update(overrides)
    return pesos


def _version(vid: str, ano: int, **pesos: float) -> dict[str, Any]:
    return {
        "id": vid,
        "pesos": _full(**pesos),
        "vigente_desde": datetime(ano, 1, 1, tzinfo=timezone.utc),
    }


# -- resolve_weights_at (função pura) ---------------------------------------------------


def test_resolve_seleciona_versao_vigente_na_data() -> None:
    versions = [_version("v1", 2024, A1=1.0), _version("v2", 2025, A1=0.5)]
    meio = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert resolve_weights_at(versions, meio)["A1"] == 1.0


def test_resolve_usa_versao_mais_recente_aplicavel() -> None:
    versions = [_version("v1", 2024, A1=1.0), _version("v2", 2025, A1=0.5)]
    depois = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert resolve_weights_at(versions, depois)["A1"] == 0.5


def test_resolve_retorna_none_antes_de_qualquer_versao() -> None:
    versions = [_version("v1", 2024, A1=1.0)]
    antes = datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert resolve_weights_at(versions, antes) is None


def test_resolve_retorna_none_sem_versoes() -> None:
    assert resolve_weights_at([], datetime.now(timezone.utc)) is None


# -- QualisWeightsService ---------------------------------------------------------------


class _FakeRepo:
    """QualisWeightsRepository fake em memória, por programa."""

    def __init__(self) -> None:
        self.store: dict[str, list[dict[str, Any]]] = {}
        self._counter = 0

    async def create_version(self, programa_id: str, data: dict[str, Any]) -> str:
        self._counter += 1
        vid = f"v{self._counter}"
        self.store.setdefault(programa_id, []).append({**data, "id": vid})
        return vid

    async def list_versions(self, programa_id: str) -> list[dict[str, Any]]:
        return [dict(v) for v in self.store.get(programa_id, [])]


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> QualisWeightsService:
    monkeypatch.setattr(qws_module, "QualisWeightsRepository", _FakeRepo)
    return QualisWeightsService()


async def test_set_weights_cria_versao_com_metadados(service: QualisWeightsService) -> None:
    result = await service.set_weights("prog1", "coord-uid", QualisWeightsUpdate(pesos=_full(A1=2.0)))

    assert result["id"] == "v1"
    versao = service._repo.store["prog1"][0]
    assert versao["pesos"]["A1"] == 2.0
    assert versao["alterado_por"] == "coord-uid"
    assert "vigente_desde" in versao and "alterado_em" in versao


async def test_set_weights_nao_sobrescreve_versao_anterior(service: QualisWeightsService) -> None:
    await service.set_weights("prog1", "coord-uid", QualisWeightsUpdate(pesos=_full(A1=1.0)))
    await service.set_weights("prog1", "coord-uid", QualisWeightsUpdate(pesos=_full(A1=0.5)))

    versoes = service._repo.store["prog1"]
    assert len(versoes) == 2
    assert [v["pesos"]["A1"] for v in versoes] == [1.0, 0.5]


async def test_list_history_ordena_recente_primeiro(service: QualisWeightsService) -> None:
    service._repo.store["prog1"] = [
        _version("antiga", 2024, A1=1.0),
        _version("nova", 2025, A1=0.5),
    ]
    history = await service.list_history("prog1")
    assert [v["id"] for v in history] == ["nova", "antiga"]


async def test_get_active_weights_fallback_sem_versao(service: QualisWeightsService) -> None:
    assert await service.get_active_weights("prog1") == dict(PESO_POR_NIVEL)


async def test_escopo_por_programa_nao_vaza(service: QualisWeightsService) -> None:
    await service.set_weights("prog1", "coord-uid", QualisWeightsUpdate(pesos=_full(A1=2.0)))
    # prog2 nunca recebeu versão → cai no fallback default, não vê os pesos de prog1.
    assert await service.get_active_weights("prog2") == dict(PESO_POR_NIVEL)

"""
Testes da resolução de peso por data de publicação na pontuação RL05 (ADR-0003).

Verifica que o InferenceService pontua cada produção com o peso vigente na sua data de
publicação: produções do mesmo nível publicadas sob versões de peso distintas recebem
scores distintos, e produção não publicada usa o peso vigente atual. O motor (RL05)
permanece isolado — apenas o peso injetado muda.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.models.vehicle import PESO_POR_NIVEL
from backend.app.repositories.fixtures import FixtureRepository
from backend.app.services.inference_service import InferenceService


def _full(**overrides: float) -> dict[str, float]:
    pesos = dict(PESO_POR_NIVEL)
    pesos.update(overrides)
    return pesos


_VERSIONS: list[dict[str, Any]] = [
    {"id": "vw1", "pesos": _full(A1=1.0), "vigente_desde": datetime(2024, 1, 1, tzinfo=timezone.utc)},
    {"id": "vw2", "pesos": _full(A1=0.5), "vigente_desde": datetime(2025, 1, 1, tzinfo=timezone.utc)},
]


@pytest.fixture
def service() -> InferenceService:
    return InferenceService(FixtureRepository())


def _scores_by_id(service: InferenceService, productions: list[dict[str, Any]]) -> dict[str, float]:
    pontuacoes = service._score_productions(productions, _VERSIONS)
    return {p.producao_id: p.score for p in pontuacoes}


def test_publicada_usa_peso_vigente_na_data_de_publicacao(service: InferenceService) -> None:
    productions = [
        {"id": "p_old", "nivel": "A1", "pontuacao_base": 10, "status_publicacao": "publicado", "data_realizacao": "2024-06-01"},
        {"id": "p_new", "nivel": "A1", "pontuacao_base": 10, "status_publicacao": "publicado", "data_realizacao": "2025-06-01"},
    ]
    scores = _scores_by_id(service, productions)
    # p_old publicada sob a vw1 (A1=1.0); p_new sob a vw2 (A1=0.5) — mesmo nível, scores distintos.
    assert scores["p_old"] == 10.0
    assert scores["p_new"] == 5.0


def test_nao_publicada_usa_peso_vigente_atual(service: InferenceService) -> None:
    # Submetida sem data: usa o peso vigente hoje (após 2025-01-01 → vw2, A1=0.5).
    productions = [
        {"id": "p_sub", "nivel": "A1", "pontuacao_base": 10, "status_publicacao": "submetido", "data_realizacao": None},
    ]
    scores = _scores_by_id(service, productions)
    assert scores["p_sub"] == 5.0


def test_sem_nivel_nao_pontua(service: InferenceService) -> None:
    productions = [{"id": "p_sem", "nivel": None, "pontuacao_base": 10, "status_publicacao": "publicado"}]
    assert _scores_by_id(service, productions) == {}

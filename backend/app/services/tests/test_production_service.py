"""
Testes do ProductionService.

Cobre:
- _resolve_pontuacao_base: artigo modulado por status_publicacao (publicado/aceito/
  submetido) e tipos de base única (livro/capítulo). Função pura — sem acesso ao Firebase.
- Acoplamento com atividade (FK invertida): create_production grava a produção na coleção
  raiz e cria uma atividade com producao_id por autor cadastrado; list_productions expõe o
  status_atividade vindo da atividade ligada.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from backend.app.core.auth import CurrentUser
from backend.app.models.production import ProductionCreate
from backend.app.services import production_service as production_module
from backend.app.services.production_service import (
    ACTIVITY_CATEGORIA_PRODUCAO,
    ProductionService,
    _resolve_pontuacao_base,
)


@pytest.mark.parametrize(
    "status, esperado",
    [
        ("publicado", 1.0),
        ("aceito", 0.8),
        ("submetido", 0.3),
    ],
)
def test_artigo_varia_por_status(status: str, esperado: float) -> None:
    assert _resolve_pontuacao_base("artigo", status) == esperado


@pytest.mark.parametrize(
    "tipo, esperado",
    [
        ("livro", 1.0),
        ("capitulo", 0.6),
    ],
)
def test_tipo_base_unica_ignora_status(tipo: str, esperado: float) -> None:
    # Para livro/capítulo o status não altera a base.
    assert _resolve_pontuacao_base(tipo, "publicado") == esperado
    assert _resolve_pontuacao_base(tipo, "submetido") == esperado


# -- Acoplamento com atividade (#45) ----------------------------------------------------


class _FakeProductionRepository:
    store: dict[str, dict[str, Any]] = {}
    counter = 0

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        production_id = f"prod{type(self).counter}"
        type(self).store[production_id] = {**data, "id": production_id}
        return production_id

    async def get(self, production_id: str) -> dict[str, Any] | None:
        item = type(self).store.get(production_id)
        return dict(item) if item else None


class _FakeActivityRepository:
    store: dict[str, list[dict[str, Any]]] = {}
    counter = 0

    async def create_activity(self, student_id: str, data: dict[str, Any]) -> str:
        type(self).counter += 1
        activity_id = f"act{type(self).counter}"
        type(self).store.setdefault(student_id, []).append({**data, "id": activity_id})
        return activity_id

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return [dict(item) for item in type(self).store.get(student_id, [])]


class _FakeVehicleRepository:
    async def list_levels(self, programa_id: str) -> list[dict[str, Any]]:
        return [{"id": "veic1", "nivel": "A1", "peso": 2.0}]

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": "veic1", "nome": "Revista X"}]


class _FakeStudentService:
    async def list_students(self, user: CurrentUser) -> list[dict[str, Any]]:
        return [{"id": "student1", "uid": "uid-aluno", "nome": "Maria"}]


class _FakeInferenceService:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def score_production(self, nivel: str, peso: float, pontuacao_base: float) -> float:
        return peso * pontuacao_base


class _FakeQualisWeightsService:
    """Pesos Qualis versionados: A1=2.0 (peso vigente resolvido por data)."""

    async def get_weights_at(self, programa_id: str, when: Any) -> dict[str, float]:
        return {"A1": 2.0, "SC": 0.1}


@pytest.fixture(autouse=True)
def _setup_coupling(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeProductionRepository.store = {}
    _FakeProductionRepository.counter = 0
    _FakeActivityRepository.store = {}
    _FakeActivityRepository.counter = 0
    monkeypatch.setattr(production_module, "ProductionRepository", _FakeProductionRepository)
    monkeypatch.setattr(production_module, "ActivityRepository", _FakeActivityRepository)
    monkeypatch.setattr(production_module, "VehicleRepository", _FakeVehicleRepository)
    monkeypatch.setattr(production_module, "StudentService", _FakeStudentService)
    monkeypatch.setattr(production_module, "InferenceService", _FakeInferenceService)
    monkeypatch.setattr(production_module, "InferenceRepository", lambda: object())
    monkeypatch.setattr(production_module, "QualisWeightsService", _FakeQualisWeightsService)


def _aluno() -> CurrentUser:
    return CurrentUser(uid="uid-aluno", role="aluno", programa_id="prog1", email="a@x.com")


def _payload() -> ProductionCreate:
    return ProductionCreate(
        titulo="Artigo X",
        veiculo_id="veic1",
        tipo_producao="artigo",
        status_publicacao="publicado",
        data_realizacao=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


async def test_create_production_cria_atividade_ligada() -> None:
    service = ProductionService()

    result = await service.create_production(_payload(), _aluno())

    assert result["id"] == "prod1"
    assert "activity_id" not in result  # FK agora é activities.producao_id
    assert result["pontuacao_calculada"] == 2.0  # peso 2.0 x base 1.0 (artigo publicado)

    atividade = _FakeActivityRepository.store["student1"][0]
    assert atividade["tipo_id"] is None
    assert atividade["producao_id"] == "prod1"  # FK invertida
    assert atividade["categoria"] == ACTIVITY_CATEGORIA_PRODUCAO
    assert atividade["status"] == "enviado"
    assert atividade["creditos_gerados"] == 2.0  # = pontuacao_calculada

    producao = _FakeProductionRepository.store["prod1"]
    assert "activity_id" not in producao  # produção não referencia atividade
    assert "uid-aluno" in producao["autores"]  # autor que registra incluído


async def test_list_productions_usa_status_da_atividade() -> None:
    service = ProductionService()
    await service.create_production(_payload(), _aluno())
    # Orientador valida a atividade ligada: o status muda na atividade, não na produção.
    _FakeActivityRepository.store["student1"][0]["status"] = "aprovado"

    listadas = await service.list_productions(_aluno())

    assert listadas[0]["id"] == "prod1"
    assert listadas[0]["status_atividade"] == "aprovado"

from __future__ import annotations

from typing import Any

import pytest

import backend.scripts.seed_firestore as seed_module


class _FakeRepository:
    """FirebaseRepository fake em memória, fixado por coleção (como o real)."""

    store: dict[tuple[str, str], dict[str, Any]] = {}

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        return type(self).store.get((self.collection, doc_id))

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store[(self.collection, doc_id)] = dict(data)

    async def query(
        self, filters: list[tuple] | None = None, **_: Any
    ) -> list[dict[str, Any]]:
        results = []
        for (collection, doc_id), value in type(self).store.items():
            if collection != self.collection:
                continue
            if all(value.get(field) == val for field, _op, val in (filters or [])):
                results.append({"id": doc_id, **value})
        return results


class _FakeAdvisorRepository:
    """advisors/ fake: o seed verifica existência e provisiona coordenadores."""

    store: dict[str, dict[str, Any]] = {}

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        return type(self).store.get(doc_id)

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store[doc_id] = dict(data)

    async def query(self, filters: list[tuple] | None = None, **_: Any) -> list[dict[str, Any]]:
        return []


class _FakeWorkPlan:
    """WorkPlanRepository fake em memória para o seed (1 plano por aluno)."""

    plans: dict[str, dict[str, Any]] = {}
    _counter: int = 0

    async def get_plan(self, student_id: str) -> dict[str, Any] | None:
        return type(self).plans.get(student_id)

    async def create_plan(self, student_id: str, data: dict[str, Any]) -> str:
        type(self).plans[student_id] = {"student_id": student_id}
        return f"plan_{student_id}"

    async def create_stage(self, plan_id: str, data: dict[str, Any]) -> str:
        return f"stage_{plan_id}"

    async def create_task(self, stage_id: str, data: dict[str, Any]) -> str:
        type(self)._counter += 1
        return f"task_{type(self)._counter}"

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        return None


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeRepository.store = {}
    _FakeAdvisorRepository.store = {}
    _FakeWorkPlan.plans = {}
    _FakeWorkPlan._counter = 0
    monkeypatch.setattr(seed_module, "FirebaseRepository", _FakeRepository)
    monkeypatch.setattr(seed_module, "WorkPlanRepository", _FakeWorkPlan)
    monkeypatch.setattr(seed_module, "AdvisorRepository", _FakeAdvisorRepository)


async def test_seed_cria_todos_os_documentos() -> None:
    created = await seed_module.seed_firestore()

    assert created == {
        "departments": 1,
        "programs": 1,
        "vehicle_levels": 9,
        "qualis_weights": 1,
        "activity_types": 6,
        "work_plans": 1,
        "coordinator_advisors": 0,
    }
    # departments e programs com id explícito (não auto-id) — ADR-0004
    assert ("departments", "dept_default") in _FakeRepository.store
    assert ("programs", "prog_default") in _FakeRepository.store
    assert _FakeRepository.store[("programs", "prog_default")]["departamento_id"] == "dept_default"
    # vehicle_levels gravados como subcoleção via path
    assert ("programs/prog_default/vehicle_levels", "v_placeholder_a1") in _FakeRepository.store
    # versão inicial (bootstrap) de pesos Qualis na subcoleção versionada
    assert ("programs/prog_default/qualis_weights", "bootstrap") in _FakeRepository.store
    # aluno real de exemplo criado para acompanhar o plano
    assert ("students", seed_module.SEED_STUDENT_ID) in _FakeRepository.store


async def test_seed_e_idempotente() -> None:
    await seed_module.seed_firestore()
    again = await seed_module.seed_firestore()

    assert again == {
        "departments": 0,
        "programs": 0,
        "vehicle_levels": 0,
        "qualis_weights": 0,
        "activity_types": 0,
        "work_plans": 0,
        "coordinator_advisors": 0,
    }


async def test_seed_provisiona_advisor_de_coordenador_preexistente() -> None:
    """Issue #309/M5: o backfill de coordenadores antigos vive no seed, não no GET /advisors."""
    _FakeRepository.store[("users", "coord1")] = {
        "uid": "coord1",
        "nome": "Coord",
        "email": "coord@x.com",
        "role": "coordenacao",
        "programa_id": "prog_default",
    }

    created = await seed_module.seed_firestore()

    assert created["coordinator_advisors"] == 1
    assert _FakeAdvisorRepository.store["coord1"]["uid"] == "coord1"


async def test_seed_backfill_de_coordenador_e_idempotente() -> None:
    _FakeRepository.store[("users", "coord1")] = {
        "uid": "coord1",
        "nome": "Coord",
        "email": "coord@x.com",
        "role": "coordenacao",
        "programa_id": "prog_default",
    }

    await seed_module.seed_firestore()
    again = await seed_module.seed_firestore()

    assert again["coordinator_advisors"] == 0
    assert list(_FakeAdvisorRepository.store.keys()) == ["coord1"]


async def test_seed_activity_types_gravam_metadados() -> None:
    await seed_module.seed_firestore()

    tipo = _FakeRepository.store[("activity_types", "artigo_publicado")]
    assert tipo["programa_id"] == "prog_default"
    assert tipo["criado_por"] == "seed_firestore"
    assert tipo["ativo"] is True
    assert "criado_em" in tipo and "atualizado_em" in tipo

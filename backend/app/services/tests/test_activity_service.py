from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityCreateRequest
from backend.app.services import activity_service as activity_module
from backend.app.services.activity_service import ActivityService


class _FakeActivityRepository:
    # store[student_id] = list[activity dict]
    store: dict[str, list[dict[str, Any]]] = {}
    counter = 0

    async def create_activity(self, student_id: str, data: dict[str, Any]) -> str:
        type(self).counter += 1
        activity_id = f"act{type(self).counter}"
        item = {**data, "id": activity_id}
        type(self).store.setdefault(student_id, []).append(item)
        return activity_id

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return [dict(item) for item in type(self).store.get(student_id, [])]


class _FakeStudentRepository:
    store: list[dict[str, Any]] = []

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(item) for item in type(self).store]


class _FakeActivityTypeRepository:
    store: dict[str, dict[str, Any]] = {}

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]


class _FakeAdvisorRepository:
    store: dict[str, dict[str, Any]] = {}

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]


class _FakeInferenceService:
    last_kwargs: dict[str, Any] = {}
    result: bool = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def evaluate_activity_eligibility(self, **kwargs: Any) -> bool:
        type(self).last_kwargs = kwargs
        return type(self).result


def _aluno(uid: str = "uid-aluno") -> CurrentUser:
    return CurrentUser(uid=uid, role="aluno", programa_id="prog_default", email="a@x.com")


def _orientador(uid: str = "uid-orient") -> CurrentUser:
    return CurrentUser(uid=uid, role="orientador", programa_id="prog_default", email="o@x.com")


def _coord() -> CurrentUser:
    return CurrentUser(uid="uid-coord", role="coordenacao", programa_id="prog_default", email="c@x.com")


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeActivityRepository.store = {}
    _FakeActivityRepository.counter = 0
    _FakeStudentRepository.store = [
        {
            "id": "student1",
            "uid": "uid-aluno",
            "nome": "Maria",
            "programa_id": "prog_default",
            "orientador_id": "advisor1",
            "data_ingresso": datetime(2024, 3, 1, tzinfo=timezone.utc),
        },
    ]
    _FakeActivityTypeRepository.store = {
        "t1": {
            "nome": "Curso de extensão",
            "categoria": "basico",
            "pontuacao_base": 4.0,
            "limite_maximo_creditos": 12.0,
            "ativo": True,
        },
    }
    _FakeAdvisorRepository.store = {"advisor1": {"uid": "uid-orient", "nome": "Prof"}}
    _FakeInferenceService.last_kwargs = {}
    _FakeInferenceService.result = True

    monkeypatch.setattr(activity_module, "ActivityRepository", _FakeActivityRepository)
    monkeypatch.setattr(activity_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(activity_module, "ActivityTypeRepository", _FakeActivityTypeRepository)
    monkeypatch.setattr(activity_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(activity_module, "InferenceRepository", lambda: object())


def _service() -> ActivityService:
    return ActivityService(inference_service=_FakeInferenceService())


async def test_submit_enviado_cria_atividade_e_notifica_orientador() -> None:
    service = _service()

    result = await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Curso",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            comprovante_url="https://x/c.pdf",
            status="enviado",
        ),
        _aluno(),
    )

    assert result["id"] == "act1"
    assert result["elegibilidade_preliminar"] is True
    assert result["notificacao_enviada"] is True
    assert result["orientador_uid"] == "uid-orient"
    assert result["aluno_nome"] == "Maria"

    stored = _FakeActivityRepository.store["student1"][0]
    assert stored["creditos_gerados"] == 4.0
    assert stored["status"] == "enviado"


async def test_submit_passa_fatos_rl04_corretos_ao_motor() -> None:
    service = _service()

    await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Curso",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            comprovante_url="https://x/c.pdf",
            status="enviado",
        ),
        _aluno(),
    )

    kwargs = _FakeInferenceService.last_kwargs
    assert kwargs["student_id"] == "student1"
    assert kwargs["data_ingresso"] == "2024-03-01"
    assert kwargs["data_realizacao"] == "2024-06-01"
    assert kwargs["tem_comprovante"] is True
    assert kwargs["tipo_ativo"] is True
    assert kwargs["pontuacao_base"] == 4.0
    assert kwargs["limite_categoria"] == 12.0
    assert kwargs["categoria_creditos_aprovados"] == 0.0


async def test_submit_soma_creditos_aprovados_da_categoria() -> None:
    _FakeActivityRepository.store["student1"] = [
        {
            "id": "old1",
            "tipo_id": "t1",
            "status": "aprovado",
            "creditos_gerados": 8.0,
            "creditos_concedidos": 6.0,
        },
    ]
    service = _service()

    await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Outro curso",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            status="enviado",
        ),
        _aluno(),
    )

    assert _FakeInferenceService.last_kwargs["categoria_creditos_aprovados"] == 6.0
    assert _FakeInferenceService.last_kwargs["tem_comprovante"] is False


async def test_submit_rascunho_nao_notifica() -> None:
    service = _service()

    result = await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Curso",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            comprovante_url="https://x/c.pdf",
            status="rascunho",
        ),
        _aluno(),
    )

    assert result["notificacao_enviada"] is False


async def test_submit_404_tipo_inexistente() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_activity(
            ActivityCreateRequest(
                tipo_id="inexistente",
                descricao="x",
                data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            ),
            _aluno(),
        )

    assert exc_info.value.status_code == 404


async def test_submit_404_aluno_inexistente() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc_info:
        await service.submit_activity(
            ActivityCreateRequest(
                tipo_id="t1",
                descricao="x",
                data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            ),
            _aluno(uid="desconhecido"),
        )

    assert exc_info.value.status_code == 404


async def test_list_aluno_ve_apenas_proprias_enriquecidas() -> None:
    _FakeActivityRepository.store["student1"] = [
        {"id": "a1", "tipo_id": "t1", "status": "enviado"},
    ]
    service = _service()

    result = await service.list_activities(_aluno())

    assert len(result) == 1
    assert result[0]["id"] == "a1"
    assert result[0]["tipo_nome"] == "Curso de extensão"
    assert result[0]["categoria"] == "basico"
    assert result[0]["aluno_nome"] == "Maria"
    assert result[0]["orientador_nome"] == "Prof"


async def test_list_orientador_ve_orientandos() -> None:
    _FakeStudentRepository.store.append(
        {"id": "student2", "uid": "uid-outro", "orientador_id": "outro_advisor"}
    )
    _FakeActivityRepository.store["student1"] = [{"id": "a1", "tipo_id": "t1", "status": "enviado"}]
    _FakeActivityRepository.store["student2"] = [{"id": "a2", "tipo_id": "t1", "status": "enviado"}]
    service = _service()

    result = await service.list_activities(_orientador())

    assert [item["id"] for item in result] == ["a1"]


async def test_list_coordenacao_filtra_por_status_e_categoria() -> None:
    _FakeActivityRepository.store["student1"] = [
        {"id": "a1", "tipo_id": "t1", "status": "enviado"},
        {"id": "a2", "tipo_id": "t1", "status": "aprovado"},
    ]
    service = _service()

    aprovadas = await service.list_activities(_coord(), status_filter="aprovado")
    assert [item["id"] for item in aprovadas] == ["a2"]

    basicas = await service.list_activities(_coord(), categoria="basico")
    assert {item["id"] for item in basicas} == {"a1", "a2"}

    tecnologicas = await service.list_activities(_coord(), categoria="tecnologico")
    assert tecnologicas == []

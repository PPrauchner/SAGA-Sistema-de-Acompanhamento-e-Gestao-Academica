from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import ActivityCreateByAdvisorRequest, ActivityCreateRequest
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

    async def list_all_grouped(self) -> list[dict[str, Any]]:
        return [
            {**item, "student_id": student_id}
            for student_id, items in type(self).store.items()
            for item in items
        ]


class _FakeStudentRepository:
    store: list[dict[str, Any]] = []

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(item) for item in type(self).store]

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [dict(item) for item in type(self).store if item.get("programa_id") == programa_id]

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        return next((dict(item) for item in type(self).store if item.get("id") == doc_id), None)


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


class _FakeUsersRepository:
    """Repo genérico de users/ (FirebaseRepository) para resolver a coordenação."""

    store: list[dict[str, Any]] = []

    def __init__(self, collection: str | None = None) -> None:
        pass

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(user) for user in type(self).store]


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
    _FakeUsersRepository.store = [
        {"id": "uid-coord", "role": "coordenacao", "programa_id": "prog_default"},
    ]
    _FakeInferenceService.last_kwargs = {}
    _FakeInferenceService.result = True

    monkeypatch.setattr(activity_module, "ActivityRepository", _FakeActivityRepository)
    monkeypatch.setattr(activity_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(activity_module, "ActivityTypeRepository", _FakeActivityTypeRepository)
    monkeypatch.setattr(activity_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(activity_module, "FirebaseRepository", _FakeUsersRepository)
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
    assert result["created_activity_ids"] == ["act1"]


async def test_submit_sem_coautor_cria_unica_atividade() -> None:
    service = _service()

    result = await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Curso individual",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            status="enviado",
        ),
        _aluno(),
    )

    assert result["created_activity_ids"] == ["act1"]
    assert list(_FakeActivityRepository.store) == ["student1"]
    assert len(_FakeActivityRepository.store["student1"]) == 1


async def test_submit_com_dois_coautores_cria_copias_independentes() -> None:
    _FakeStudentRepository.store.extend(
        [
            {
                "id": "student2",
                "uid": "uid-coautor-1",
                "nome": "Joao",
                "programa_id": "prog_default",
                "orientador_id": "advisor1",
                "data_ingresso": datetime(2024, 3, 1, tzinfo=timezone.utc),
            },
            {
                "id": "student3",
                "uid": "uid-coautor-2",
                "nome": "Ana",
                "programa_id": "prog_default",
                "orientador_id": "advisor1",
                "data_ingresso": datetime(2024, 3, 1, tzinfo=timezone.utc),
            },
        ]
    )
    service = _service()

    result = await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Atividade em coautoria",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            status="rascunho",
            coauthor_student_uids=["uid-coautor-1", "uid-aluno", "uid-coautor-1", "uid-coautor-2"],
            external_authors=["Maria Externa"],
        ),
        _aluno(),
    )

    assert result["created_activity_ids"] == ["act1", "act2", "act3"]
    assert result["activity_group_id"]
    assert set(_FakeActivityRepository.store) == {"student1", "student2", "student3"}

    principal = _FakeActivityRepository.store["student1"][0]
    copia_1 = _FakeActivityRepository.store["student2"][0]
    copia_2 = _FakeActivityRepository.store["student3"][0]

    assert principal["id"] != copia_1["id"] != copia_2["id"]
    assert {principal["status"], copia_1["status"], copia_2["status"]} == {"enviado"}
    assert principal["origin_activity_id"] is None
    assert copia_1["origin_activity_id"] == "act1"
    assert copia_2["origin_activity_id"] == "act1"
    assert principal["activity_group_id"] == copia_1["activity_group_id"] == copia_2["activity_group_id"]
    assert principal["coauthor_student_uids"] == ["uid-coautor-1", "uid-coautor-2"]
    assert copia_1["external_authors"] == ["Maria Externa"]
    assert copia_2["creditos_gerados"] == 4.0


async def test_submit_autor_externo_nao_gera_copia() -> None:
    service = _service()

    result = await service.submit_activity(
        ActivityCreateRequest(
            tipo_id="t1",
            descricao="Atividade com autor externo",
            data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
            external_authors=["Maria Externa", "Maria Externa", " "],
        ),
        _aluno(),
    )

    assert result["created_activity_ids"] == ["act1"]
    assert _FakeActivityRepository.store["student1"][0]["external_authors"] == ["Maria Externa"]
    assert _FakeActivityRepository.store["student1"][0]["activity_group_id"] is None


async def test_submit_coautor_inexistente_gera_erro_claro() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        await service.submit_activity(
            ActivityCreateRequest(
                tipo_id="t1",
                descricao="Atividade em coautoria",
                data_realizacao=datetime(2024, 6, 1, tzinfo=timezone.utc),
                coauthor_student_uids=["uid-fantasma"],
            ),
            _aluno(),
        )

    assert exc.value.status_code == 404
    assert "Coautor" in exc.value.detail
    assert _FakeActivityRepository.store == {}


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


# -- Criação pelo orientador (issue #263) -----------------------------------------------


def _advisor_activity_payload(**overrides: Any) -> ActivityCreateByAdvisorRequest:
    data: dict[str, Any] = {
        "aluno_id": "student1",
        "tipo_id": "t1",
        "descricao": "Curso registrado pelo orientador",
        "data_realizacao": datetime(2024, 6, 1, tzinfo=timezone.utc),
        "comprovante_url": "https://x/c.pdf",
        "parecer": "Endosso do orientador",
    }
    data.update(overrides)
    return ActivityCreateByAdvisorRequest(**data)


async def test_orientador_cria_atividade_enviada_com_parecer() -> None:
    service = _service()

    result = await service.submit_activity_for_orientando(_advisor_activity_payload(), _orientador())

    assert result["id"] == "act1"
    assert result["elegibilidade_preliminar"] is True
    assert result["aluno_nome"] == "Maria"
    # Coordenação do programa é notificada (A05)
    assert result["notificacao_enviada"] is True
    assert result["coord_uids"] == ["uid-coord"]

    stored = _FakeActivityRepository.store["student1"][0]
    assert stored["status"] == "enviado"
    assert stored["parecer_orientador"] == "Endosso do orientador"
    # Créditos não são contabilizados antes da aprovação da coordenação (US-CR01)
    assert stored["creditos_gerados"] == 4.0
    assert stored["creditos_concedidos"] is None


async def test_orientador_sem_coordenacao_nao_notifica() -> None:
    _FakeUsersRepository.store = []  # programa sem coordenação cadastrada
    service = _service()

    result = await service.submit_activity_for_orientando(_advisor_activity_payload(), _orientador())

    assert result["coord_uids"] == []
    assert result["notificacao_enviada"] is False


def test_build_notificacao_criacao_orientador() -> None:
    from backend.app.api.v1.activities import _build_notificacao_criacao_orientador

    result = {
        "id": "act1",
        "aluno_nome": "Maria",
        "programa_id": "prog_default",
        "coord_uids": ["c1", "c2"],
    }
    notifs = _build_notificacao_criacao_orientador(result, (), {})

    assert [n["destinatario_id"] for n in notifs] == ["c1", "c2"]
    assert all(n["tipo"] == "atividade_submetida" for n in notifs)
    assert all(n["entidade_id"] == "act1" for n in notifs)
    assert all(n["programa_id"] == "prog_default" for n in notifs)


async def test_orientador_cria_para_aluno_inexistente_404() -> None:
    service = _service()

    with pytest.raises(HTTPException) as exc:
        await service.submit_activity_for_orientando(
            _advisor_activity_payload(aluno_id="fantasma"), _orientador()
        )

    assert exc.value.status_code == 404


async def test_resolve_advisor_uid_for_student(monkeypatch: pytest.MonkeyPatch) -> None:
    # A resolução aluno -> orientador sustenta o 403 do A01 por propriedade no router.
    monkeypatch.setattr(activity_module, "_student_repo", _FakeStudentRepository())
    monkeypatch.setattr(activity_module, "_advisor_repo", _FakeAdvisorRepository())

    uid = await activity_module.resolve_advisor_uid_for_student("student1")
    assert uid == "uid-orient"

    assert await activity_module.resolve_advisor_uid_for_student("fantasma") is None

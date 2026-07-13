from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.aspects import aspect_config
from backend.app.core.auth import CurrentUser
from backend.app.models.advisor import AdvisorCreateRequest, AdvisorUpdateRequest
from backend.app.models.student import (
    ProficienciaRequest,
    QualificacaoRequest,
    SituacaoRequest,
    StudentCreateRequest,
)
from backend.app.models.user import InviteRequest
from backend.app.services import advisor_service as advisor_module
from backend.app.services import student_service as student_module
from backend.app.services.advisor_service import AdvisorService
from backend.app.services.student_service import StudentService


class _FakeRepo:
    store: dict[str, dict[str, Any]] = {}
    prefix = "doc"
    counter = 0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"{self.prefix}{type(self).counter}"
        type(self).store[doc_id] = dict(data)
        return doc_id

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def set(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store[doc_id] = dict(data)

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        type(self).store.setdefault(doc_id, {}).update(data)

    async def delete(self, doc_id: str) -> None:
        type(self).store.pop(doc_id, None)

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]

    async def query(
        self,
        filters: list[tuple[str, str, Any]] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        results = [{"id": key, **value} for key, value in type(self).store.items()]
        for field, op, value in filters or []:
            if op == "==":
                results = [item for item in results if item.get(field) == value]
        return results[:limit] if limit else results


class _FakeStudentRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "student"
    counter = 0

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return await self.query(filters=[("programa_id", "==", programa_id)])


class _FakeAdvisorRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "advisor"
    counter = 0

    async def get_advisors_with_student_count(self) -> list[dict[str, Any]]:
        advisors = await self.list_all()
        students = await _FakeStudentRepository().list_all()
        for advisor in advisors:
            advisor["orientandos_ativos"] = sum(
                1 for student in students if student.get("orientador_id") == advisor["id"]
            )
        return advisors

    async def count_active_students(self, advisor_id: str) -> int:
        students = await _FakeStudentRepository().list_all()
        return sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in {"concluido", "desligado"}
        )


class _FakeProgramRepository(_FakeRepo):
    store: dict[str, dict[str, Any]] = {}
    prefix = "program"
    counter = 0

    async def get_config(self, programa_id: str) -> dict[str, Any] | None:
        return await self.get(programa_id)


class _FakeDepartmentRepository:
    """Fake de DepartmentRepository: nome fixo por teste (ou None por padrão)."""

    nome: str | None = None

    def __init__(self) -> None:
        pass

    async def get_nome_by_programa(self, programa_id: str | None) -> str | None:
        return type(self).nome if programa_id is not None else None


class _FakeWorkPlanRepository:
    """Fake do plano de trabalho: tasks por aluno definidas pelo teste."""

    tasks_by_student: dict[str, list[dict[str, Any]]] = {}

    def __init__(self) -> None:
        pass

    async def list_all_tasks_grouped(self) -> list[dict[str, Any]]:
        return [
            {"student_id": sid, "status": task.get("status")}
            for sid, tasks in type(self).tasks_by_student.items()
            for task in tasks
        ]

    async def get_all_tasks_for_student(self, student_id: str) -> list[dict[str, Any]]:
        return [dict(task) for task in type(self).tasks_by_student.get(student_id, [])]


class _FakeAuthService:
    async def create_invite(
        self,
        data: InviteRequest,
        current_user: CurrentUser,
        extra_fields: dict[str, Any] | None = None,
    ):
        return type("Invite", (), {"token": f"tok-{data.role}", "expira_em": "x"})()


class _FakeInferenceService:
    calls: list[tuple[str, str]] = []

    async def run_inference(self, student_id: str, programa_id: str):
        type(self).calls.append((student_id, programa_id))
        return type("InferenceResult", (), {"situacao_inferida": "qualificado"})()


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog", email="c@x.com")


def _advisor_user() -> CurrentUser:
    return CurrentUser(uid="uid-advisor", role="orientador", programa_id="prog", email="a@x.com")


def _student_user() -> CurrentUser:
    return CurrentUser(uid="uid-student", role="aluno", programa_id="prog", email="s@x.com")


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeStudentRepository.store = {}
    _FakeStudentRepository.counter = 0
    _FakeAdvisorRepository.store = {}
    _FakeAdvisorRepository.counter = 0
    _FakeProgramRepository.store = {}
    _FakeProgramRepository.counter = 0
    _FakeWorkPlanRepository.tasks_by_student = {}
    _FakeDepartmentRepository.nome = None
    _FakeInferenceService.calls = []
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(student_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(student_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(student_module, "ProgramRepository", _FakeProgramRepository)
    monkeypatch.setattr(student_module, "WorkPlanRepository", _FakeWorkPlanRepository)
    monkeypatch.setattr(advisor_module, "StudentRepository", _FakeStudentRepository)
    monkeypatch.setattr(advisor_module, "AdvisorRepository", _FakeAdvisorRepository)
    monkeypatch.setattr(advisor_module, "DepartmentRepository", _FakeDepartmentRepository)


async def test_create_student_usa_auto_id_e_retorna_invite_token() -> None:
    service = StudentService(auth_service=_FakeAuthService())
    data_ingresso = datetime(2024, 3, 31, tzinfo=timezone.utc)

    result = await service.create_student(
        StudentCreateRequest(
            nome="Aluno X",
            email="aluno@x.com",
            matricula="2024001",
            orientador_id="advisor1",
            nivel="mestrado",
            data_ingresso=data_ingresso,
            programa_id="prog",
        ),
        _coord(),
    )

    assert result["id"] == "student1"
    assert result["invite_token"] == "tok-aluno"
    assert "2024001" not in _FakeStudentRepository.store
    assert _FakeStudentRepository.store["student1"]["matricula"] == "2024001"
    assert _FakeStudentRepository.store["student1"]["prazo_final"] == datetime(
        2026,
        3,
        31,
        tzinfo=timezone.utc,
    )


async def test_create_student_usa_duracao_meses_do_programa() -> None:
    _FakeProgramRepository.store = {
        "programa_mestrado_30": {"duracao_meses": 30},
    }
    service = StudentService(auth_service=_FakeAuthService())

    await service.create_student(
        StudentCreateRequest(
            nome="Aluno 30",
            email="aluno30@x.com",
            matricula="2026001",
            orientador_id="advisor1",
            nivel="mestrado",
            data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc),
            programa_id="programa_mestrado_30",
        ),
        _coord(),
    )

    assert _FakeStudentRepository.store["student1"]["prazo_final"] == datetime(
        2028,
        7,
        1,
        tzinfo=timezone.utc,
    )


async def test_create_student_usa_fallback_quando_duracao_meses_ausente() -> None:
    _FakeProgramRepository.store = {
        "programa_sem_duracao": {"nome": "Programa sem duração"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    await service.create_student(
        StudentCreateRequest(
            nome="Aluno fallback",
            email="fallback@x.com",
            matricula="2026002",
            orientador_id="advisor1",
            nivel="mestrado",
            data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc),
            programa_id="programa_sem_duracao",
        ),
        _coord(),
    )

    assert _FakeStudentRepository.store["student1"]["prazo_final"] == datetime(
        2028,
        1,
        1,
        tzinfo=timezone.utc,
    )


async def test_orientador_cria_aluno_no_proprio_programa() -> None:
    service = StudentService(auth_service=_FakeAuthService())

    await service.create_student(
        StudentCreateRequest(
            nome="Aluno do orientador",
            email="orientando@x.com",
            matricula="2026003",
            orientador_id="advisor1",
            nivel="mestrado",
            data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc),
            programa_id="prog",
        ),
        _advisor_user(),
    )

    assert _FakeStudentRepository.store["student1"]["programa_id"] == "prog"


async def test_orientador_nao_cria_aluno_em_outro_programa() -> None:
    service = StudentService(auth_service=_FakeAuthService())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_student(
            StudentCreateRequest(
                nome="Aluno bloqueado",
                email="bloqueado@x.com",
                matricula="2026004",
                orientador_id="advisor1",
                nivel="mestrado",
                data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc),
                programa_id="outro_programa",
            ),
            _advisor_user(),
        )

    assert exc_info.value.status_code == 403
    assert _FakeStudentRepository.store == {}


async def test_list_students_orientador_filtra_por_auto_id_do_advisor() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
        "advisor2": {"uid": "outro", "nome": "Outro"},
    }
    _FakeStudentRepository.store = {
        "student1": {"nome": "Meu aluno", "orientador_id": "advisor1"},
        "student2": {"nome": "Outro aluno", "orientador_id": "advisor2"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.list_students(_advisor_user())

    assert [student["id"] for student in result] == ["student1"]


async def test_get_student_orientador_filtra_por_propriedade() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
        "advisor2": {"uid": "outro", "nome": "Outro"},
    }
    _FakeStudentRepository.store = {
        "student1": {"nome": "Meu aluno", "orientador_id": "advisor1"},
        "student2": {"nome": "Outro aluno", "orientador_id": "advisor2"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.get_student("student1", _advisor_user())

    assert result["id"] == "student1"

    with pytest.raises(HTTPException) as exc_info:
        await service.get_student("student2", _advisor_user())

    assert exc_info.value.status_code == 403


async def test_list_coauthor_candidates_ignora_escopo_de_papel_do_chamador() -> None:
    _FakeStudentRepository.store = {
        "student1": {"uid": "uid-student", "nome": "Aluno Chamador", "programa_id": "prog"},
        "student2": {"uid": "uid-outro", "nome": "Outro Aluno", "programa_id": "prog"},
        "student3": {"uid": None, "nome": "Convite pendente", "programa_id": "prog"},
        "student4": {"uid": "uid-fora", "nome": "Aluno de outro programa", "programa_id": "outro"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.list_coauthor_candidates(_student_user())

    assert {c["uid"] for c in result} == {"uid-student", "uid-outro"}


async def test_update_situacao_nao_grava_observacao_no_documento() -> None:
    _FakeStudentRepository.store = {
        "student1": {"nome": "Aluno", "situacao_registrada": "regular"},
    }
    service = StudentService(auth_service=_FakeAuthService())

    await service.update_situacao(
        "student1",
        SituacaoRequest(
            situacao_registrada="em_risco",
            observacao="Acompanhar no historico",
        ),
        _coord(),
    )

    assert _FakeStudentRepository.store["student1"]["situacao_registrada"] == "em_risco"
    assert "situacao_observacao" not in _FakeStudentRepository.store["student1"]


async def test_update_proficiencia_persiste_comprovante_e_recalcula_inferencia() -> None:
    _FakeStudentRepository.store = {
        "student1": {"nome": "Aluno", "programa_id": "prog"},
    }
    service = StudentService(
        auth_service=_FakeAuthService(),
        inference_service=_FakeInferenceService(),
    )

    result = await service.update_proficiencia(
        "student1",
        ProficienciaRequest(
            comprovada=True,
            data_proficiencia=datetime(2026, 4, 1, tzinfo=timezone.utc),
            comprovante_url="https://example.com/prof.pdf",
        ),
        _coord(),
    )

    student = _FakeStudentRepository.store["student1"]
    assert student["proficiencia_comprovada"] is True
    assert student["proficiencia_data"] == datetime(2026, 4, 1, tzinfo=timezone.utc)
    assert student["proficiencia_comprovante_url"] == "https://example.com/prof.pdf"
    assert _FakeInferenceService.calls == [("student1", "prog")]
    assert result["situacao_inferida_atualizada"] is True


async def test_update_qualificacao_persiste_comprovante_e_recalcula_inferencia() -> None:
    _FakeStudentRepository.store = {
        "student1": {"nome": "Aluno", "programa_id": "prog"},
    }
    service = StudentService(
        auth_service=_FakeAuthService(),
        inference_service=_FakeInferenceService(),
    )

    result = await service.update_qualificacao(
        "student1",
        QualificacaoRequest(
            aprovada=True,
            data_qualificacao=datetime(2026, 5, 1, tzinfo=timezone.utc),
            comprovante_url="https://example.com/qual.pdf",
        ),
        _coord(),
    )

    student = _FakeStudentRepository.store["student1"]
    assert student["qualificacao_aprovada"] is True
    assert student["qualificacao_data"] == datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert student["qualificacao_comprovante_url"] == "https://example.com/qual.pdf"
    assert _FakeInferenceService.calls == [("student1", "prog")]
    assert result["situacao_inferida_atualizada"] is True


async def test_create_advisor_usa_auto_id_e_retorna_invite_token() -> None:
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.create_advisor(
        AdvisorCreateRequest(
            nome="Orientador X",
            email="orientador@x.com",
            programa_id="prog",
        ),
        _coord(),
    )

    assert result["id"] == "advisor1"
    assert result["invite_token"] == "tok-orientador"
    assert "orientador@x.com" not in _FakeAdvisorRepository.store
    assert _FakeAdvisorRepository.store["advisor1"]["email"] == "orientador@x.com"


async def test_list_advisors_orientador_filtra_por_programa() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador", "programa_id": "prog"},
        "advisor2": {"uid": "outro", "nome": "Outro", "programa_id": "outro"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.list_advisors(_advisor_user())

    assert [advisor["id"] for advisor in result] == ["advisor1"]


async def test_list_advisors_coordenacao_inclui_convites_pendentes() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador", "programa_id": "prog"},
        "advisor2": {"uid": None, "nome": "Pendente", "programa_id": "prog"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.list_advisors(_coord())

    assert [advisor["id"] for advisor in result] == ["advisor1", "advisor2"]
    assert result[1]["uid"] == ""


async def test_list_advisors_nao_coordenacao_oculta_convites_pendentes() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador", "programa_id": "prog"},
        "advisor2": {"uid": None, "nome": "Pendente", "programa_id": "prog"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.list_advisors(_student_user())

    assert [advisor["id"] for advisor in result] == ["advisor1"]


async def test_get_advisor_retorna_orientandos_ativos() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador"},
    }
    _FakeStudentRepository.store = {
        "student1": {"orientador_id": "advisor1", "situacao_registrada": "regular"},
        "student2": {"orientador_id": "advisor1", "situacao_registrada": "concluido"},
        "student3": {"orientador_id": "advisor2", "situacao_registrada": "regular"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.get_advisor("advisor1")

    assert result["orientandos_ativos"] == 1


async def test_update_advisor_altera_nome_lattes_e_limite() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {
            "uid": "uid-advisor",
            "nome": "Nome Antigo",
            "email": "advisor@x.com",
            "departamento": "Computacao",
            "programa_id": "prog",
            "lattes": None,
            "limite_orientandos": 5,
        },
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.update_advisor(
        "advisor1",
        AdvisorUpdateRequest(
            nome="Nome Novo",
            lattes="https://lattes.cnpq.br/123",
            limite_orientandos=7,
        ),
        _coord(),
    )

    assert result["message"] == "Orientador atualizado"
    assert _FakeAdvisorRepository.store["advisor1"]["nome"] == "Nome Novo"
    assert _FakeAdvisorRepository.store["advisor1"]["lattes"] == "https://lattes.cnpq.br/123"
    assert _FakeAdvisorRepository.store["advisor1"]["limite_orientandos"] == 7
    assert _FakeAdvisorRepository.store["advisor1"]["departamento"] == "Computacao"


async def test_update_advisor_rejeita_limite_menor_que_orientandos_ativos() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {
            "uid": "uid-advisor",
            "nome": "Orientador",
            "email": "advisor@x.com",
            "departamento": "Computacao",
            "programa_id": "prog",
            "limite_orientandos": 5,
        },
    }
    _FakeStudentRepository.store = {
        "student1": {"orientador_id": "advisor1", "situacao_registrada": "regular"},
        "student2": {"orientador_id": "advisor1", "situacao_registrada": "em_risco"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    with pytest.raises(HTTPException) as exc_info:
        await service.update_advisor(
            "advisor1",
            AdvisorUpdateRequest(limite_orientandos=1),
            _coord(),
        )

    assert exc_info.value.status_code == 400
    assert _FakeAdvisorRepository.store["advisor1"]["limite_orientandos"] == 5


async def test_list_students_calcula_progresso_do_plano() -> None:
    """progresso_plano vem da fração de tasks concluídas; sem tasks é 0.0 (issue #317)."""
    _FakeStudentRepository.store = {
        "student1": {"nome": "Com plano", "orientador_id": "advisor1"},
        "student2": {"nome": "Sem plano", "orientador_id": "advisor1"},
    }
    _FakeWorkPlanRepository.tasks_by_student = {
        "student1": [
            {"status": "concluido"},
            {"status": "concluido"},
            {"status": "concluido"},
            {"status": "pendente"},
        ],
    }
    service = StudentService(auth_service=_FakeAuthService())

    result = await service.list_students(_coord())

    by_id = {student["id"]: student for student in result}
    assert by_id["student1"]["progresso_plano"] == 75.0
    assert by_id["student2"]["progresso_plano"] == 0.0


async def test_list_advisors_deriva_departamento_do_programa() -> None:
    """departamento vem do resolver programa_id -> departments, nao mais armazenado (issue #249)."""
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador", "programa_id": "prog"},
    }
    _FakeDepartmentRepository.nome = "Ciência da Computação"
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.list_advisors(_coord())

    assert result[0]["departamento"] == "Ciência da Computação"


async def test_get_advisor_deriva_departamento_do_programa() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Orientador", "programa_id": "prog"},
    }
    _FakeDepartmentRepository.nome = "Engenharia"
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.get_advisor("advisor1")

    assert result["departamento"] == "Engenharia"


async def test_coordenacao_provisionada_aparece_no_dropdown_do_orientador() -> None:
    """Issue #309: orientador vendo o dropdown já enxerga o coordenador-orientador."""
    service = AdvisorService(auth_service=_FakeAuthService())
    await service.ensure_advisor_for_coordenacao(
        {"uid": "coord1", "nome": "Coord", "email": "coord@x.com", "programa_id": "prog"}
    )

    result = await service.list_advisors(_advisor_user())

    assert [advisor["id"] for advisor in result] == ["coord1"]
    assert _FakeAdvisorRepository.store["coord1"]["uid"] == "coord1"


async def test_ensure_advisor_for_coordenacao_e_idempotente() -> None:
    service = AdvisorService(auth_service=_FakeAuthService())
    coordinator = {
        "uid": "coord1",
        "nome": "Coord",
        "email": "coord@x.com",
        "programa_id": "prog",
    }

    first = await service.ensure_advisor_for_coordenacao(coordinator)
    second = await service.ensure_advisor_for_coordenacao(coordinator)

    assert first == second == "coord1"
    assert list(_FakeAdvisorRepository.store.keys()) == ["coord1"]


async def test_list_advisors_nao_escreve_no_firestore() -> None:
    """M5: GET /advisors é leitura pura — não provisiona nem faz backfill."""
    service = AdvisorService(auth_service=_FakeAuthService())

    result = await service.list_advisors(_coord())

    assert result == []
    assert _FakeAdvisorRepository.store == {}


async def test_update_advisor_bloqueia_auto_gestao_da_coordenacao() -> None:
    _FakeAdvisorRepository.store = {
        "advisor-self": {"uid": "coord1", "nome": "Coord", "programa_id": "prog"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    with pytest.raises(HTTPException) as exc_info:
        await service.update_advisor(
            "advisor-self",
            AdvisorUpdateRequest(nome="Novo Nome"),
            _coord(),
        )

    assert exc_info.value.status_code == 403
    assert _FakeAdvisorRepository.store["advisor-self"]["nome"] == "Coord"


async def test_delete_advisor_bloqueia_auto_gestao_da_coordenacao() -> None:
    _FakeAdvisorRepository.store = {
        "advisor-self": {"uid": "coord1", "nome": "Coord", "programa_id": "prog"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_advisor("advisor-self", _coord())

    assert exc_info.value.status_code == 403
    assert "advisor-self" in _FakeAdvisorRepository.store


async def test_vincula_aluno_a_coordenador_orientador_como_qualquer_orientador() -> None:
    """Issue #309: um coordenador-orientador é um orientador válido para orientador_id."""
    advisor_service = AdvisorService(auth_service=_FakeAuthService())
    await advisor_service.ensure_advisor_for_coordenacao(
        {"uid": "coord1", "nome": "Coord", "email": "coord@x.com", "programa_id": "prog"}
    )
    advisors = await advisor_service.list_advisors(_advisor_user())
    coord_advisor_id = advisors[0]["id"]

    student_service = StudentService(auth_service=_FakeAuthService())
    result = await student_service.create_student(
        StudentCreateRequest(
            nome="Aluno Y",
            email="aluno-y@x.com",
            matricula="2026099",
            orientador_id=coord_advisor_id,
            nivel="mestrado",
            data_ingresso=datetime(2026, 1, 1, tzinfo=timezone.utc),
            programa_id="prog",
        ),
        _coord(),
    )

    assert _FakeStudentRepository.store[result["id"]]["orientador_id"] == coord_advisor_id


async def test_update_advisor_de_outro_orientador_continua_permitido() -> None:
    _FakeAdvisorRepository.store = {
        "advisor1": {"uid": "uid-advisor", "nome": "Antigo", "programa_id": "prog"},
    }
    service = AdvisorService(auth_service=_FakeAuthService())

    await service.update_advisor(
        "advisor1",
        AdvisorUpdateRequest(nome="Novo Nome"),
        _coord(),
    )

    assert _FakeAdvisorRepository.store["advisor1"]["nome"] == "Novo Nome"

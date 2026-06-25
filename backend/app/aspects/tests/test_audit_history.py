from __future__ import annotations

from typing import Any

import pytest

from backend.app.aspects import aspect_config
from backend.app.aspects import audit as audit_module
from backend.app.aspects import history as history_module
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser
from backend.app.models.user import ProfileUpdateRequest


class _AuditRepo:
    store: dict[str, dict[str, Any]] = {}
    counter = 0

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"log{type(self).counter}"
        self.store[doc_id] = dict(data)
        return doc_id


class _StudentRepo:
    documents: dict[str, dict[str, Any]] = {
        "s1": {"nome": "Aluno", "situacao_registrada": "regular"}
    }
    history: list[tuple[str, dict[str, Any]]] = []

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = self.documents.get(doc_id)
        return dict(data) if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        self.documents.setdefault(doc_id, {}).update(data)

    async def save_history_snapshot(
        self,
        student_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        self.history.append((student_id, dict(snapshot)))
        return "hist1"


class _TransferRepo:
    documents: dict[str, dict[str, Any]] = {
        "tr1": {"student_id": "s1", "status": "pendente"}
    }

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = self.documents.get(doc_id)
        return dict(data) if data else None


def _user() -> CurrentUser:
    return CurrentUser(
        uid="coord1",
        role="coordenacao",
        programa_id="prog_default",
        email="coord@x.com",
    )


async def test_audit_operation_registra_autoria_e_status_pt_br(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def operacao(user: CurrentUser) -> dict[str, str]:
        return {"ok": "sim"}

    assert await operacao(_user()) == {"ok": "sim"}

    assert list(_AuditRepo.store) == ["log1"]
    log = next(iter(_AuditRepo.store.values()))
    assert log["usuario_id"] == "coord1"
    assert log["role"] == "coordenacao"
    assert log["programa_id"] == "prog_default"
    assert log["operacao"] == "operacao"
    assert log["resultado_status"] == "sucesso"


async def test_audit_operation_captura_modulo_recurso_e_valor_entrada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def update_situacao(
        student_id: str,
        body: dict[str, str],
        user: CurrentUser,
    ) -> dict[str, str]:
        return {"id": student_id, "message": "ok"}

    await update_situacao("s1", {"situacao_registrada": "concluido"}, _user())

    log = next(iter(_AuditRepo.store.values()))
    assert log["modulo"] == update_situacao.__module__
    # recurso usa o primeiro argumento *_id encontrado nos argumentos capturados.
    assert log["recurso"].endswith("/s1")
    # valor_entrada captura os argumentos nomeados via inspect, exceto o CurrentUser.
    assert log["valor_entrada"]["student_id"] == "s1"
    assert log["valor_entrada"]["body"] == {"situacao_registrada": "concluido"}
    assert "user" not in log["valor_entrada"]


async def test_audit_operation_deriva_recurso_do_id_no_resultado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def create_something(body: dict[str, str], user: CurrentUser) -> dict[str, str]:
        return {"id": "novo123"}

    await create_something({"nome": "X"}, _user())

    log = next(iter(_AuditRepo.store.values()))
    assert log["recurso"].endswith("/novo123")


async def test_audit_operation_respeita_flag_desativada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def operacao(user: CurrentUser) -> str:
        return "ok"

    assert await operacao(_user()) == "ok"
    assert _AuditRepo.store == {}


async def test_audit_operation_registra_programa_id_em_erro(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def operacao(user: CurrentUser) -> None:
        raise ValueError("falha controlada")

    with pytest.raises(ValueError):
        await operacao(_user())

    log = next(iter(_AuditRepo.store.values()))
    assert log["programa_id"] == "prog_default"
    assert log["resultado_status"] == "erro"
    assert log["erro_mensagem"] == "falha controlada"


async def test_track_history_salva_snapshot_com_usuario_em_subcolecao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _StudentRepo.documents = {"s1": {"nome": "Aluno", "situacao_registrada": "regular"}}
    _StudentRepo.history = []
    monkeypatch.setattr(history_module, "StudentRepository", _StudentRepo)

    @track_history
    async def update_situacao(
        student_id: str,
        data: dict[str, str],
        user: CurrentUser,
    ) -> dict[str, str]:
        await _StudentRepo().update(student_id, data)
        return {"message": "ok"}

    await update_situacao("s1", {"situacao_registrada": "concluido"}, _user())

    student_id, snapshot = _StudentRepo.history[0]
    assert student_id == "s1"
    assert snapshot["entidade_tipo"] == "student"
    assert snapshot["entidade_id"] == "s1"
    assert snapshot["valor_anterior"]["situacao_registrada"] == "regular"
    assert snapshot["valor_novo"]["situacao_registrada"] == "concluido"
    assert snapshot["usuario_id"] == "coord1"
    assert snapshot["role"] == "coordenacao"
    assert snapshot["timestamp"] is not None


async def test_track_history_salva_observacao_no_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _StudentRepo.documents = {"s1": {"nome": "Aluno", "situacao_registrada": "regular"}}
    _StudentRepo.history = []
    monkeypatch.setattr(history_module, "StudentRepository", _StudentRepo)

    payload = type(
        "Payload",
        (),
        {"observacao": "Mudanca revisada pela coordenacao"},
    )()

    @track_history
    async def update_situacao(
        student_id: str,
        body,
        user: CurrentUser,
    ) -> dict[str, str]:
        await _StudentRepo().update(
            student_id,
            {"situacao_registrada": "em_risco"},
        )
        return {"message": "ok"}

    await update_situacao("s1", payload, _user())

    _, snapshot = _StudentRepo.history[0]
    assert snapshot["observacao"] == "Mudanca revisada pela coordenacao"


async def test_track_history_resolve_student_id_no_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _StudentRepo.documents = {"s1": {"nome": "Aluno", "orientador_id": "advisor1"}}
    _StudentRepo.history = []
    monkeypatch.setattr(history_module, "StudentRepository", _StudentRepo)

    payload = type(
        "Payload",
        (),
        {"student_id": "s1", "observacao": "Transferencia direta"},
    )()

    @track_history
    async def direct_transfer(
        body,
        user: CurrentUser,
    ) -> dict[str, str]:
        await _StudentRepo().update(
            body.student_id,
            {"orientador_id": "advisor2"},
        )
        return {"message": "ok"}

    await direct_transfer(payload, _user())

    student_id, snapshot = _StudentRepo.history[0]
    assert student_id == "s1"
    assert snapshot["valor_anterior"]["orientador_id"] == "advisor1"
    assert snapshot["valor_novo"]["orientador_id"] == "advisor2"
    assert snapshot["observacao"] == "Transferencia direta"


async def test_track_history_resolve_student_id_por_transfer_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _StudentRepo.documents = {"s1": {"nome": "Aluno", "orientador_id": "advisor1"}}
    _StudentRepo.history = []
    _TransferRepo.documents = {"tr1": {"student_id": "s1", "status": "pendente"}}
    monkeypatch.setattr(history_module, "StudentRepository", _StudentRepo)
    monkeypatch.setattr(history_module, "TransferRepository", _TransferRepo)

    @track_history
    async def approve_transfer(
        transfer_id: str,
        user: CurrentUser,
    ) -> dict[str, str]:
        await _StudentRepo().update(
            "s1",
            {"orientador_id": "advisor2"},
        )
        return {"message": "ok"}

    await approve_transfer("tr1", _user())

    student_id, snapshot = _StudentRepo.history[0]
    assert student_id == "s1"
    assert snapshot["valor_anterior"]["orientador_id"] == "advisor1"
    assert snapshot["valor_novo"]["orientador_id"] == "advisor2"


class _ActivityTypeRepo:
    documents: dict[str, dict[str, Any]] = {
        "type1": {"nome": "Disciplina", "pontuacao_base": 4.0}
    }
    history: list[tuple[str, dict[str, Any]]] = []

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = self.documents.get(doc_id)
        return dict(data) if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        self.documents.setdefault(doc_id, {}).update(data)

    async def save_history_snapshot(
        self,
        type_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        self.history.append((type_id, dict(snapshot)))
        return "hist1"


async def test_track_history_resolve_activity_type_por_type_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ActivityTypeRepo.documents = {"type1": {"nome": "Disciplina", "pontuacao_base": 4.0}}
    _ActivityTypeRepo.history = []
    monkeypatch.setattr(history_module, "ActivityTypeRepository", _ActivityTypeRepo)

    @track_history
    async def update_type(
        type_id: str,
        body: dict[str, float],
        user: CurrentUser,
    ) -> dict[str, str]:
        await _ActivityTypeRepo().update(type_id, body)
        return {"message": "ok"}

    await update_type("type1", {"pontuacao_base": 6.0}, _user())

    type_id, snapshot = _ActivityTypeRepo.history[0]
    assert type_id == "type1"
    assert snapshot["entidade_tipo"] == "activity_type"
    assert snapshot["entidade_id"] == "type1"
    assert snapshot["valor_anterior"]["pontuacao_base"] == 4.0
    assert snapshot["valor_novo"]["pontuacao_base"] == 6.0


async def test_audit_redige_campo_senha_em_valor_entrada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def trocar_senha(
        user_id: str,
        senha: str,
        user: CurrentUser,
    ) -> dict[str, str]:
        return {"ok": "sim"}

    await trocar_senha("u1", "s3cr3t!", _user())

    log = next(iter(_AuditRepo.store.values()))
    assert log["valor_entrada"]["user_id"] == "u1"
    assert log["valor_entrada"]["senha"] == "***"


async def test_audit_redige_campo_token_em_payload_aninhado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _AuditRepo.store = {}
    _AuditRepo.counter = 0
    monkeypatch.setattr(audit_module, "FirebaseRepository", _AuditRepo)

    @audit_operation
    async def ativar_conta(
        payload: dict[str, Any],
        user: CurrentUser,
    ) -> dict[str, str]:
        return {"ok": "sim"}

    await ativar_conta({"email": "a@b.com", "token": "abc123"}, _user())

    log = next(iter(_AuditRepo.store.values()))
    assert log["valor_entrada"]["payload"]["email"] == "a@b.com"
    assert log["valor_entrada"]["payload"]["token"] == "***"


class _UsersRepo:
    documents: dict[str, dict[str, Any]] = {}
    history: list[tuple[str, dict[str, Any]]] = []

    def __init__(self, collection: str) -> None:
        self.collection = collection

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = self.documents.get(doc_id)
        return dict(data) if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        self.documents.setdefault(doc_id, {}).update(data)

    async def save_history_snapshot(
        self,
        doc_id: str,
        snapshot: dict[str, Any],
    ) -> str:
        self.history.append((doc_id, dict(snapshot)))
        return "hist1"


async def test_track_history_resolve_perfil_do_usuario(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _UsersRepo.documents = {"coord1": {"uid": "coord1", "nome": "Antigo"}}
    _UsersRepo.history = []
    monkeypatch.setattr(history_module, "FirebaseRepository", _UsersRepo)

    @track_history
    async def update_profile(
        body: ProfileUpdateRequest,
        user: CurrentUser,
    ) -> dict[str, str]:
        await _UsersRepo("users").update(user.uid, {"nome": body.nome})
        return {"message": "ok"}

    await update_profile(ProfileUpdateRequest(nome="Novo"), _user())

    doc_id, snapshot = _UsersRepo.history[0]
    assert doc_id == "coord1"
    assert snapshot["entidade_tipo"] == "user"
    assert snapshot["entidade_id"] == "coord1"
    assert snapshot["valor_anterior"]["nome"] == "Antigo"
    assert snapshot["valor_novo"]["nome"] == "Novo"
    assert snapshot["usuario_id"] == "coord1"


async def test_track_history_respeita_flag_desativada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _StudentRepo.history = []
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)
    monkeypatch.setattr(history_module, "StudentRepository", _StudentRepo)

    @track_history
    async def update_situacao(student_id: str) -> str:
        return student_id

    assert await update_situacao("s1") == "s1"
    assert _StudentRepo.history == []

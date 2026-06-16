from __future__ import annotations

from typing import Any

import pytest

from backend.app.aspects import aspect_config
from backend.app.aspects import audit as audit_module
from backend.app.aspects import history as history_module
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.history import track_history
from backend.app.core.auth import CurrentUser


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

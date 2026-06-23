"""Testes de comportamento para CrossProgramTransferService.

Padrao do projeto: _FakeRepo concreto + monkeypatch.setattr no modulo.
Sem AsyncMock/patch — igual ao test_transfer_service.py existente.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.services.transfer_cross import CrossProgramTransferService


# ------------------------------------------------------------------
# Fakes
# ------------------------------------------------------------------

class _FakeAdvisorRepo:
    def __init__(self, capacity: bool = True) -> None:
        self._capacity = capacity
        self._store: dict[str, dict] = {
            "ori-origem": {
                "id": "ori-origem",
                "uid": "uid-origem",
                "nome": "Prof Origem",
                "programa_id": "prog-A",
            },
            "ori-destino": {
                "id": "ori-destino",
                "uid": "uid-destino",
                "nome": "Prof Destino",
                "programa_id": "prog-B",
            },
            "ori-b-same": {
                "id": "ori-b-same",
                "uid": "uid-b-same",
                "nome": "Prof Same",
                "programa_id": "prog-A",
            },
        }

    async def get(self, advisor_id: str) -> dict | None:
        return self._store.get(advisor_id)

    async def check_advisor_capacity(self, advisor_id: str) -> bool:
        return self._capacity


class _FakeStudentRepo:
    def __init__(self, situacao: str = "regular") -> None:
        self._store: dict[str, dict] = {
            "aluno-1": {
                "id": "aluno-1",
                "nome": "Aluno Teste",
                "uid": "uid-aluno",
                "orientador_id": "ori-origem",
                "programa_id": "prog-A",
                "situacao_registrada": situacao,
                "coorientador_id": None,
            }
        }
        self.updated: dict[str, dict] = {}

    async def get(self, student_id: str) -> dict | None:
        return self._store.get(student_id)

    async def update(self, student_id: str, data: dict) -> None:
        self.updated[student_id] = data
        if student_id in self._store:
            self._store[student_id].update(data)


class _FakeTransferRepo:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._counter = 0
        self._pending: dict | None = None

    async def get(self, transfer_id: str) -> dict | None:
        return self._store.get(transfer_id)

    async def create_request(self, data: dict) -> str:
        self._counter += 1
        tid = f"transfer-{self._counter}"
        self._store[tid] = {"id": tid, **data}
        return tid

    async def get_pending_by_student(self, student_id: str) -> dict | None:
        return self._pending

    async def list_all(self) -> list[dict]:
        return list(self._store.values())

    async def update_status(self, transfer_id: str, data: dict) -> None:
        if transfer_id in self._store:
            self._store[transfer_id].update(data)

    async def approve(self, transfer_id: str, data: dict) -> None:
        await self.update_status(transfer_id, {"status": "aprovada", **data})

    async def reject(self, transfer_id: str, data: dict) -> None:
        await self.update_status(transfer_id, {"status": "rejeitada", **data})


class _FakeInferenceService:
    def __init__(self) -> None:
        self.called_for: list[str] = []

    async def evaluate_student(self, student_id: str) -> Any:
        self.called_for.append(student_id)


class _FakeUser:
    def __init__(self, programa_id: str = "prog-A") -> None:
        self.uid = "uid-coord"
        self.role = "coordenacao"
        self.programa_id = programa_id


# ------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------

def _setup(
    monkeypatch: pytest.MonkeyPatch,
    situacao: str = "regular",
    capacity: bool = True,
) -> tuple[CrossProgramTransferService, _FakeStudentRepo, _FakeTransferRepo, _FakeInferenceService]:
    s_repo = _FakeStudentRepo(situacao=situacao)
    t_repo = _FakeTransferRepo()
    a_repo = _FakeAdvisorRepo(capacity=capacity)
    inf = _FakeInferenceService()

    svc = CrossProgramTransferService()
    monkeypatch.setattr(svc, "_students", s_repo)
    monkeypatch.setattr(svc, "_transfers", t_repo)
    monkeypatch.setattr(svc, "_advisors", a_repo)

    return svc, s_repo, t_repo, inf


# ------------------------------------------------------------------
# Cenário 1 — Fluxo feliz cross-program
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_cross_inicia_em_pendente_origem(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user = _FakeUser(programa_id="prog-A")

    result = await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Mudanca de linha de pesquisa",
        user=user,
    )

    assert result["status"] == "pendente_origem"
    assert result["tipo"] == "cross_program"
    stored = list(t_repo._store.values())[0]
    assert stored["status"] == "pendente_origem"
    assert stored["programa_destino_id"] == "prog-B"


@pytest.mark.asyncio
async def test_approve_origin_avanca_para_pendente_destino(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user_origem = _FakeUser(programa_id="prog-A")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user_origem,
    )
    transfer_id = list(t_repo._store.keys())[0]

    result = await svc.approve_origin(transfer_id, user_origem)

    assert result["status"] == "pendente_destino"
    assert t_repo._store[transfer_id]["status"] == "pendente_destino"


@pytest.mark.asyncio
async def test_approve_destination_efetiva_migracao_e_chama_inferencia(monkeypatch):
    svc, s_repo, t_repo, inf = _setup(monkeypatch)
    user_origem = _FakeUser(programa_id="prog-A")
    user_destino = _FakeUser(programa_id="prog-B")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user_origem,
    )
    transfer_id = list(t_repo._store.keys())[0]
    await svc.approve_origin(transfer_id, user_origem)

    result = await svc.approve_destination(transfer_id, user_destino, inf)

    assert result["status"] == "aprovada"
    assert s_repo.updated["aluno-1"]["programa_id"] == "prog-B"
    assert s_repo.updated["aluno-1"]["orientador_id"] == "ori-destino"
    assert "aluno-1" in inf.called_for


# ------------------------------------------------------------------
# Cenário 2 — Rejeição na etapa de origem
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rejeicao_em_pendente_origem(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user = _FakeUser(programa_id="prog-A")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user,
    )
    transfer_id = list(t_repo._store.keys())[0]

    result = await svc.reject_request(transfer_id, "Aluno nao apto", user)

    assert result["status"] == "rejeitada"
    assert result["motivo"] == "Aluno nao apto"
    assert t_repo._store[transfer_id]["status"] == "rejeitada"


@pytest.mark.asyncio
async def test_rejeicao_sem_motivo_levanta_422(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user = _FakeUser(programa_id="prog-A")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user,
    )
    transfer_id = list(t_repo._store.keys())[0]

    with pytest.raises(HTTPException) as exc:
        await svc.reject_request(transfer_id, "   ", user)
    assert exc.value.status_code == 422


# ------------------------------------------------------------------
# Cenário 3 — Rejeição na etapa de destino
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rejeicao_em_pendente_destino(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user_a = _FakeUser(programa_id="prog-A")
    user_b = _FakeUser(programa_id="prog-B")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user_a,
    )
    transfer_id = list(t_repo._store.keys())[0]
    await svc.approve_origin(transfer_id, user_a)

    result = await svc.reject_request(transfer_id, "Sem vagas no programa", user_b)

    assert result["status"] == "rejeitada"
    assert t_repo._store[transfer_id]["status"] == "rejeitada"


# ------------------------------------------------------------------
# Cenário 4 — Bloqueios de integridade
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aluno_desligado_nao_pode_ser_transferido(monkeypatch):
    svc, _, _, _ = _setup(monkeypatch, situacao="desligado")
    user = _FakeUser()

    with pytest.raises(HTTPException) as exc:
        await svc.create_request(
            student_id="aluno-1",
            orientador_destino_id="ori-destino",
            programa_destino_id="prog-B",
            motivo="Motivo valido",
            user=user,
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_capacidade_excedida_bloqueia_aprovacao_destino(monkeypatch):
    svc, _, t_repo, inf = _setup(monkeypatch, capacity=False)
    user_a = _FakeUser(programa_id="prog-A")
    user_b = _FakeUser(programa_id="prog-B")

    await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-destino",
        programa_destino_id="prog-B",
        motivo="Motivo valido",
        user=user_a,
    )
    transfer_id = list(t_repo._store.keys())[0]
    await svc.approve_origin(transfer_id, user_a)

    with pytest.raises(HTTPException) as exc:
        await svc.approve_destination(transfer_id, user_b, inf)
    assert exc.value.status_code == 400
    assert "aluno-1" not in inf.called_for


# ------------------------------------------------------------------
# Cenário 5 — Same-program colapsa para 1 passo
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_same_program_colapsa_para_pendente(monkeypatch):
    svc, _, t_repo, _ = _setup(monkeypatch)
    user = _FakeUser(programa_id="prog-A")

    result = await svc.create_request(
        student_id="aluno-1",
        orientador_destino_id="ori-b-same",
        programa_destino_id="prog-A",
        motivo="Troca de orientador",
        user=user,
    )

    assert result["status"] == "pendente"
    assert result["tipo"] == "same_program"
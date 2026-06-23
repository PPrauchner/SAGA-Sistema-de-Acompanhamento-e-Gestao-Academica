# backend/app/tests/test_transfer_cross.py
import pytest
from fastapi import HTTPException
from backend.app.services.transfer_cross import CrossProgramTransferService
from backend.app.models.transfer_cross import TransferRequestCreate

class FakeRepo:
    def __init__(self):
        self.storage = {}
        self.pending = False
        self.advising_count = 0
    async def get_by_id(self, uid): return self.storage.get(uid)
    async def save(self, payload):
        payload["id"] = "trans_123"
        self.storage["trans_123"] = payload
        return payload
    async def update(self, uid, updates):
        self.storage[uid].update(updates)
        return self.storage[uid]
    async def has_pending_request(self, sid): return self.pending
    async def get_active_advising_count(self, oid): return self.advising_count

class FakeStudentRepo:
    def __init__(self):
        self.students = {
            "aluno_ativo": {"orientador_id": "prof_antigo", "programa_id": "matriz_antiga", "situacao_registrada": "regular"},
            "aluno_desligado": {"orientador_id": "prof_antigo", "programa_id": "matriz_antiga", "situacao_registrada": "desligado"}
        }
    async def get_by_id(self, uid): return self.students.get(uid)
    async def update(self, uid, updates): self.students[uid].update(updates)

class FakeInferenceService:
    async def evaluate_student(self, student_id: str): pass

class FakeUser:
    def __init__(self): self.uid = "coord_01"

@pytest.mark.asyncio
async def test_fluxo_cross_program_dupla_aprovacao_sucesso():
    repo = FakeRepo()
    s_repo = FakeStudentRepo()
    inf_service = FakeInferenceService()
    service = CrossProgramTransferService(transfer_repo=repo, student_repo=s_repo, inference_service=inf_service)
    user = FakeUser()

    payload = TransferRequestCreate(
        student_id="aluno_ativo",
        orientador_destino_id="prof_novo",
        programa_origem_id="matriz_antiga",
        programa_destino_id="matriz_nova"
    )

    req = await service.create_request(payload, user)
    assert req["status"] == "pendente_origem"

    req = await service.approve_origin_stage("trans_123", "coord_origem")
    assert req["status"] == "pendente_destino"

    req = await service.approve_destination_stage("trans_123", "coord_destino")
    assert req["status"] == "aprovada"

    aluno_atualizado = await s_repo.get_by_id("aluno_ativo")
    assert aluno_atualizado["programa_id"] == "matriz_nova"
    assert aluno_atualizado["orientador_id"] == "prof_novo"
    assert aluno_atualizado["coorientador_id"] is None
    
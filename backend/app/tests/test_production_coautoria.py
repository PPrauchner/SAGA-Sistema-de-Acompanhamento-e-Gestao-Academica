"""Teste de integração — fan-out de atividade para cada co-autor cadastrado (issue #310).

Exercita ProductionService.create_production com repositórios reais (StudentRepository,
ActivityRepository, VehicleRepository, ProductionRepository) contra um FakeFirestore
compartilhado, em vez dos fakes-de-serviço usados em services/tests/test_production_service.py
— prova que a resolução de co-autores enxerga alunos além do próprio autor que registra
(comportamento que StudentService.list_students(user), por ser escopado à visibilidade do
papel do chamador, não garante para um usuário 'aluno').
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.core.auth import CurrentUser
from backend.app.models.production import ProductionCreate
from backend.app.repositories import activity_repository, firebase_repository
from backend.app.services.production_service import ProductionService
from backend.app.tests.fake_firestore import FakeFirestore


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeFirestore:
    fake = FakeFirestore()
    monkeypatch.setattr(firebase_repository, "get_firestore_client", lambda: fake)
    monkeypatch.setattr(activity_repository, "get_firestore_client", lambda: fake)
    return fake


def _seed_student(
    fake_db: FakeFirestore,
    student_id: str,
    uid: str,
    nome: str,
    programa_id: str = "prog1",
) -> None:
    fake_db.collection("students").document(student_id).set(
        {
            "uid": uid,
            "nome": nome,
            "orientador_id": "adv1",
            "programa_id": programa_id,
            "situacao_registrada": "regular",
        }
    )


def _seed_vehicle_level(
    fake_db: FakeFirestore,
    programa_id: str,
    veiculo_id: str,
    nivel: str = "A1",
    peso: float = 1.0,
) -> None:
    fake_db.collection("programs").document(programa_id).collection("vehicle_levels").document(
        veiculo_id
    ).set({"veiculo_id": veiculo_id, "nivel": nivel, "peso": peso})


def _payload(autores: list[str]) -> ProductionCreate:
    return ProductionCreate(
        titulo="Artigo em coautoria",
        veiculo_id="veic1",
        tipo_producao="artigo",
        status_publicacao="publicado",
        autores=autores,
        data_realizacao=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


async def test_cada_coautor_cadastrado_recebe_sua_propria_activity(
    fake_db: FakeFirestore,
) -> None:
    _seed_student(fake_db, "student_a", "uid-a", "Autora A")
    _seed_student(fake_db, "student_b", "uid-b", "Autor B")
    _seed_vehicle_level(fake_db, "prog1", "veic1")

    service = ProductionService()
    user = CurrentUser(uid="uid-a", role="aluno", programa_id="prog1", email="a@saga.edu")

    result = await service.create_production(_payload(autores=["uid-b"]), user)

    activities_a = (
        fake_db.collection("students").document("student_a").collection("activities").stream()
    )
    activities_b = (
        fake_db.collection("students").document("student_b").collection("activities").stream()
    )
    docs_a = [snap.to_dict() for snap in activities_a]
    docs_b = [snap.to_dict() for snap in activities_b]

    assert len(docs_a) == 1
    assert len(docs_b) == 1  # co-autor cadastrado recebe sua própria cópia
    assert docs_a[0]["producao_id"] == result["id"]
    assert docs_b[0]["producao_id"] == result["id"]
    assert docs_a[0]["creditos_gerados"] == docs_b[0]["creditos_gerados"]  # crédito cheio, sem rateio


async def test_autor_externo_nao_registrado_nao_gera_activity(fake_db: FakeFirestore) -> None:
    _seed_student(fake_db, "student_a", "uid-a", "Autora A")
    _seed_vehicle_level(fake_db, "prog1", "veic1")

    service = ProductionService()
    user = CurrentUser(uid="uid-a", role="aluno", programa_id="prog1", email="a@saga.edu")

    result = await service.create_production(
        _payload(autores=["Fulano Externo"]), user
    )

    producao = fake_db.collection("productions").document(result["id"]).get().to_dict()
    assert "Fulano Externo" in producao["autores"]

    activities_a = list(
        fake_db.collection("students").document("student_a").collection("activities").stream()
    )
    assert len(activities_a) == 1  # só o autor cadastrado (quem registra) recebe activity

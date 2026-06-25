from __future__ import annotations

import pytest

from backend.app.repositories import firebase_repository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.tests.fake_firestore import FakeFirestore


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch) -> FakeFirestore:
    db = FakeFirestore()
    monkeypatch.setattr(firebase_repository, "get_firestore_client", lambda: db)
    return db


async def test_list_by_ids_normaliza_apenas_producoes_solicitadas(fake_db: FakeFirestore) -> None:
    fake_db.collection("productions").document("prod_1").set(
        {
            "titulo": "Artigo A",
            "veiculo_id": "veic_1",
            "tipo_producao": "artigo",
            "autores": ["uid-aluno"],
            "pontuacao_calculada": "4.5",
            "programa_id": "prog",
        }
    )
    fake_db.collection("productions").document("prod_2").set(
        {
            "titulo": "Artigo B",
            "veiculo_id": "veic_2",
            "tipo_producao": "artigo",
            "autores": ["uid-aluno"],
            "pontuacao_calculada": 2,
            "programa_id": "prog",
        }
    )
    fake_db.collection("programs/prog/vehicle_levels").document("nivel_1").set(
        {"veiculo_id": "veic_1", "nivel": "A1"}
    )

    result = await ProductionRepository().list_by_ids({"prod_1", "prod_inexistente"})

    assert result == [
        {
            "id": "prod_1",
            "titulo": "Artigo A",
            "veiculo_id": "veic_1",
            "tipo_producao": "artigo",
            "autores": ["uid-aluno"],
            "pontuacao_calculada": 4.5,
            "nivel": "A1",
            "programa_id": "prog",
        }
    ]

"""
Testes de InferenceRepository — mapeamento das coleções do Firestore ao contrato do motor.

- get_approved_activities: students/{id}/activities/ + activity_types/ (RL02). Corrige o stub
  que sempre retornava [] (issue #306): a re-execução do motor após qualquer mudança em
  atividades (aprovação, exclusão) agora reflete créditos reais.
- get_student: normalização do documento do aluno, incluindo as URLs de comprovante de
  proficiência e qualificação consumidas pelo checklist (issue #343).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.app.repositories.inference_repository import InferenceRepository


@pytest.fixture
def repo() -> InferenceRepository:
    instance = InferenceRepository()
    instance._activities = AsyncMock()
    instance._activity_types = AsyncMock()
    instance._students = AsyncMock()
    return instance


async def test_get_student_devolve_comprovantes_registrados(repo: InferenceRepository) -> None:
    repo._students.get.return_value = {
        "nome": "Aluna",
        "programa_id": "prog1",
        "proficiencia_comprovante_url": "https://x/prof.pdf",
        "qualificacao_comprovante_url": "https://x/qual.pdf",
    }

    student = await repo.get_student("s1")

    assert student["proficiencia_comprovante_url"] == "https://x/prof.pdf"
    assert student["qualificacao_comprovante_url"] == "https://x/qual.pdf"


async def test_get_student_comprovantes_none_quando_ausentes(repo: InferenceRepository) -> None:
    repo._students.get.return_value = {"nome": "Aluno", "programa_id": "prog1"}

    student = await repo.get_student("s1")

    assert student["proficiencia_comprovante_url"] is None
    assert student["qualificacao_comprovante_url"] is None


async def test_mapeia_atividade_aprovada_com_creditos_gerados(repo: InferenceRepository) -> None:
    repo._activities.list_by_student.return_value = [
        {
            "id": "act1",
            "tipo_id": "t1",
            "status": "aprovado",
            "creditos_gerados": 4.0,
            "creditos_concedidos": None,
            "comprovante_url": "https://x/comprovante.pdf",
            "data_realizacao": "2026-01-15",
        }
    ]
    repo._activity_types.list_all.return_value = [
        {"id": "t1", "categoria": "basico", "ativo": True}
    ]

    result = await repo.get_approved_activities("s1")

    assert result == [
        {
            "id": "act1",
            "grupo": "basico",
            "creditos": 4.0,
            "comprovante": "https://x/comprovante.pdf",
            "tipo_ativo": True,
            "data": "2026-01-15",
        }
    ]


async def test_creditos_concedidos_tem_precedencia_sobre_gerados(repo: InferenceRepository) -> None:
    repo._activities.list_by_student.return_value = [
        {
            "id": "act1",
            "tipo_id": "t1",
            "status": "aprovado",
            "creditos_gerados": 4.0,
            "creditos_concedidos": 2.5,
            "comprovante_url": None,
            "data_realizacao": "2026-01-15",
        }
    ]
    repo._activity_types.list_all.return_value = [
        {"id": "t1", "categoria": "basico", "ativo": True}
    ]

    result = await repo.get_approved_activities("s1")

    assert result[0]["creditos"] == 2.5
    assert result[0]["comprovante"] is None


async def test_ignora_atividades_nao_aprovadas(repo: InferenceRepository) -> None:
    repo._activities.list_by_student.return_value = [
        {"id": "act1", "tipo_id": "t1", "status": "enviado", "creditos_gerados": 4.0},
        {"id": "act2", "tipo_id": "t1", "status": "rejeitado", "creditos_gerados": 4.0},
    ]
    repo._activity_types.list_all.return_value = [
        {"id": "t1", "categoria": "basico", "ativo": True}
    ]

    assert await repo.get_approved_activities("s1") == []


async def test_lista_vazia_quando_aluno_sem_atividades(repo: InferenceRepository) -> None:
    repo._activities.list_by_student.return_value = []
    repo._activity_types.list_all.return_value = []

    assert await repo.get_approved_activities("s1") == []

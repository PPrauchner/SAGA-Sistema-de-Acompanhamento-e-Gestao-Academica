from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.activity_type import (
    ActivityTypeCreateRequest,
    ActivityTypeToggleRequest,
    ActivityTypeUpdateRequest,
)
from backend.app.services import activity_type_service as activity_type_module
from backend.app.services.activity_type_service import ActivityTypeService


class _FakeActivityTypeRepository:
    store: dict[str, dict[str, Any]] = {}
    counter = 0

    async def create(self, data: dict[str, Any]) -> str:
        type(self).counter += 1
        doc_id = f"type{type(self).counter}"
        type(self).store[doc_id] = dict(data)
        return doc_id

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        data = type(self).store.get(doc_id)
        return dict(data) if data else None

    async def update(self, doc_id: str, data: dict[str, Any]) -> None:
        if not data:
            # Espelha o google-cloud-firestore real: update({}) levanta ValueError.
            raise ValueError("Cannot update with an empty document.")
        type(self).store.setdefault(doc_id, {}).update(data)

    async def list_all(self) -> list[dict[str, Any]]:
        return [{"id": key, **value} for key, value in type(self).store.items()]


def _coord() -> CurrentUser:
    return CurrentUser(uid="coord1", role="coordenacao", programa_id="prog", email="c@x.com")


@pytest.fixture(autouse=True)
def _setup(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeActivityTypeRepository.store = {}
    _FakeActivityTypeRepository.counter = 0
    monkeypatch.setattr(
        activity_type_module, "ActivityTypeRepository", _FakeActivityTypeRepository
    )


async def test_create_type_usa_auto_id_e_marca_ativo_por_padrao() -> None:
    service = ActivityTypeService()

    result = await service.create_type(
        ActivityTypeCreateRequest(
            nome="Publicação em periódico",
            categoria="especifico",
            pontuacao_base=10.0,
        ),
        _coord(),
    )

    assert result["id"] == "type1"
    stored = _FakeActivityTypeRepository.store["type1"]
    assert stored["ativo"] is True
    assert stored["categoria"] == "especifico"
    # M1: metadados de autoria/tenant/timestamps gravados no create
    assert stored["programa_id"] == "prog"
    assert stored["criado_por"] == "coord1"
    assert "criado_em" in stored and "atualizado_em" in stored


async def test_update_type_atualiza_apenas_campos_informados() -> None:
    _FakeActivityTypeRepository.store = {
        "type1": {
            "nome": "Disciplina",
            "categoria": "basico",
            "pontuacao_base": 4.0,
            "limite_maximo_creditos": None,
            "exige_comprovante": True,
            "permite_multiplas": True,
            "ativo": True,
        },
    }
    service = ActivityTypeService()

    result = await service.update_type(
        "type1",
        ActivityTypeUpdateRequest(pontuacao_base=6.0),
        _coord(),
    )

    assert result["historico_criado"] is True
    assert _FakeActivityTypeRepository.store["type1"]["pontuacao_base"] == 6.0
    assert _FakeActivityTypeRepository.store["type1"]["nome"] == "Disciplina"


async def test_update_type_so_com_observacao_nao_chama_update_vazio() -> None:
    _FakeActivityTypeRepository.store = {
        "type1": {"nome": "Disciplina", "categoria": "basico", "pontuacao_base": 4.0},
    }
    service = ActivityTypeService()

    result = await service.update_type(
        "type1",
        ActivityTypeUpdateRequest(observacao="Apenas justificando, sem alterar campos"),
        _coord(),
    )

    assert result["historico_criado"] is True
    assert _FakeActivityTypeRepository.store["type1"]["pontuacao_base"] == 4.0


async def test_update_type_inexistente_lanca_404() -> None:
    service = ActivityTypeService()

    with pytest.raises(HTTPException) as exc_info:
        await service.update_type(
            "inexistente",
            ActivityTypeUpdateRequest(pontuacao_base=1.0),
            _coord(),
        )

    assert exc_info.value.status_code == 404


async def test_toggle_active_desativa_tipo() -> None:
    _FakeActivityTypeRepository.store = {
        "type1": {"nome": "Estágio docência", "categoria": "tecnologico", "ativo": True},
    }
    service = ActivityTypeService()

    result = await service.toggle_active(
        "type1",
        ActivityTypeToggleRequest(ativo=False),
        _coord(),
    )

    assert result["message"] == "Tipo desativado"
    assert _FakeActivityTypeRepository.store["type1"]["ativo"] is False


async def test_list_types_retorna_todos_independente_de_papel() -> None:
    _FakeActivityTypeRepository.store = {
        "type1": {"nome": "Disciplina", "ativo": True},
        "type2": {"nome": "Banca", "ativo": False},
    }
    service = ActivityTypeService()

    result = await service.list_types()

    assert {item["id"] for item in result} == {"type1", "type2"}

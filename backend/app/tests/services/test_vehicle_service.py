"""
Testes para VehicleService — métricas descritivas do veículo (US-VQ04/VQ05).

Responsabilidades:
- Verificar a persistência de indice_h, percentil_scopus e jcr no create_vehicle.
- Garantir que JCR só é aceito para veículo do tipo 'revista'.
- Garantir que list_vehicles devolve as métricas (None quando ausentes).
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.app.core.auth import CurrentUser
from backend.app.models.vehicle import VehicleCreate
from backend.app.services.vehicle_service import VehicleService


@pytest.fixture
def user():
    """Coordenação do programa default."""
    return CurrentUser(
        uid="coord", role="coordenacao", programa_id="prog_default", email="c@saga.edu"
    )


@pytest.fixture
def service():
    """VehicleService com repositório mockado."""
    svc = VehicleService()
    svc._vehicles = AsyncMock()
    return svc


async def test_create_revista_persiste_metricas(service, user):
    """Deve gravar indice_h, percentil_scopus e jcr no doc do veículo revista."""
    service._vehicles.create.return_value = "vec_1"

    result = await service.create_vehicle(
        VehicleCreate(
            nome="Rev X",
            tipo="revista",
            nivel="A1",
            indice_h=12,
            percentil_scopus=90,
            jcr=3.5,
        ),
        user,
    )

    assert result["id"] == "vec_1"
    saved = service._vehicles.create.call_args.args[0]
    assert saved["indice_h"] == 12
    assert saved["percentil_scopus"] == 90
    assert saved["jcr"] == 3.5


async def test_create_evento_com_jcr_rejeitado(service, user):
    """Deve recusar (422) jcr em veículo do tipo 'evento' e não gravar nada."""
    with pytest.raises(HTTPException) as exc:
        await service.create_vehicle(
            VehicleCreate(nome="Ev Y", tipo="evento", nivel="SC", jcr=2.0),
            user,
        )

    assert exc.value.status_code == 422
    service._vehicles.create.assert_not_called()


async def test_create_evento_sem_jcr_permitido(service, user):
    """Deve aceitar evento com indice_h/percentil_scopus mas sem jcr."""
    service._vehicles.create.return_value = "vec_2"

    result = await service.create_vehicle(
        VehicleCreate(nome="Ev Z", tipo="evento", nivel="SC", indice_h=5),
        user,
    )

    assert result["id"] == "vec_2"
    saved = service._vehicles.create.call_args.args[0]
    assert saved["indice_h"] == 5
    assert saved["jcr"] is None


async def test_list_vehicles_inclui_metricas(service, user):
    """Deve devolver as métricas; ausentes viram None."""
    service._vehicles.list_all.return_value = [
        {
            "id": "vec_1",
            "nome": "Rev X",
            "tipo": "revista",
            "programa_id": "prog_default",
            "indice_h": 12,
            "percentil_scopus": 90,
            "jcr": 3.5,
        },
        {
            "id": "vec_2",
            "nome": "Ev Z",
            "tipo": "evento",
            "programa_id": "prog_default",
        },
    ]
    service._vehicles.list_levels.return_value = []

    result = await service.list_vehicles(user)
    by_id = {v["id"]: v for v in result}

    assert by_id["vec_1"]["indice_h"] == 12
    assert by_id["vec_1"]["percentil_scopus"] == 90
    assert by_id["vec_1"]["jcr"] == 3.5
    assert by_id["vec_2"]["indice_h"] is None
    assert by_id["vec_2"]["percentil_scopus"] is None
    assert by_id["vec_2"]["jcr"] is None

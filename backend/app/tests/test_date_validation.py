"""
Testes dos validators de intervalo de data aplicados aos schemas de entrada.

Cobre:
- DataFutura (prorrogação): aceita futuro até hoje + 10 anos; rejeita datas
  anteriores a 2000-01-01 e além do máximo.
- DataEventoRealizacao (atividade/produção): aceita apenas eventos já
  ocorridos; rejeita datas no futuro e anteriores a 2000-01-01.
- Schemas de resposta não são restringidos (leitura de dados legados).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.app.models.activity import ActivityCreateRequest, ActivityResponse
from backend.app.models.extension import ExtensionCreateRequest
from backend.app.models.production import ProductionCreate
from backend.app.models.validators import (
    DATA_MINIMA,
    _maximo_futuro,
    validar_data_evento,
    validar_data_futura,
)

HOJE = date.today()
ANO_9999 = date(9999, 1, 1)
ANO_1800 = date(1800, 1, 1)
ANTES_DO_MINIMO = DATA_MINIMA - timedelta(days=1)


def _ext(nova_data: date) -> ExtensionCreateRequest:
    return ExtensionCreateRequest(nova_data=nova_data, motivo="x")


def _act(data_realizacao: datetime) -> ActivityCreateRequest:
    return ActivityCreateRequest(tipo_id="t", descricao="d", data_realizacao=data_realizacao)


def _prod(data_realizacao: datetime) -> ProductionCreate:
    return ProductionCreate(
        titulo="t",
        veiculo_id="v",
        tipo_producao="artigo",
        status_publicacao="publicado",
        data_realizacao=data_realizacao,
    )


# --- helper validar_data_futura (prorrogação) -------------------------------


@pytest.mark.parametrize(
    "valor",
    [DATA_MINIMA, HOJE, HOJE + timedelta(days=365 * 9), date(HOJE.year + 10, 1, 1)],
)
def test_data_futura_aceita_intervalo_valido(valor: date) -> None:
    assert validar_data_futura(valor) == valor


def test_data_futura_rejeita_antes_do_minimo() -> None:
    with pytest.raises(ValueError, match="anterior ao mínimo"):
        validar_data_futura(ANTES_DO_MINIMO)


def test_data_futura_rejeita_alem_do_maximo() -> None:
    with pytest.raises(ValueError, match="excede o máximo"):
        validar_data_futura(date(HOJE.year + 11, 1, 1))


# --- helper validar_data_evento (atividade/produção) ------------------------


@pytest.mark.parametrize("valor", [DATA_MINIMA, HOJE, HOJE - timedelta(days=1)])
def test_data_evento_aceita_passado_e_hoje(valor: date) -> None:
    assert validar_data_evento(valor) == valor


def test_data_evento_rejeita_antes_do_minimo() -> None:
    with pytest.raises(ValueError, match="anterior ao mínimo"):
        validar_data_evento(ANTES_DO_MINIMO)


def test_data_evento_rejeita_futuro() -> None:
    with pytest.raises(ValueError, match="não pode estar no futuro"):
        validar_data_evento(HOJE + timedelta(days=1))


def test_maximo_futuro_trata_29_de_fevereiro() -> None:
    # 2024 é bissexto; 2034 não é — o limite recua para 28/02 em vez de falhar.
    assert _maximo_futuro(date(2024, 2, 29)) == date(2034, 2, 28)


# --- schema ExtensionCreateRequest (nova_data: futuro permitido) ------------


def test_extension_aceita_data_futura_razoavel() -> None:
    assert _ext(HOJE + timedelta(days=365 * 5)).nova_data == HOJE + timedelta(days=365 * 5)


@pytest.mark.parametrize("valor", [ANO_1800, ANO_9999, ANTES_DO_MINIMO])
def test_extension_rejeita_data_irreal(valor: date) -> None:
    with pytest.raises(ValidationError):
        _ext(valor)


# --- schema ActivityCreateRequest (data_realizacao: sem futuro) -------------


def test_activity_aceita_evento_passado() -> None:
    assert _act(datetime(2024, 1, 1)).data_realizacao == datetime(2024, 1, 1)


@pytest.mark.parametrize(
    "valor",
    [
        datetime(1800, 1, 1),
        datetime(9999, 1, 1),
        datetime(HOJE.year + 1, 1, 1),
    ],
)
def test_activity_rejeita_data_irreal_ou_futura(valor: datetime) -> None:
    with pytest.raises(ValidationError):
        _act(valor)


# --- schema ProductionCreate (data_realizacao: sem futuro) ------------------


def test_production_aceita_evento_passado() -> None:
    assert _prod(datetime(2024, 1, 1)).data_realizacao == datetime(2024, 1, 1)


@pytest.mark.parametrize(
    "valor",
    [
        datetime(1800, 1, 1),
        datetime(9999, 1, 1),
        datetime(HOJE.year + 1, 1, 1),
    ],
)
def test_production_rejeita_data_irreal_ou_futura(valor: datetime) -> None:
    with pytest.raises(ValidationError):
        _prod(valor)


# --- schema de resposta não é restringido (leitura de dados legados) --------


def test_activity_response_aceita_data_futura_sem_validar() -> None:
    # ActivityResponse é leitura: não deve rejeitar datas fora do intervalo de
    # entrada, para não quebrar a exibição de dados já persistidos.
    futuro = datetime(HOJE.year + 50, 1, 1)
    assert ActivityResponse(id="a", data_realizacao=futuro).data_realizacao == futuro

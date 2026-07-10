"""
Validadores reutilizáveis de campos de data para schemas Pydantic.

Responsabilidades:
- Rejeitar datas irreais (ano 1800, ano 9999) com mensagem descritiva,
  resultando em 422 quando aplicadas a um schema de entrada.
- Oferecer dois tipos `Annotated`, conforme a semântica do campo:
    - `DataFutura`: data-hora que pode estar no futuro (ex.: novo prazo de
      prorrogação) — intervalo [2000-01-01, hoje + 10 anos].
    - `DataEventoRealizacao`: evento já ocorrido (ex.: data de realização de
      atividade/produção) — intervalo [2000-01-01, hoje], sem futuro.

O limite superior é diferenciado por campo: prorrogação descreve um prazo
futuro, enquanto `data_realizacao` descreve algo que já aconteceu.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, TypeVar

from pydantic import AfterValidator

DATA_MINIMA: date = date(2000, 1, 1)
ANOS_MAXIMOS_FUTURO: int = 10

DateT = TypeVar("DateT", bound=date)


def _como_data(valor: date) -> date:
    """Reduz um `datetime` à sua parte de data para comparação de intervalo.

    `datetime` é subclasse de `date`; `data_realizacao` e `nova_data` chegam
    como `datetime`. A comparação de intervalo é feita sempre no nível de dia.

    Args:
        valor: Data ou data-hora a normalizar.

    Returns:
        A parte de data (`date`) correspondente.
    """
    return valor.date() if isinstance(valor, datetime) else valor


def _maximo_futuro(hoje: date) -> date:
    """Calcula o limite superior `hoje + ANOS_MAXIMOS_FUTURO` anos.

    Trata 29 de fevereiro: se o ano-alvo não for bissexto, recua para 28.

    Args:
        hoje: Data de referência (normalmente `date.today()`).

    Returns:
        Data máxima aceita para campos de data futura.
    """
    try:
        return hoje.replace(year=hoje.year + ANOS_MAXIMOS_FUTURO)
    except ValueError:
        return hoje.replace(year=hoje.year + ANOS_MAXIMOS_FUTURO, day=28)


def validar_data_futura(valor: DateT) -> DateT:
    """Valida data que pode estar no futuro: [2000-01-01, hoje + 10 anos].

    Args:
        valor: Data ou data-hora informada pelo usuário.

    Returns:
        O mesmo valor, inalterado, se estiver no intervalo aceito.

    Raises:
        ValueError: Se a data for anterior a 2000-01-01 ou exceder o máximo.
    """
    dia = _como_data(valor)
    if dia < DATA_MINIMA:
        raise ValueError(f"data anterior ao mínimo permitido ({DATA_MINIMA.isoformat()})")
    maxima = _maximo_futuro(date.today())
    if dia > maxima:
        raise ValueError(f"data excede o máximo permitido ({maxima.isoformat()})")
    return valor


def validar_data_evento(valor: DateT) -> DateT:
    """Valida data de evento já ocorrido: [2000-01-01, hoje], sem futuro.

    Args:
        valor: Data ou data-hora informada pelo usuário.

    Returns:
        O mesmo valor, inalterado, se estiver no intervalo aceito.

    Raises:
        ValueError: Se a data for anterior a 2000-01-01 ou estiver no futuro.
    """
    dia = _como_data(valor)
    if dia < DATA_MINIMA:
        raise ValueError(f"data anterior ao mínimo permitido ({DATA_MINIMA.isoformat()})")
    if dia > date.today():
        raise ValueError("data não pode estar no futuro")
    return valor


DataFutura = Annotated[datetime, AfterValidator(validar_data_futura)]
DataEventoRealizacao = Annotated[datetime, AfterValidator(validar_data_evento)]

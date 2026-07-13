"""
Modelos Pydantic dos pesos Qualis versionados por programa (fonte de verdade da RL05).

Responsabilidades:
- Definir QualisWeightsUpdate: o conjunto de pesos submetido pelo coordenador para criar
  uma nova versão (POST /api/v1/qualis-weights).
- Definir QualisWeightsVersion: uma versão persistida, com os pesos e os metadados de
  versionamento (vigente_desde, alterado_por, alterado_em).
- Validar que o conjunto cobre exatamente a escala A1-A8 + fallback SC (chaves de
  PESO_POR_NIVEL, a fonte canônica da escala) e que nenhum peso é negativo.

A coleção de versões é o próprio histórico de mudanças (ADR-0003): cada alteração cria uma
nova versão sem sobrescrever a anterior.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from backend.app.models.vehicle import PESO_POR_NIVEL

# Escala canônica que todo conjunto de pesos deve cobrir (A1-A8 + fallback SC).
REQUIRED_LEVELS: frozenset[str] = frozenset(PESO_POR_NIVEL)


def _validate_pesos(pesos: dict[str, float]) -> dict[str, float]:
    """Garante que `pesos` cobre exatamente a escala Qualis e não tem valores negativos.

    Args:
        pesos: Mapa nível -> peso submetido.

    Returns:
        O próprio mapa, se válido.

    Raises:
        ValueError: Se faltar/sobrar nível ou houver peso negativo.
    """
    missing = REQUIRED_LEVELS - pesos.keys()
    extra = pesos.keys() - REQUIRED_LEVELS
    if missing or extra:
        raise ValueError(
            f"pesos deve cobrir exatamente os níveis {sorted(REQUIRED_LEVELS)}; "
            f"faltando={sorted(missing)} inesperado={sorted(extra)}"
        )
    if any(peso < 0 for peso in pesos.values()):
        raise ValueError("pesos não podem ser negativos")
    return pesos


class QualisWeightsUpdate(BaseModel):
    """Conjunto de pesos submetido pelo coordenador para criar uma nova versão."""

    pesos: dict[str, float]

    @field_validator("pesos")
    @classmethod
    def _check_pesos(cls, value: dict[str, float]) -> dict[str, float]:
        return _validate_pesos(value)


class QualisWeightsVersion(BaseModel):
    """Versão persistida dos pesos Qualis de um programa.

    Attributes:
        id: ID do documento em programs/{programa_id}/qualis_weights/.
        pesos: Mapa nível -> peso vigente nesta versão.
        vigente_desde: Momento a partir do qual esta versão vale (resolução por data).
        alterado_por: uid do coordenador que criou a versão.
        alterado_em: Momento de criação da versão.
    """

    id: str
    pesos: dict[str, float]
    vigente_desde: datetime
    alterado_por: str
    alterado_em: datetime

"""
Repositório concreto para a coleção raiz productions/ no Firestore.

Responsabilidades:
- Herdar FirebaseRepository e especializar a leitura da coleção raiz productions/.
- list_all(): herdado — produções cruas com id injetado.
- list_productions(): produções com campos normalizados para os relatórios gerenciais
  (titulo, veiculo_id, tipo_producao, autores, pontuacao_calculada, nivel, programa_id).

Restrição: sem lógica de negócio — apenas leitura e mapeamento de campos. A junção com
activities/ (quem reivindica crédito por produção) e a agregação por aluno/orientador são
responsabilidade do ReportService.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

""""
 Nível de relevância usado quando o veículo da produção não foi classificado em
 programs/{id}/vehicle_levels/ — espelha o fallback C (peso 0.5) da RL05 (data-model §3).
 """

_NIVEL_PADRAO = "C"


def _normalize_production(production: dict[str, Any]) -> dict[str, Any]:
    """Mapeia um documento de produção para os campos consumidos pelos relatórios.

    Args:
        production: Documento cru de productions/ (com id injetado por list_all).

    Returns:
        Dict com os campos de relatório normalizados; nivel cai para o padrão C quando
        o veículo não tem classificação, e pontuacao_calculada é coagida para float.
    """
    return {
        "id": production.get("id"),
        "titulo": production.get("titulo", ""),
        "veiculo_id": production.get("veiculo_id"),
        "tipo_producao": production.get("tipo_producao"),
        "autores": production.get("autores", []),
        "pontuacao_calculada": float(production.get("pontuacao_calculada", 0) or 0),
        "nivel": production.get("nivel") or _NIVEL_PADRAO,
        "programa_id": production.get("programa_id"),
    }


class ProductionRepository(FirebaseRepository):
    """Repositório específico da coleção raiz productions/."""

    def __init__(self) -> None:
        super().__init__("productions")

    async def list_productions(self) -> list[dict[str, Any]]:
        """Lista produções com campos normalizados para os relatórios gerenciais."""
        return [
            _normalize_production(production) for production in await self.list_all()
        ]

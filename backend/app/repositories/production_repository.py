"""
Repositório concreto para a coleção raiz productions/ no Firestore.

Responsabilidades:
- Herdar FirebaseRepository e especializar a leitura da coleção raiz productions/.
- create(data) / get(production_id): herdados — escrita e leitura por id (com id injetado),
  consumidos pelo ProductionService.
- list_all(): herdado — produções cruas com id injetado.
- list_productions(): produções com campos normalizados para os relatórios gerenciais
  (titulo, veiculo_id, tipo_producao, autores, pontuacao_calculada, nivel, programa_id). O
  nivel é resolvido por junção com programs/{programa_id}/vehicle_levels/ via veiculo_id —
  productions/ não persiste nivel (data-model §3); veículos sem classificação caem no padrão SC.
- list_productions_by_program(programa_id): mesma normalização restrita a um programa via
  consulta filtrada no Firestore, sem ler a coleção inteira.

Restrição: sem lógica de negócio — apenas leitura/escrita e mapeamento de campos. A junção com
activities/ (quem reivindica crédito por produção) e a agregação por aluno/orientador são
responsabilidade do ReportService; a pontuação RL05 é resolvida pelo ProductionService e pelo
InferenceRepository.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

# Nível Qualis Único usado quando o veículo da produção não foi classificado em
# programs/{id}/vehicle_levels/ — espelha o fallback SC (peso 0.2) da RL05 (data-model §3).
_NIVEL_PADRAO = "SC"


def _normalize_production(
    production: dict[str, Any], niveis_por_veiculo: dict[str, str]
) -> dict[str, Any]:
    """Mapeia um documento de produção para os campos consumidos pelos relatórios.

    Args:
        production: Documento cru de productions/ (com id injetado por list_all).
        niveis_por_veiculo: Mapa veiculo_id → nivel lido de vehicle_levels/.

    Returns:
        Dict com os campos de relatório normalizados; nivel vem da classificação do veículo
        em vehicle_levels/ e cai para o padrão SC quando ele não está classificado, e
        pontuacao_calculada é coagida para float.
    """
    veiculo_id = production.get("veiculo_id")
    return {
        "id": production.get("id"),
        "titulo": production.get("titulo", ""),
        "veiculo_id": veiculo_id,
        "tipo_producao": production.get("tipo_producao"),
        "autores": production.get("autores", []),
        "pontuacao_calculada": float(production.get("pontuacao_calculada", 0) or 0),
        "nivel": niveis_por_veiculo.get(veiculo_id, _NIVEL_PADRAO),
        "programa_id": production.get("programa_id"),
    }


class ProductionRepository(FirebaseRepository):
    """Repositório específico da coleção raiz productions/."""

    def __init__(self) -> None:
        super().__init__("productions")

    async def list_productions(self) -> list[dict[str, Any]]:
        """Lista produções normalizadas, com o nivel resolvido por junção com vehicle_levels."""
        productions = await self.list_all()
        program_ids = {
            production["programa_id"]
            for production in productions
            if production.get("programa_id")
        }
        niveis_por_veiculo = await self._vehicle_levels(program_ids)
        return [
            _normalize_production(production, niveis_por_veiculo)
            for production in productions
        ]

    async def list_productions_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        """Lista produções normalizadas de um programa via consulta filtrada no Firestore.

        Args:
            programa_id: Programa cujas produções devem ser retornadas.

        Returns:
            Produções do programa normalizadas para os relatórios, com o nivel resolvido por
            junção com vehicle_levels/ — sem ler a coleção inteira e filtrar em memória.
        """
        productions = await self.query(filters=[("programa_id", "==", programa_id)])
        niveis_por_veiculo = await self._vehicle_levels({programa_id})
        return [
            _normalize_production(production, niveis_por_veiculo)
            for production in productions
        ]

    async def list_by_ids(self, production_ids: set[str]) -> list[dict[str, Any]]:
        """Lista produções específicas por id, normalizadas para relatórios/dashboard."""
        if not production_ids:
            return []

        # Busca os documentos em paralelo — os gets são independentes (issue #319).
        fetched = await asyncio.gather(
            *(self.get(production_id) for production_id in production_ids)
        )
        productions = [production for production in fetched if production is not None]

        program_ids = {
            production["programa_id"]
            for production in productions
            if production.get("programa_id")
        }
        niveis_por_veiculo = await self._vehicle_levels(program_ids)
        return [
            _normalize_production(production, niveis_por_veiculo)
            for production in productions
        ]

    async def _vehicle_levels(self, program_ids: set[str]) -> dict[str, str]:
        """Mapa veiculo_id → nivel lido de programs/{id}/vehicle_levels/ dos programas dados.

        Args:
            program_ids: Programas cujas classificações de veículo devem ser carregadas.

        Returns:
            Mapa do veiculo_id para o nivel classificado; veículos sem classificação
            simplesmente não aparecem (o chamador aplica o fallback SC).
        """
        niveis: dict[str, str] = {}
        for programa_id in program_ids:
            levels = FirebaseRepository(f"programs/{programa_id}/vehicle_levels")
            for level in await levels.list_all():
                veiculo_id = level.get("veiculo_id") or level.get("id")
                if veiculo_id and level.get("nivel"):
                    niveis[veiculo_id] = level["nivel"]
        return niveis

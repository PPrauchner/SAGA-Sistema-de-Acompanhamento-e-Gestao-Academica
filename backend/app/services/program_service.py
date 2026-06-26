"""
Serviço para gerenciar configurações de programas acadêmicos e níveis de veículos.

Responsabilidades:
- Recuperar e atualizar configurações do programa (créditos, prazos).
- Gerenciar níveis de relevância de veículos para programas específicos.
- Coordenar com o ProgramRepository para persistência de dados.
"""

from typing import Any
from backend.app.models.program_config import ProgramConfigUpdate
from backend.app.models.vehicle_level import VehicleLevelUpdate, VehicleLevelCreate
from backend.app.repositories.program_repository import ProgramRepository


class ProgramService:
    """Serviço para lidar com a lógica de negócios das configurações do programa."""

    def __init__(self, repository=None):
        """Inicializa o ProgramService.

        Args:
            repository: Uma instância de ProgramRepository. Se None, uma nova é criada.
        """
        self.repository = repository or ProgramRepository()

    async def get_config(self, programa_id: str) -> dict[str, Any] | None:
        """Busca a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            A configuração do programa como dicionário ou None.
        """
        return await self.repository.get_config(programa_id)

    async def list_programs(self) -> list[dict[str, Any]]:
        """Lista os programas cadastrados, com id injetado pelo repositório."""
        return await self.repository.list_all()

    async def update_config(self, programa_id: str, data: ProgramConfigUpdate) -> bool:
        """Atualiza a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.
            data: Os dados de atualização validados pelo Pydantic.

        Returns:
            True se a atualização foi bem-sucedida.
        """
        update_dict = data.model_dump(exclude_unset=True)
        return await self.repository.update_config(programa_id, update_dict)

    async def get_vehicle_levels(self, programa_id: str) -> list[dict[str, Any]]:
        """Busca todos os níveis de relevância de veículos para um programa.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            Uma lista de mapeamentos de níveis de veículos.
        """
        return await self.repository.get_vehicle_levels(programa_id)

    async def update_vehicle_level(
        self, 
        programa_id: str, 
        veiculo_id: str, 
        data: VehicleLevelUpdate | VehicleLevelCreate
    ) -> bool:
        """Atualiza ou cria um mapeamento de nível de relevância de veículo.

        Args:
            programa_id: O identificador único do programa.
            veiculo_id: O identificador único do veículo.
            data: Os dados de nível e peso validados pelo Pydantic.

        Returns:
            True se a atualização foi bem-sucedida.
        """
        update_dict = data.model_dump(exclude_unset=True)
        return await self.repository.update_vehicle_level(programa_id, veiculo_id, update_dict)

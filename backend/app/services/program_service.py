"""
Serviço para gerenciar configurações de programas acadêmicos e níveis de veículos.

Responsabilidades:
- Recuperar e atualizar configurações do programa (créditos, prazos).
- Gerenciar níveis de relevância de veículos para programas específicos.
- Coordenar com o ProgramRepository para persistência de dados.
"""

from datetime import datetime, timezone
from typing import Any
from fastapi import HTTPException, status

from backend.app.models.program_config import ProgramConfigCreate, ProgramConfigUpdate
from backend.app.models.vehicle_level import VehicleLevelUpdate, VehicleLevelCreate
from backend.app.repositories.department_repository import DepartmentRepository
from backend.app.repositories.program_repository import ProgramRepository


class ProgramService:
    """Serviço para lidar com a lógica de negócios das configurações do programa."""

    def __init__(self, repository=None, department_repository=None):
        """Inicializa o ProgramService.

        Args:
            repository: Uma instância de ProgramRepository. Se None, uma nova é criada.
            department_repository: Uma instância de DepartmentRepository, usada para
                validar `departamento_id` na criação de programa. Se None, uma nova é
                criada.
        """
        self.repository = repository or ProgramRepository()
        self._departments = department_repository or DepartmentRepository()

    @staticmethod
    def _validate_creditos_total_min(config: dict[str, Any]) -> None:
        basico = config.get("creditos_grupo_basico_min")
        especifico = config.get("creditos_grupo_especifico_min")
        total = config.get("creditos_total_min")
        if basico is None or especifico is None or total is None:
            return
        if total < basico + especifico:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Créditos totais mínimos não podem ser menores que a soma "
                    "dos créditos básico e específico."
                ),
            )

    async def list_programs(self) -> list[dict[str, Any]]:
        """Lista todos os programas cadastrados no sistema.

        Returns:
            Uma lista de programas, cada um com `id` e demais campos de configuração.
        """
        return await self.repository.list_programs()

    async def create_program(self, data: ProgramConfigCreate) -> dict[str, Any]:
        """Cria um novo programa (adm — ADR-0004).

        Args:
            data: Configuração do novo programa, incluindo `departamento_id`
                (obrigatório pelo schema).

        Returns:
            O id do documento criado e os dados persistidos.

        Raises:
            HTTPException: 404 se `departamento_id` não referenciar um departamento
                existente.
        """
        department = await self._departments.get(data.departamento_id)
        if department is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Departamento não encontrado",
            )

        now = datetime.now(timezone.utc)
        payload = {**data.model_dump(), "criado_em": now, "atualizado_em": now}
        program_id = await self.repository.create(payload)
        return {"id": program_id, **payload}

    async def get_config(self, programa_id: str) -> dict[str, Any] | None:
        """Busca a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.

        Returns:
            A configuração do programa como dicionário ou None.
        """
        return await self.repository.get_config(programa_id)

    async def update_config(self, programa_id: str, data: ProgramConfigUpdate) -> bool:
        """Atualiza a configuração de um determinado programa.

        Args:
            programa_id: O identificador único do programa.
            data: Os dados de atualização validados pelo Pydantic.

        Returns:
            True se a atualização foi bem-sucedida.
        """
        update_dict = data.model_dump(exclude_unset=True)
        current_config = await self.repository.get_config(programa_id) or {}
        self._validate_creditos_total_min({**current_config, **update_dict})
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

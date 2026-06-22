"""
Implementação de InferenceDataSource com dados reais do Firestore.

Responsabilidades:
- Costurar as coleções students/ e programs/ para fornecer os dados que o InferenceService
  consome, mapeando nomes de campos do Firestore ao contrato InferenceDataSource.
- Converter Timestamps Firestore para strings ISO 'YYYY-MM-DD'.
- Retornar [] para atividades, tasks e produções enquanto ActivityRepository e
  WorkPlanRepository não estiverem implementados — o motor opera com créditos zerados
  e exibe checklist "pendente". Quando esses repositórios forem implementados, basta
  delegar para eles nos métodos correspondentes.

Restrição: sem lógica de negócio — apenas leitura e mapeamento de campos.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.app.models.vehicle import PESO_POR_NIVEL
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository

_DEFAULT_RELEVANCIA_PESOS: dict[str, float] = dict(PESO_POR_NIVEL)


def _to_date_str(value: Any) -> str | None:
    """Converte Timestamp Firestore (datetime) ou date para string 'YYYY-MM-DD', ou None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value) or None


class InferenceRepository:
    """Fonte de dados real do Firestore que implementa o contrato InferenceDataSource.

    Métodos que dependem de repositórios ainda não implementados (ActivityRepository,
    WorkPlanRepository) retornam listas vazias. O motor de inferência opera normalmente:
    créditos e produções ficam zerados, o checklist exibe status reais do aluno com
    requisitos de crédito como 'pendente'. Quando os repositórios correspondentes forem
    implementados, basta delegar para eles nos métodos get_approved_activities,
    get_plan_tasks e get_approved_productions.
    """

    def __init__(self) -> None:
        self._students = StudentRepository()
        self._programs = FirebaseRepository("programs")

    async def get_student(self, student_id: str) -> dict[str, Any] | None:
        """Lê o aluno do Firestore e normaliza campos para o contrato InferenceDataSource.

        Args:
            student_id: ID do documento em students/.

        Returns:
            Dict com campos normalizados, ou None se o aluno não existir.
        """
        data = await self._students.get(student_id)
        if data is None:
            return None
        return {
            "id": student_id,
            "nome": data.get("nome", ""),
            "programa_id": data.get("programa_id", "prog_default"),
            "situacao_registrada": data.get("situacao_registrada", "regular"),
            "data_ingresso": _to_date_str(data.get("data_ingresso")),
            "prazo_final": _to_date_str(data.get("prazo_final")),
            "proficiencia_comprovada": bool(data.get("proficiencia_comprovada", False)),
            "proficiencia_data": _to_date_str(data.get("proficiencia_data")),
            "qualificacao_aprovada": bool(data.get("qualificacao_aprovada", False)),
            "qualificacao_data": _to_date_str(data.get("qualificacao_data")),
        }

    async def get_program(self, programa_id: str) -> dict[str, Any] | None:
        """Lê configuração do programa e normaliza nomes de campos.

        Retorna configuração com defaults se o documento não existir no Firestore.
        relevancia_pesos usa valores fixos padrão até vehicle_levels ser carregado
        como subcoleção (depende de VehicleRepository).

        Args:
            programa_id: ID do documento em programs/ (ex: 'prog_default').

        Returns:
            Dict com campos normalizados ao contrato InferenceDataSource.
        """
        data = await self._programs.get(programa_id)
        if data is None:
            return {
                "id": programa_id,
                "min_creditos_basico": 12,
                "min_creditos_especifico": 8,
                "max_creditos_tecnologico": 4,
                "min_creditos_total": 24,
                "max_prorrogacoes": 1,
                "meses_ate_qualificacao": 12,
                "relevancia_pesos": dict(_DEFAULT_RELEVANCIA_PESOS),
            }
        return {
            "id": programa_id,
            "min_creditos_basico": int(data.get("creditos_grupo_basico_min", 12)),
            "min_creditos_especifico": int(data.get("creditos_grupo_especifico_min", 8)),
            "max_creditos_tecnologico": int(data.get("creditos_grupo_tecnologico_max", 4)),
            "min_creditos_total": int(data.get("creditos_total_min", 24)),
            "max_prorrogacoes": int(data.get("max_prorrogacoes", 1)),
            "meses_ate_qualificacao": int(data.get("meses_ate_qualificacao", 12)),
            # TODO: carregar de programs/{id}/vehicle_levels/ quando VehicleRepository estiver pronto
            "relevancia_pesos": dict(_DEFAULT_RELEVANCIA_PESOS),
        }

    async def get_approved_activities(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna [] até ActivityRepository.list_activities estar implementado."""
        return []

    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna [] até WorkPlanRepository.get_all_tasks_for_student estar implementado."""
        return []

    async def get_approved_productions(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna [] até ProductionRepository estar implementado."""
        return []

    async def save_inferred_status(self, student_id: str, snapshot: dict[str, Any]) -> str:
        """Persiste snapshot em students/{id}/inferred_status/ e atualiza situacao_inferida.

        Args:
            student_id: ID do documento em students/.
            snapshot: Resultado completo da inferência serializado.

        Returns:
            ID gerado para o documento de snapshot.
        """
        snapshot_id = await self._students.set_subcollection_auto(
            student_id, "inferred_status", snapshot
        )
        await self._students.update(
            student_id, {"situacao_inferida": snapshot.get("situacao_inferida")}
        )
        return snapshot_id

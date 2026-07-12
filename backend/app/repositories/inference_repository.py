"""
Implementação de InferenceDataSource com dados reais do Firestore.

Responsabilidades:
- Costurar as coleções students/, programs/ e students/{id}/activities/ para fornecer os
  dados que o InferenceService consome, mapeando nomes de campos do Firestore ao contrato
  InferenceDataSource.
- Converter Timestamps Firestore para strings ISO 'YYYY-MM-DD'.
- Carregar atividades aprovadas (juntando activity_types para grupo/tipo_ativo), tasks do
  plano (via WorkPlanRepository) e produções aprovadas do aluno, normalizando cada uma ao
  contrato InferenceDataSource consumido pelo InferenceService.

Restrição: sem lógica de negócio — apenas leitura e mapeamento de campos.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.activity_type_repository import ActivityTypeRepository
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.repositories.qualis_weights_repository import QualisWeightsRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.vehicle_repository import VehicleRepository
from backend.app.repositories.work_plan_repository import WorkPlanRepository


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

    Costura students/, programs/, activities/, activity_types/, o plano de trabalho e as
    produções raiz, normalizando cada coleção aos campos que o InferenceService espera.
    """

    def __init__(self) -> None:
        self._students = StudentRepository()
        self._programs = FirebaseRepository("programs")
        self._productions = ProductionRepository()
        self._activities = ActivityRepository()
        self._activity_types = ActivityTypeRepository()
        self._vehicles = VehicleRepository()
        self._qualis_weights = QualisWeightsRepository()
        self._work_plan = WorkPlanRepository()

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

        Retorna configuração com defaults se o documento não existir no Firestore. Os pesos
        Qualis não vêm daqui — são versionados e resolvidos por data via
        get_qualis_weights_versions (ADR-0003).

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
            }
        return {
            "id": programa_id,
            "min_creditos_basico": int(data.get("creditos_grupo_basico_min", 12)),
            "min_creditos_especifico": int(data.get("creditos_grupo_especifico_min", 8)),
            "max_creditos_tecnologico": int(data.get("creditos_grupo_tecnologico_max", 4)),
            "min_creditos_total": int(data.get("creditos_total_min", 24)),
            "max_prorrogacoes": int(data.get("max_prorrogacoes", 1)),
            "meses_ate_qualificacao": int(data.get("meses_ate_qualificacao", 12)),
        }

    async def get_qualis_weights_versions(self, programa_id: str) -> list[dict[str, Any]]:
        """Lê as versões de pesos Qualis de programs/{id}/qualis_weights/ (resolução RL05).

        Args:
            programa_id: ID do documento em programs/.

        Returns:
            Lista de versões (pesos + vigente_desde), usada pelo InferenceService para
            resolver o peso vigente na data de publicação de cada produção.
        """
        return await self._qualis_weights.list_versions(programa_id)

    async def get_approved_activities(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as atividades aprovadas do aluno normalizadas ao contrato de inferência.

        Lê a sub-coleção students/{id}/activities/, filtra por status='aprovado' e junta cada
        atividade ao seu activity_type para derivar o grupo (categoria) e se o tipo está ativo.
        Créditos seguem o override da coordenação: creditos_concedidos quando presente, senão
        creditos_gerados (mesma regra de ActivityService._approved_credits_in_category).

        Args:
            student_id: ID do documento em students/.

        Returns:
            Lista de dicts com id, grupo, creditos, comprovante, tipo_ativo e data.
        """
        activities = await self._activities.list_by_student(student_id)
        types_by_id = {item["id"]: item for item in await self._activity_types.list_all()}

        result: list[dict[str, Any]] = []
        for activity in activities:
            if activity.get("status") != "aprovado":
                continue
            tipo = types_by_id.get(activity.get("tipo_id"), {})
            creditos = activity.get("creditos_concedidos")
            if creditos is None:
                creditos = activity.get("creditos_gerados", 0)
            result.append(
                {
                    "id": activity["id"],
                    "grupo": tipo.get("categoria"),
                    "creditos": float(creditos),
                    "comprovante": activity.get("comprovante_url"),
                    "tipo_ativo": bool(tipo.get("ativo", False)),
                    "data": _to_date_str(activity.get("data_realizacao")),
                }
            )
        return result

    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as tasks do plano do aluno (id, is_defesa, concluida) para a inferência."""
        return await self._work_plan.get_plan_tasks(student_id)

    async def get_approved_productions(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as produções aprovadas do aluno com nível do veículo e pontuação base.

        Com a FK invertida, o vínculo aluno↔produção vive em students/{id}/activities
        (activities.producao_id) e o status de validação fica na atividade, não na produção.
        Lê as atividades do aluno com producao_id, filtra por status='aprovado' e busca cada
        produção correspondente na coleção raiz productions/, juntando-a ao seu nível de
        relevância em programs/{id}/vehicle_levels/ (campo usado pelo fato RL05
        nivel_relevancia).

        Args:
            student_id: ID do documento em students/.

        Returns:
            Lista de dicts com id, veiculo_id, nivel e pontuacao_base.
        """
        student = await self._students.get(student_id)
        programa_id = student.get("programa_id", "prog_default") if student else "prog_default"

        activities = await self._activities.list_by_student(student_id)
        levels = await self._vehicles.list_levels(programa_id)
        nivel_by_vehicle = {level["id"]: level.get("nivel") for level in levels}

        result: list[dict[str, Any]] = []
        for activity in activities:
            producao_id = activity.get("producao_id")
            if not producao_id or activity.get("status") != "aprovado":
                continue
            production = await self._productions.get(producao_id)
            if production is None:
                continue
            veiculo_id = production.get("veiculo_id")
            result.append(
                {
                    "id": production["id"],
                    "veiculo_id": veiculo_id,
                    "nivel": nivel_by_vehicle.get(veiculo_id),
                    "pontuacao_base": production.get("pontuacao_base", 0),
                    # Todo documento em productions/ é bibliográfico por definição do domínio
                    # (RL01 depende do fato producao_bibliografica_validada).
                    "bibliografica": True,
                    # Resolução de peso por data (ADR-0003): a data de publicação é a
                    # data_realizacao da atividade; status_publicacao distingue publicado
                    # (peso travado na data) de submetido/aceito (peso vigente atual).
                    "status_publicacao": production.get("status_publicacao"),
                    "data_realizacao": activity.get("data_realizacao"),
                }
            )
        return result

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

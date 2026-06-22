"""Repositorio em memoria para plano de trabalho.

Stub do MVP: o estado e isolado por instancia de WorkPlanStore para evitar acoplamento
entre testes e apps, mas ainda nao persiste no Firestore.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.models.work_plan import STATUS_ATRASADO, STATUS_CONCLUIDO, STAGE_KIND_DEFESA


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _task(
    task_id: str,
    stage_id: str,
    titulo: str,
    prazo: str,
    status: str,
    prioridade: str = "media",
    progresso: float = 0,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "stage_id": stage_id,
        "titulo": titulo,
        "descricao": "",
        "prazo": _dt(prazo),
        "status": status,
        "prioridade": prioridade,
        "progresso_percentual": progresso,
        "updates": [],
    }


def _seed() -> dict[str, dict[str, Any]]:
    stages = [
        {
            "stage_id": "stage_revisao",
            "nome": "Revisao bibliografica",
            "ordem": 1,
            "data_inicio": _dt("2025-01-01T00:00:00"),
            "data_fim": _dt("2025-04-30T00:00:00"),
            "status": STATUS_CONCLUIDO,
            "tasks": [
                _task("task_revisao_1", "stage_revisao", "Levantamento bibliografico", "2025-02-28T00:00:00", STATUS_CONCLUIDO, "alta", 100),
                _task("task_revisao_2", "stage_revisao", "Sintese da literatura", "2025-04-15T00:00:00", STATUS_CONCLUIDO, "media", 100),
            ],
        },
        {
            "stage_id": "stage_desenvolvimento",
            "nome": "Desenvolvimento",
            "ordem": 2,
            "data_inicio": _dt("2025-05-01T00:00:00"),
            "data_fim": _dt("2026-08-30T00:00:00"),
            "status": "em_andamento",
            "tasks": [
                _task("task_dev_1", "stage_desenvolvimento", "Prototipo inicial", "2026-03-30T00:00:00", STATUS_CONCLUIDO, "alta", 100),
                _task("task_dev_2", "stage_desenvolvimento", "Experimentos principais", "2026-08-30T00:00:00", "em_andamento", "alta", 55),
                _task("task_dev_3", "stage_desenvolvimento", "Analise dos resultados", "2026-09-30T00:00:00", "pendente", "media", 0),
            ],
        },
        {
            "stage_id": "stage_defesa",
            "nome": "Defesa",
            "tipo": "defesa",
            "ordem": 3,
            "data_inicio": _dt("2026-09-01T00:00:00"),
            "data_fim": _dt("2026-12-15T00:00:00"),
            "status": "pendente",
            "tasks": [
                _task("task_defesa_1", "stage_defesa", "Agendamento da banca", "2026-11-15T00:00:00", "pendente", "alta", 0),
            ],
        },
    ]

    return {
        "aluno_regular": {
            "plan_id": "plan_aluno_regular",
            "student_id": "aluno_regular",
            "titulo": "Plano de trabalho de Rita Regular",
            "data_inicio": _dt("2025-01-01T00:00:00"),
            "data_fim_prevista": _dt("2026-12-15T00:00:00"),
            "descricao": "Plano de acompanhamento academico.",
            "progresso_percentual": 0.0,
            "status_geral": "em_andamento",
            "stages": deepcopy(stages),
            "facts": [],
            "notifications": [],
            "history": [],
        },
        "aluno_apto": {
            "plan_id": "plan_aluno_apto",
            "student_id": "aluno_apto",
            "titulo": "Plano concluido para defesa",
            "data_inicio": _dt("2024-01-01T00:00:00"),
            "data_fim_prevista": _dt("2026-12-15T00:00:00"),
            "descricao": "Todas as etapas nao-defesa concluidas.",
            "progresso_percentual": 100.0,
            "status_geral": STATUS_CONCLUIDO,
            "stages": [
                {
                    "stage_id": "stage_apto",
                    "nome": "Escrita",
                    "ordem": 1,
                    "data_inicio": _dt("2024-01-01T00:00:00"),
                    "data_fim": _dt("2026-05-30T00:00:00"),
                    "status": STATUS_CONCLUIDO,
                    "tasks": [
                        _task("task_apto_1", "stage_apto", "Dissertacao final", "2026-05-30T00:00:00", STATUS_CONCLUIDO, "alta", 100),
                        _task("task_apto_2", "stage_apto", "Revisao final", "2026-06-15T00:00:00", STATUS_CONCLUIDO, "alta", 100),
                        _task("task_apto_3", "stage_apto", "Deposito preliminar", "2026-07-01T00:00:00", STATUS_CONCLUIDO, "media", 100),
                    ],
                }
            ],
            "facts": ["plano_concluido(aluno_apto)"],
            "notifications": [],
            "history": [],
        },
        "aluno_risco": {
            "plan_id": "plan_aluno_risco",
            "student_id": "aluno_risco",
            "titulo": "Plano em risco",
            "data_inicio": _dt("2023-01-01T00:00:00"),
            "data_fim_prevista": _dt("2024-03-01T00:00:00"),
            "descricao": "Plano com tarefas atrasadas.",
            "progresso_percentual": 0.0,
            "status_geral": STATUS_ATRASADO,
            "stages": [
                {
                    "stage_id": "stage_risco",
                    "nome": "Pesquisa",
                    "ordem": 1,
                    "data_inicio": _dt("2023-01-01T00:00:00"),
                    "data_fim": _dt("2024-03-01T00:00:00"),
                    "status": STATUS_ATRASADO,
                    "tasks": [
                        _task("task_risco_1", "stage_risco", "Regularizar entregas", "2024-01-31T00:00:00", STATUS_ATRASADO, "alta", 0),
                        _task("task_risco_2", "stage_risco", "Atualizar cronograma", "2024-02-10T00:00:00", "pendente", "alta", 0),
                        _task("task_risco_3", "stage_risco", "Enviar relatorio", "2024-02-20T00:00:00", "pendente", "media", 0),
                    ],
                }
            ],
            "facts": [],
            "notifications": [],
            "history": [],
        },
    }


def _is_defense_stage(stage: dict[str, Any]) -> bool:
    return stage.get("tipo") == STAGE_KIND_DEFESA


class WorkPlanStore:
    """Estado em memoria isolado por instancia/app/teste."""

    def __init__(self) -> None:
        self.plans = _seed()
        self.notifications: list[dict[str, Any]] = []


class WorkPlanRepository:
    """Persistencia em memoria com store injetavel."""

    def __init__(self, store: WorkPlanStore | None = None) -> None:
        self._store = store or WorkPlanStore()

    async def get_plan(self, student_id: str) -> dict[str, Any] | None:
        plan = self._store.plans.get(student_id)
        return deepcopy(plan) if plan else None

    async def get_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        for plan in self._store.plans.values():
            if plan["plan_id"] == plan_id:
                return deepcopy(plan)
        return None

    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]:
        plan = self._store.plans.get(student_id)
        if plan is None:
            return []

        tasks: list[dict[str, Any]] = []
        for stage in plan["stages"]:
            is_defesa = _is_defense_stage(stage)
            for task in stage["tasks"]:
                tasks.append(
                    {
                        "id": task["task_id"],
                        "is_defesa": is_defesa,
                        "concluida": task.get("status") == STATUS_CONCLUIDO,
                    }
                )
        return tasks

    async def get_all_tasks_for_student(self, student_id: str) -> list[dict[str, Any]]:
        """Lista achatada das tasks do plano do aluno, para os dashboards.

        Diferente de `get_plan_tasks` (projeção booleana usada pela inferência),
        expõe os campos consumidos pelo DashboardService: id, status, titulo e
        prazo (ISO date). Lista vazia se o aluno não tem plano.

        Args:
            student_id: Identificador do aluno dono do plano.

        Returns:
            Lista de dicts com chaves id, status, titulo e prazo.
        """
        plan = self._store.plans.get(student_id)
        if plan is None:
            return []

        tasks: list[dict[str, Any]] = []
        for stage in plan["stages"]:
            for task in stage["tasks"]:
                prazo = task.get("prazo")
                tasks.append(
                    {
                        "id": task["task_id"],
                        "status": task.get("status"),
                        "titulo": task.get("titulo", ""),
                        "prazo": prazo.date().isoformat() if isinstance(prazo, datetime) else prazo,
                    }
                )
        return tasks

    async def create_plan(self, student_id: str, data: dict[str, Any]) -> str:
        plan_id = f"plan_{uuid4().hex}"
        self._store.plans[student_id] = {
            "plan_id": plan_id,
            "student_id": student_id,
            "titulo": data["titulo"],
            "data_inicio": data["data_inicio"],
            "data_fim_prevista": data["data_fim_prevista"],
            "descricao": data.get("descricao"),
            "progresso_percentual": 0.0,
            "status_geral": "pendente",
            "stages": [],
            "facts": [],
            "notifications": [],
            "history": [],
        }
        return plan_id

    async def update_plan(self, plan_id: str, data: dict[str, Any]) -> None:
        plan = self._find_plan(plan_id)
        plan["history"].append({"criado_em": datetime.now(timezone.utc), "snapshot": deepcopy(plan)})
        plan.update({k: v for k, v in data.items() if v is not None})

    async def create_stage(self, plan_id: str, data: dict[str, Any]) -> str:
        plan = self._find_plan(plan_id)
        stage_id = f"stage_{uuid4().hex}"

        if str(data.get("nome", "")).casefold() == STAGE_KIND_DEFESA:
            data["tipo"] = STAGE_KIND_DEFESA

        plan["stages"].append({"stage_id": stage_id, "status": "pendente", "tasks": [], **data})
        return stage_id

    async def update_stage(self, stage_id: str, data: dict[str, Any]) -> None:
        stage = self._find_stage(stage_id)
        stage.update({k: v for k, v in data.items() if v is not None})

    async def create_task(self, stage_id: str, data: dict[str, Any]) -> str:
        stage = self._find_stage(stage_id)
        task_id = f"task_{uuid4().hex}"
        stage["tasks"].append(
            {
                "task_id": task_id,
                "stage_id": stage_id,
                "status": "pendente",
                "progresso_percentual": 0.0,
                "updates": [],
                **data,
            }
        )
        return task_id

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        task = self._find_task(task_id)
        task.update({k: v for k, v in data.items() if v is not None})

    async def create_update(self, task_id: str, data: dict[str, Any]) -> str:
        task = self._find_task(task_id)
        update_id = f"upd_{uuid4().hex}"
        task["updates"].append({"update_id": update_id, **data})
        task["progresso_percentual"] = float(data["percentual"])

        if task["progresso_percentual"] >= 100:
            task["status"] = STATUS_CONCLUIDO
        elif task["status"] == "pendente":
            task["status"] = "em_andamento"

        return update_id

    async def list_updates(self, task_id: str) -> list[dict[str, Any]]:
        return deepcopy(self._find_task(task_id)["updates"])

    async def get_task_context(self, task_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        for plan in self._store.plans.values():
            for stage in plan["stages"]:
                for task in stage["tasks"]:
                    if task["task_id"] == task_id:
                        return plan, stage, task
        raise KeyError(task_id)

    async def get_stage_context(self, stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        for plan in self._store.plans.values():
            for stage in plan["stages"]:
                if stage["stage_id"] == stage_id:
                    return plan, stage
        raise KeyError(stage_id)

    async def save_fact(self, student_id: str, fact: str) -> None:
        plan = self._store.plans[student_id]
        if fact not in plan["facts"]:
            plan["facts"].append(fact)

    async def remove_fact(self, student_id: str, fact: str) -> None:
        plan = self._store.plans[student_id]
        plan["facts"] = [item for item in plan["facts"] if item != fact]

    async def create_notification(self, notification: dict[str, Any]) -> str:
        notification_id = f"notif_{uuid4().hex}"
        self._store.notifications.append({"id": notification_id, **notification})
        return notification_id

    async def list_notifications(self) -> list[dict[str, Any]]:
        return deepcopy(self._store.notifications)

    def _find_plan(self, plan_id: str) -> dict[str, Any]:
        for plan in self._store.plans.values():
            if plan["plan_id"] == plan_id:
                return plan
        raise KeyError(plan_id)

    def _find_stage(self, stage_id: str) -> dict[str, Any]:
        for plan in self._store.plans.values():
            for stage in plan["stages"]:
                if stage["stage_id"] == stage_id:
                    return stage
        raise KeyError(stage_id)

    def _find_task(self, task_id: str) -> dict[str, Any]:
        for plan in self._store.plans.values():
            for stage in plan["stages"]:
                for task in stage["tasks"]:
                    if task["task_id"] == task_id:
                        return task
        raise KeyError(task_id)

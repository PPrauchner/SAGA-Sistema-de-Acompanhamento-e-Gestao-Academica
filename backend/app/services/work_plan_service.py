"""Serviço de negócio para planos de trabalho."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.models.work_plan import (
    ActorContext,
    CreatePlanResponse,
    CreateStageResponse,
    CreateTaskResponse,
    ProgressUpdateCreate,
    ProgressUpdateCreated,
    ProgressUpdateList,
    ProgressUpdateResponse,
    StageCreate,
    StageResponse,
    STAGE_KIND_DEFESA,
    STATUS_ATRASADO,
    STATUS_CONCLUIDO,
    StageUpdate,
    TaskCreate,
    TaskResponse,
    TaskStatusResponse,
    TaskUpdate,
    WorkPlanCreate,
    WorkPlanFact,
    WorkPlanFull,
    WorkPlanUpdate,
)
from backend.app.repositories.work_plan_repository import WorkPlanRepository


class WorkPlanNotFoundError(Exception):
    """Recurso de plano de trabalho não encontrado."""


async def _build_progress_update_alert(
    result: ProgressUpdateCreated,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any] | None:
    service = next((value for value in (*kwargs.values(), *args) if hasattr(value, "_repo")), None)
    task_id = kwargs.get("task_id") or next((value for value in args if isinstance(value, str)), None)
    actor = kwargs.get("actor") or next((value for value in args if isinstance(value, ActorContext)), None)
    if service is None or task_id is None or not hasattr(service, "_repo"):
        return None

    plan, _, task = await service._repo.get_task_context(task_id)
    result.notificacao_enviada_ao_orientador = True
    return {
        "tipo": "progresso_task",
        "titulo": "Atualizacao de progresso",
        "mensagem": f"{actor.nome if actor else 'Sistema'} atualizou {task['titulo']}.",
        "destinatario_id": "orientador",
        "entidade_id": task_id,
        "student_id": plan["student_id"],
    }


class WorkPlanService:
    """Orquestra CRUD, progresso e fatos consumidos pela inferência."""

    def __init__(self, repository: WorkPlanRepository) -> None:
        self._repo = repository

    async def get_plan(self, student_id: str) -> WorkPlanFull:
        plan = await self._repo.get_plan(student_id)
        if plan is None:
            raise WorkPlanNotFoundError(student_id)
        return self._to_response(plan)

    async def create_plan(self, student_id: str, payload: WorkPlanCreate) -> CreatePlanResponse:
        plan_id = await self._repo.create_plan(student_id, payload.model_dump())
        return CreatePlanResponse(plan_id=plan_id, message="Plano criado")

    async def update_plan(self, plan_id: str, payload: WorkPlanUpdate) -> dict[str, Any]:
        try:
            await self._repo.update_plan(plan_id, payload.model_dump(exclude_unset=True))
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        return {"message": "Plano atualizado", "historico_criado": True}

    async def create_stage(self, plan_id: str, payload: StageCreate) -> CreateStageResponse:
        try:
            stage_id = await self._repo.create_stage(plan_id, payload.model_dump())
            plan, _ = await self._repo.get_stage_context(stage_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        await self._recalculate(plan)
        return CreateStageResponse(stage_id=stage_id)

    async def update_stage(self, stage_id: str, payload: StageUpdate) -> dict[str, str]:
        try:
            await self._repo.update_stage(stage_id, payload.model_dump(exclude_unset=True))
            plan, _ = await self._repo.get_stage_context(stage_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        await self._recalculate(plan)
        return {"message": "Etapa atualizada"}

    async def create_task(self, stage_id: str, payload: TaskCreate) -> CreateTaskResponse:
        try:
            task_id = await self._repo.create_task(stage_id, payload.model_dump())
            plan, _, _ = await self._repo.get_task_context(task_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        await self._recalculate(plan)
        return CreateTaskResponse(task_id=task_id)

    async def update_task(self, task_id: str, payload: TaskUpdate) -> dict[str, str]:
        try:
            await self._repo.update_task(task_id, payload.model_dump(exclude_unset=True))
            plan, _, _ = await self._repo.get_task_context(task_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        await self._recalculate(plan)
        return {"message": "Task atualizada"}

    async def update_task_status(self, task_id: str, status: str) -> TaskStatusResponse:
        try:
            await self._repo.update_task(task_id, {"status": status, "progresso_percentual": 100.0 if status == STATUS_CONCLUIDO else None})
            plan, _, _ = await self._repo.get_task_context(task_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc

        task_fact = None
        if status == STATUS_CONCLUIDO:
            task_fact = f"task_concluida({task_id}, {plan['student_id']})"
            await self._repo.save_fact(plan["student_id"], task_fact)

        plano_concluido = await self._recalculate(plan)
        plan_fact = f"plano_concluido({plan['student_id']})" if plano_concluido else None
        return TaskStatusResponse(
            message="Status atualizado",
            fato_motor_gerado=task_fact,
            plano_concluido=plano_concluido,
            fato_plano_concluido=plan_fact,
        )

    async def add_progress_update(
        self,
        task_id: str,
        payload: ProgressUpdateCreate,
        actor: ActorContext,
    ) -> ProgressUpdateCreated:
        try:
            plan, _, task = await self._repo.get_task_context(task_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc

        update_id = await self._repo.create_update(
            task_id,
            {
                "task_id": task_id,
                "conteudo": payload.conteudo,
                "percentual": payload.percentual,
                "autor_id": actor.uid,
                "autor_nome": actor.nome,
                "criado_em": datetime.now(timezone.utc),
            },
        )
        await self._recalculate(plan)
        updated_plan = await self._repo.get_plan(plan["student_id"])
        progresso = updated_plan["progresso_percentual"] if updated_plan else 0
        return ProgressUpdateCreated(
            update_id=update_id,
            alerta_prazo=False,
            notificacao_enviada_ao_orientador=False,
            progresso_percentual=progresso,
        )

    async def list_updates(self, task_id: str) -> ProgressUpdateList:
        try:
            updates = await self._repo.list_updates(task_id)
        except KeyError as exc:
            raise WorkPlanNotFoundError(str(exc)) from exc
        return ProgressUpdateList(items=[ProgressUpdateResponse(**item) for item in updates])

    async def get_plan_fact(self, student_id: str) -> WorkPlanFact:
        plan = await self.get_plan(student_id)
        return WorkPlanFact(
            student_id=student_id,
            plano_concluido=plan.plano_concluido,
            fato=plan.fato_plano_concluido,
        )

    async def _recalculate(self, plan: dict[str, Any]) -> bool:
        stages = plan["stages"]
        all_tasks = [task for stage in stages for task in stage["tasks"]]
        for stage in stages:
            tasks = stage["tasks"]
            if not tasks:
                stage["progresso_percentual"] = 0.0
                stage["status"] = stage.get("status", "pendente")
                continue
            stage["progresso_percentual"] = round(sum(float(t.get("progresso_percentual", 0)) for t in tasks) / len(tasks), 2)
            if all(t.get("status") == STATUS_CONCLUIDO for t in tasks):
                stage["status"] = STATUS_CONCLUIDO
            elif any(t.get("status") == STATUS_ATRASADO for t in tasks):
                stage["status"] = STATUS_ATRASADO
            elif any(t.get("status") == "em_andamento" for t in tasks):
                stage["status"] = "em_andamento"
            else:
                stage["status"] = "pendente"

        plan["progresso_percentual"] = round(sum(float(t.get("progresso_percentual", 0)) for t in all_tasks) / len(all_tasks), 2) if all_tasks else 0
        if stages and all(stage["status"] == STATUS_CONCLUIDO for stage in stages):
            plan["status_geral"] = STATUS_CONCLUIDO
        elif any(stage["status"] == STATUS_ATRASADO for stage in stages):
            plan["status_geral"] = STATUS_ATRASADO
        elif any(stage["status"] == "em_andamento" for stage in stages):
            plan["status_geral"] = "em_andamento"
        else:
            plan["status_geral"] = "pendente"

        non_defesa = [task for stage in stages if not _is_defense_stage(stage) for task in stage["tasks"]]
        plano_concluido = bool(non_defesa) and all(task.get("status") == STATUS_CONCLUIDO for task in non_defesa)
        fact = f"plano_concluido({plan['student_id']})"
        if plano_concluido:
            await self._repo.save_fact(plan["student_id"], fact)
        else:
            await self._repo.remove_fact(plan["student_id"], fact)
        return plano_concluido

    def _to_response(self, plan: dict[str, Any]) -> WorkPlanFull:
        stages = []
        for stage in sorted(plan["stages"], key=lambda item: item["ordem"]):
            tasks = []
            for task in stage["tasks"]:
                latest = sorted(task.get("updates", []), key=lambda item: item["criado_em"], reverse=True)
                task_data = {k: v for k, v in task.items() if k != "updates"}
                if latest:
                    task_data["ultima_atualizacao"] = latest[0]
                tasks.append(TaskResponse(**task_data))
            stages.append(StageResponse(**{k: v for k, v in stage.items() if k != "tasks"}, tasks=tasks))
        fact = f"plano_concluido({plan['student_id']})"
        return WorkPlanFull(
            **{k: v for k, v in plan.items() if k not in {"stages", "facts", "notifications", "history"}},
            plano_concluido=fact in plan.get("facts", []),
            fato_plano_concluido=fact if fact in plan.get("facts", []) else None,
            stages=stages,
        )


def _is_defense_stage(stage: dict[str, Any]) -> bool:
    return stage.get("tipo") == STAGE_KIND_DEFESA

"""Repositorio do plano de trabalho persistido no Firestore.

Responsabilidades:
- Persistir planos, etapas, tasks e updates de progresso no aninhamento
  students/{student_id}/work_plan/{plan}/stages/{stage}/tasks/{task}/updates/{update}.
- Persistir os fatos de inferencia do plano (plano_concluido, task_concluida) como array
  no documento do plano, e as notificacoes (A05) na colecao raiz notifications/.
- Preservar a interface publica consumida por WorkPlanService e DashboardService.

Estrategia de localizacao (sem indices): varios metodos recebem apenas o id-folha
(stage_id, task_id). Para evitar collection group queries — que exigiriam indices
collection-group no Firestore — o id publico devolvido ao chamador **codifica o caminho
completo** ate o documento, separado por `~`:

    plan_id  = "{student_id}~{plan_doc}"
    stage_id = "{student_id}~{plan_doc}~{stage_doc}"
    task_id  = "{student_id}~{plan_doc}~{stage_doc}~{task_doc}"

Assim qualquer escrita resolve o caminho diretamente do id, sem consulta. Os ids sao
opacos para os consumidores (frontend e motor de inferencia apenas os repassam).

Campos calculados: `progresso_percentual` e `status`/`status_geral` sao agregados das tasks
e calculados em leitura (campo `calc` do modelo de dados), nao persistidos.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from backend.app.core.firebase import get_firestore_client
from backend.app.models.work_plan import (
    STAGE_KIND_DEFESA,
    STATUS_ATRASADO,
    STATUS_CONCLUIDO,
)

_SEP = "~"
_WORK_PLAN = "work_plan"
_STAGES = "stages"
_TASKS = "tasks"
_UPDATES = "updates"
_NOTIFICATIONS = "notifications"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    """Remove chaves com valor None (paridade com o update parcial do stub anterior)."""
    return {key: value for key, value in data.items() if value is not None}


def _decode(public_id: str, trailing: int) -> list[str]:
    """Decodifica um id publico nos seus segmentos de caminho.

    Args:
        public_id: Id codificado (ex: "sid~plan~stage").
        trailing: Numero de segmentos de documento apos o student_id
            (1 para plano, 2 para etapa, 3 para task).

    Returns:
        Lista [student_id, *doc_ids]. O student_id preserva eventuais `~` internos.

    Raises:
        KeyError: Se o id nao tiver segmentos suficientes (malformado).
    """
    parts = public_id.rsplit(_SEP, trailing)
    if len(parts) != trailing + 1:
        raise KeyError(public_id)
    return parts


def _is_defense_stage(stage: dict[str, Any]) -> bool:
    return stage.get("tipo") == STAGE_KIND_DEFESA


def _aggregate(plan: dict[str, Any]) -> None:
    """Calcula progresso e status de cada etapa e do plano a partir das tasks.

    Mutacao in-place do dict montado em leitura. Espelha a agregacao de
    WorkPlanService._recalculate, sem os efeitos colaterais de fatos.

    Args:
        plan: Plano montado com `stages` -> `tasks` ja carregados.
    """
    stages = plan["stages"]
    all_tasks = [task for stage in stages for task in stage["tasks"]]
    for stage in stages:
        tasks = stage["tasks"]
        if not tasks:
            stage["progresso_percentual"] = 0.0
            stage["status"] = stage.get("status", "pendente")
            continue
        stage["progresso_percentual"] = round(
            sum(float(task.get("progresso_percentual", 0)) for task in tasks) / len(tasks), 2
        )
        if all(task.get("status") == STATUS_CONCLUIDO for task in tasks):
            stage["status"] = STATUS_CONCLUIDO
        elif any(task.get("status") == STATUS_ATRASADO for task in tasks):
            stage["status"] = STATUS_ATRASADO
        elif any(task.get("status") == "em_andamento" for task in tasks):
            stage["status"] = "em_andamento"
        else:
            stage["status"] = "pendente"

    plan["progresso_percentual"] = (
        round(sum(float(task.get("progresso_percentual", 0)) for task in all_tasks) / len(all_tasks), 2)
        if all_tasks
        else 0
    )
    if stages and all(stage["status"] == STATUS_CONCLUIDO for stage in stages):
        plan["status_geral"] = STATUS_CONCLUIDO
    elif any(stage["status"] == STATUS_ATRASADO for stage in stages):
        plan["status_geral"] = STATUS_ATRASADO
    elif any(stage["status"] == "em_andamento" for stage in stages):
        plan["status_geral"] = "em_andamento"
    else:
        plan["status_geral"] = "pendente"


class WorkPlanRepository:
    """Persistencia do plano de trabalho no Firestore via Admin SDK.

    O Firebase Admin SDK e sincrono; cada operacao de I/O roda em uma thread separada
    via asyncio.to_thread para nao bloquear o event loop do FastAPI.
    """

    # ------------------------------------------------------------------ leitura

    async def get_plan(self, student_id: str) -> dict[str, Any] | None:
        """Retorna o plano do aluno (montado com etapas, tasks e agregados) ou None."""
        return await asyncio.to_thread(self._read_plan_sync, student_id)

    async def get_plan_by_id(self, plan_id: str) -> dict[str, Any] | None:
        """Retorna o plano identificado por `plan_id`, montado, ou None."""

        def _read() -> dict[str, Any] | None:
            student_id, plan_doc = _decode(plan_id, 1)
            snapshot = _plan_ref(student_id, plan_doc).get()
            return _assemble_plan(student_id, snapshot) if snapshot.exists else None

        return await asyncio.to_thread(_read)

    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]:
        """Projecao booleana das tasks para a inferencia (id, is_defesa, concluida)."""

        def _read() -> list[dict[str, Any]]:
            plan = self._read_plan_sync(student_id)
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

        return await asyncio.to_thread(_read)

    async def get_all_tasks_for_student(self, student_id: str) -> list[dict[str, Any]]:
        """Lista achatada das tasks do plano do aluno para os dashboards.

        Expoe os campos consumidos pelo DashboardService: id, status, titulo e prazo
        (ISO date). Lista vazia se o aluno nao tem plano.

        Args:
            student_id: Identificador do aluno dono do plano.

        Returns:
            Lista de dicts com chaves id, status, titulo e prazo.
        """

        def _read() -> list[dict[str, Any]]:
            plan = self._read_plan_sync(student_id)
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

        return await asyncio.to_thread(_read)

    async def list_updates(self, task_id: str) -> list[dict[str, Any]]:
        """Lista os updates de progresso de uma task. Levanta KeyError se inexistente."""

        def _read() -> list[dict[str, Any]]:
            task_ref = _task_ref(task_id)
            if not task_ref.get().exists:
                raise KeyError(task_id)
            return _load_updates(task_ref)

        return await asyncio.to_thread(_read)

    async def get_task_context(
        self, task_id: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Retorna (plano, etapa, task) montados para uma task. KeyError se inexistente."""

        def _read() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            student_id, plan_doc, _stage_doc, _task_doc = _decode(task_id, 3)
            plan = self._read_plan_by_doc(student_id, plan_doc)
            if plan is None:
                raise KeyError(task_id)
            for stage in plan["stages"]:
                for task in stage["tasks"]:
                    if task["task_id"] == task_id:
                        return plan, stage, task
            raise KeyError(task_id)

        return await asyncio.to_thread(_read)

    async def get_stage_context(self, stage_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Retorna (plano, etapa) montados para uma etapa. KeyError se inexistente."""

        def _read() -> tuple[dict[str, Any], dict[str, Any]]:
            student_id, plan_doc, _stage_doc = _decode(stage_id, 2)
            plan = self._read_plan_by_doc(student_id, plan_doc)
            if plan is None:
                raise KeyError(stage_id)
            for stage in plan["stages"]:
                if stage["stage_id"] == stage_id:
                    return plan, stage
            raise KeyError(stage_id)

        return await asyncio.to_thread(_read)

    # ------------------------------------------------------------------ escrita

    async def create_plan(self, student_id: str, data: dict[str, Any]) -> str:
        """Cria o plano do aluno na sub-colecao students/{id}/work_plan e retorna o plan_id."""

        def _write() -> str:
            ref = (
                get_firestore_client()
                .collection("students")
                .document(student_id)
                .collection(_WORK_PLAN)
                .document()
            )
            now = _now()
            ref.set(
                {
                    "titulo": data["titulo"],
                    "data_inicio": data["data_inicio"],
                    "data_fim_prevista": data["data_fim_prevista"],
                    "descricao": data.get("descricao"),
                    "facts": [],
                    "criado_em": now,
                    "atualizado_em": now,
                }
            )
            return f"{student_id}{_SEP}{ref.id}"

        return await asyncio.to_thread(_write)

    async def update_plan(self, plan_id: str, data: dict[str, Any]) -> None:
        """Atualiza campos do plano. Levanta KeyError se o plano nao existir."""

        def _write() -> None:
            student_id, plan_doc = _decode(plan_id, 1)
            ref = _plan_ref(student_id, plan_doc)
            if not ref.get().exists:
                raise KeyError(plan_id)
            ref.update({**_without_none(data), "atualizado_em": _now()})

        await asyncio.to_thread(_write)

    async def create_stage(self, plan_id: str, data: dict[str, Any]) -> str:
        """Cria uma etapa no plano. Levanta KeyError se o plano nao existir."""

        def _write() -> str:
            student_id, plan_doc = _decode(plan_id, 1)
            plan_ref = _plan_ref(student_id, plan_doc)
            if not plan_ref.get().exists:
                raise KeyError(plan_id)
            payload = dict(data)
            if str(payload.get("nome", "")).casefold() == STAGE_KIND_DEFESA:
                payload["tipo"] = STAGE_KIND_DEFESA
            ref = plan_ref.collection(_STAGES).document()
            ref.set({"status": "pendente", **payload})
            return f"{plan_id}{_SEP}{ref.id}"

        return await asyncio.to_thread(_write)

    async def update_stage(self, stage_id: str, data: dict[str, Any]) -> None:
        """Atualiza campos de uma etapa. Levanta KeyError se a etapa nao existir."""

        def _write() -> None:
            ref = _stage_ref(stage_id)
            if not ref.get().exists:
                raise KeyError(stage_id)
            ref.update(_without_none(data))

        await asyncio.to_thread(_write)

    async def create_task(self, stage_id: str, data: dict[str, Any]) -> str:
        """Cria uma task na etapa. Levanta KeyError se a etapa nao existir."""

        def _write() -> str:
            stage_ref = _stage_ref(stage_id)
            if not stage_ref.get().exists:
                raise KeyError(stage_id)
            ref = stage_ref.collection(_TASKS).document()
            now = _now()
            ref.set(
                {
                    "status": "pendente",
                    "progresso_percentual": 0.0,
                    "criado_em": now,
                    "atualizado_em": now,
                    **data,
                }
            )
            return f"{stage_id}{_SEP}{ref.id}"

        return await asyncio.to_thread(_write)

    async def update_task(self, task_id: str, data: dict[str, Any]) -> None:
        """Atualiza campos de uma task. Levanta KeyError se a task nao existir."""

        def _write() -> None:
            ref = _task_ref(task_id)
            if not ref.get().exists:
                raise KeyError(task_id)
            ref.update({**_without_none(data), "atualizado_em": _now()})

        await asyncio.to_thread(_write)

    async def delete_task(self, task_id: str) -> None:
        """Remove uma task e seus updates. Levanta KeyError se a task nao existir."""

        def _write() -> None:
            ref = _task_ref(task_id)
            if not ref.get().exists:
                raise KeyError(task_id)
            for update_doc in ref.collection(_UPDATES).stream():
                update_doc.reference.delete()
            ref.delete()

        await asyncio.to_thread(_write)

    async def create_update(self, task_id: str, data: dict[str, Any]) -> str:
        """Registra um update de progresso e ajusta progresso/status da task.

        Args:
            task_id: Task que recebe o update.
            data: Conteudo do update; deve conter `percentual`.

        Returns:
            O id do update criado.

        Raises:
            KeyError: Se a task nao existir.
        """

        def _write() -> str:
            task_ref = _task_ref(task_id)
            snapshot = task_ref.get()
            if not snapshot.exists:
                raise KeyError(task_id)
            update_ref = task_ref.collection(_UPDATES).document()
            update_ref.set({"update_id": update_ref.id, **data})

            progresso = float(data["percentual"])
            task_update: dict[str, Any] = {"progresso_percentual": progresso}
            if progresso >= 100:
                task_update["status"] = STATUS_CONCLUIDO
            elif (snapshot.to_dict() or {}).get("status") == "pendente":
                task_update["status"] = "em_andamento"
            task_ref.update(task_update)
            return update_ref.id

        return await asyncio.to_thread(_write)

    # ------------------------------------------------------------------ fatos

    async def save_fact(self, student_id: str, fact: str) -> None:
        """Adiciona um fato de inferencia ao plano do aluno (no-op se nao houver plano)."""

        def _write() -> None:
            snapshot = self._plan_snapshot_sync(student_id)
            if snapshot is None:
                return
            facts = list((snapshot.to_dict() or {}).get("facts", []))
            if fact not in facts:
                facts.append(fact)
                snapshot.reference.update({"facts": facts})

        await asyncio.to_thread(_write)

    async def remove_fact(self, student_id: str, fact: str) -> None:
        """Remove um fato de inferencia do plano do aluno (no-op se nao houver plano)."""

        def _write() -> None:
            snapshot = self._plan_snapshot_sync(student_id)
            if snapshot is None:
                return
            facts = [item for item in (snapshot.to_dict() or {}).get("facts", []) if item != fact]
            snapshot.reference.update({"facts": facts})

        await asyncio.to_thread(_write)

    # ------------------------------------------------------------ notificacoes

    async def create_notification(self, notification: dict[str, Any]) -> str:
        """Persiste uma notificacao (A05) na colecao raiz notifications/ e retorna o id."""

        def _write() -> str:
            _, ref = get_firestore_client().collection(_NOTIFICATIONS).add(notification)
            return ref.id

        return await asyncio.to_thread(_write)

    async def list_notifications(self) -> list[dict[str, Any]]:
        """Lista as notificacoes da colecao raiz notifications/ (id injetado)."""

        def _read() -> list[dict[str, Any]]:
            result = []
            for doc in get_firestore_client().collection(_NOTIFICATIONS).stream():
                item = doc.to_dict() or {}
                item["id"] = doc.id
                result.append(item)
            return result

        return await asyncio.to_thread(_read)

    # --------------------------------------------------------------- internos

    def _plan_snapshot_sync(self, student_id: str):
        """Primeiro snapshot de plano do aluno (1 por aluno no MVP), ou None."""
        docs = list(
            get_firestore_client()
            .collection("students")
            .document(student_id)
            .collection(_WORK_PLAN)
            .limit(1)
            .stream()
        )
        return docs[0] if docs else None

    def _read_plan_sync(self, student_id: str) -> dict[str, Any] | None:
        snapshot = self._plan_snapshot_sync(student_id)
        return _assemble_plan(student_id, snapshot) if snapshot else None

    def _read_plan_by_doc(self, student_id: str, plan_doc: str) -> dict[str, Any] | None:
        snapshot = _plan_ref(student_id, plan_doc).get()
        return _assemble_plan(student_id, snapshot) if snapshot.exists else None


def _plan_ref(student_id: str, plan_doc: str):
    """Referencia ao documento students/{student_id}/work_plan/{plan_doc}."""
    return (
        get_firestore_client()
        .collection("students")
        .document(student_id)
        .collection(_WORK_PLAN)
        .document(plan_doc)
    )


def _stage_ref(stage_id: str):
    """Referencia ao documento de etapa a partir do id codificado."""
    student_id, plan_doc, stage_doc = _decode(stage_id, 2)
    return _plan_ref(student_id, plan_doc).collection(_STAGES).document(stage_doc)


def _task_ref(task_id: str):
    """Referencia ao documento de task a partir do id codificado."""
    student_id, plan_doc, stage_doc, task_doc = _decode(task_id, 3)
    return (
        _plan_ref(student_id, plan_doc)
        .collection(_STAGES)
        .document(stage_doc)
        .collection(_TASKS)
        .document(task_doc)
    )


def _load_updates(task_ref) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for doc in task_ref.collection(_UPDATES).stream():
        item = doc.to_dict() or {}
        item.setdefault("update_id", doc.id)
        updates.append(item)
    return updates


def _assemble_plan(student_id: str, plan_snapshot) -> dict[str, Any]:
    """Monta o plano completo (etapas -> tasks -> updates) com ids codificados e agregados.

    Args:
        student_id: Aluno dono do plano (primeiro segmento dos ids codificados).
        plan_snapshot: Snapshot do documento work_plan.

    Returns:
        Dict do plano com `stages` aninhados, ids publicos codificados e progresso/status
        calculados em leitura.
    """
    plan = plan_snapshot.to_dict() or {}
    plan_id = f"{student_id}{_SEP}{plan_snapshot.id}"
    plan["plan_id"] = plan_id
    plan["student_id"] = student_id
    plan.setdefault("facts", [])

    stages: list[dict[str, Any]] = []
    for stage_doc in plan_snapshot.reference.collection(_STAGES).stream():
        stage = stage_doc.to_dict() or {}
        stage_id = f"{plan_id}{_SEP}{stage_doc.id}"
        stage["stage_id"] = stage_id
        tasks: list[dict[str, Any]] = []
        for task_doc in stage_doc.reference.collection(_TASKS).stream():
            task = task_doc.to_dict() or {}
            task_id = f"{stage_id}{_SEP}{task_doc.id}"
            task["task_id"] = task_id
            task["stage_id"] = stage_id
            task["updates"] = _load_updates(task_doc.reference)
            tasks.append(task)
        stage["tasks"] = tasks
        stages.append(stage)

    plan["stages"] = stages
    _aggregate(plan)
    return plan

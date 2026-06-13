"""
Repositório para atividades creditáveis e tipos de atividade no Firestore.

Responsabilidades:
- CRUD de activity_types/ (coleção raiz).
- CRUD de students/{id}/activities/ (sub-coleção).
- Agregação de créditos aprovados por categoria para alimentar fatos do motor RL04.
"""

from __future__ import annotations

import asyncio
from typing import Any

from google.cloud.firestore_v1.base_query import FieldFilter

from backend.app.repositories.firebase_repository import FirebaseRepository

ACTIVITY_TYPES_COLLECTION = "activity_types"


class ActivityRepository(FirebaseRepository):
    """Repositório concreto para atividades creditáveis e seus tipos."""

    # ── Activity Types ────────────────────────────────────────────────────────

    async def list_activity_types(self, only_active: bool = False) -> list[dict[str, Any]]:
        """Lista todos os tipos de atividade creditável.

        Args:
            only_active: Se True, retorna apenas tipos com ativo=True.

        Returns:
            Lista de dicts representando os tipos de atividade.
        """
        filters = [FieldFilter("ativo", "==", True)] if only_active else None
        return await self.list(ACTIVITY_TYPES_COLLECTION, filters=filters)

    async def get_activity_type(self, type_id: str) -> dict[str, Any]:
        """Retorna um tipo de atividade pelo ID.

        Args:
            type_id: ID do documento em activity_types/.

        Returns:
            Dict com os campos do tipo de atividade.
        """
        return await self.get(ACTIVITY_TYPES_COLLECTION, type_id)

    async def create_activity_type(self, data: dict[str, Any]) -> dict[str, Any]:
        """Cria um novo tipo de atividade.

        Args:
            data: Campos do ActivityTypeCreate + ativo=True.

        Returns:
            Dict do documento criado com id.
        """
        payload = {**data, "ativo": True}
        return await self.create(ACTIVITY_TYPES_COLLECTION, payload)

    async def update_activity_type(
        self, type_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Atualiza campos de um tipo de atividade.

        Args:
            type_id: ID do documento.
            data: Campos a atualizar.

        Returns:
            Dict atualizado.
        """
        return await self.update(ACTIVITY_TYPES_COLLECTION, type_id, data)

    async def toggle_activity_type(self, type_id: str) -> dict[str, Any]:
        """Inverte o campo ativo de um tipo de atividade.

        Args:
            type_id: ID do documento.

        Returns:
            Dict com o novo estado.
        """
        current = await self.get(ACTIVITY_TYPES_COLLECTION, type_id)
        novo_estado = not current.get("ativo", True)
        return await self.update(ACTIVITY_TYPES_COLLECTION, type_id, {"ativo": novo_estado})

    # ── Activities ────────────────────────────────────────────────────────────

    def _activities_collection(self, student_id: str) -> str:
        return f"students/{student_id}/activities"

    async def create_activity(
        self, student_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Cria uma nova atividade na sub-coleção do aluno.

        Args:
            student_id: UID do aluno no Firestore.
            data: Campos da atividade a persistir.

        Returns:
            Dict do documento criado.
        """
        payload = {**data, "student_id": student_id}
        return await self.create(self._activities_collection(student_id), payload)

    async def get_activity(self, student_id: str, activity_id: str) -> dict[str, Any]:
        """Retorna uma atividade pelo ID.

        Args:
            student_id: UID do aluno.
            activity_id: ID do documento da atividade.

        Returns:
            Dict com os campos da atividade.
        """
        return await self.get(self._activities_collection(student_id), activity_id)

    async def update_activity(
        self, student_id: str, activity_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Atualiza uma atividade.

        Args:
            student_id: UID do aluno.
            activity_id: ID do documento.
            data: Campos a atualizar.

        Returns:
            Dict atualizado.
        """
        return await self.update(
            self._activities_collection(student_id), activity_id, data
        )

    async def list_activities(
        self,
        student_id: str,
        status_filter: str | None = None,
        categoria_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista atividades de um aluno com filtros opcionais.

        Args:
            student_id: UID do aluno.
            status_filter: Filtra por status.
            categoria_filter: Filtra por categoria do tipo de atividade.

        Returns:
            Lista de dicts das atividades.
        """
        filters = []
        if status_filter:
            filters.append(FieldFilter("status", "==", status_filter))
        if categoria_filter:
            filters.append(FieldFilter("categoria", "==", categoria_filter))

        return await self.list(
            self._activities_collection(student_id),
            filters=filters or None,
        )

    async def get_approved_activities_by_category(
        self, student_id: str
    ) -> dict[str, float]:
        """Agrega créditos aprovados por categoria para o motor RL04.

        Args:
            student_id: UID do aluno.

        Returns:
            Dict com chaves 'basico', 'especifico', 'tecnologico' e totais.
        """
        activities = await self.list(
            self._activities_collection(student_id),
            filters=[FieldFilter("status", "==", "aprovado")],
        )
        totals: dict[str, float] = {"basico": 0.0, "especifico": 0.0, "tecnologico": 0.0}
        for act in activities:
            cat = act.get("categoria", "")
            creditos = float(act.get("creditos_gerados", 0))
            if cat in totals:
                totals[cat] += creditos
        return totals

    async def save_comprovante_url(
        self, student_id: str, activity_id: str, url: str
    ) -> dict[str, Any]:
        """Grava a URL do comprovante em uma atividade.

        Args:
            student_id: UID do aluno.
            activity_id: ID da atividade.
            url: URL pública do arquivo no Firebase Storage.

        Returns:
            Dict da atividade atualizada.
        """
        return await self.update(
            self._activities_collection(student_id),
            activity_id,
            {"comprovante_url": url},
        )

    async def find_activity_across_students(
        self, activity_id: str
    ) -> dict[str, Any] | None:
        """Busca uma atividade em todos os alunos.

        Args:
            activity_id: ID do documento da atividade.

        Returns:
            Dict com student_id e campos, ou None.
        """
        def _search() -> dict[str, Any] | None:
            students = list(self.client.collection("students").stream())
            for s in students:
                snap = (
                    self.client.collection("students")
                    .document(s.id)
                    .collection("activities")
                    .document(activity_id)
                    .get()
                )
                if snap.exists:
                    return {"student_id": s.id, **(snap.to_dict() or {})}
            return None

        return await asyncio.to_thread(_search)

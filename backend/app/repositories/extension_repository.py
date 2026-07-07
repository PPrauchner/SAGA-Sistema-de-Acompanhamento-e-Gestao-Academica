"""Repositorio da colecao raiz extensions/."""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

STATUS_PENDING = "pendente"
STATUS_APPROVED = "aprovada"


class ExtensionRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("extensions")

    async def list_by_program(
        self, programa_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista prorrogações de um programa via consulta filtrada no Firestore.

        Args:
            programa_id: Programa cujas prorrogações devem ser retornadas.
            status: Quando informado, restringe ao status correspondente
                (ex.: 'pendente'); caso contrário retorna todos os status.

        Returns:
            Documentos de extensions/ do programa (com id injetado), filtrados por status
            quando solicitado — sem ler a coleção inteira e filtrar em memória.
        """
        filters: list[tuple] = [("programa_id", "==", programa_id)]
        if status is not None:
            filters.append(("status", "==", status))
        return await self.query(filters=filters)

    async def list_by_student_ids(self, student_ids: set[str]) -> list[dict[str, Any]]:
        if not student_ids:
            return []
        extensions = await self.list_all()
        return [
            extension
            for extension in extensions
            if extension.get("student_id") in student_ids
        ]

    async def has_pending_for_student(self, student_id: str) -> bool:
        matches = await self.query(
            filters=[
                ("student_id", "==", student_id),
                ("status", "==", STATUS_PENDING),
            ],
            limit=1,
        )
        return bool(matches)

    async def count_approved_for_student(self, student_id: str) -> int:
        """Conta as prorrogações já aprovadas de um aluno.

        Args:
            student_id: Aluno cujas prorrogações aprovadas devem ser contadas.

        Returns:
            Quantidade de documentos em extensions/ do aluno com status 'aprovada'
            — base para comparar com programs.max_prorrogacoes (sem contador persistido).
        """
        matches = await self.query(
            filters=[
                ("student_id", "==", student_id),
                ("status", "==", STATUS_APPROVED),
            ],
        )
        return len(matches)

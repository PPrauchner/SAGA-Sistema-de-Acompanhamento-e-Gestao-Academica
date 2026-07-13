"""
Repositório concreto para a coleção raiz `extensions/` (prorrogações).

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção raiz
  `extensions/` (ADR-0006 — não é sub-coleção de students).
- create_extension / get_extension / update_extension: CRUD do documento.
- list_by_student / list_by_status / list_pending_by_students: consultas de
  leitura para as telas de aluno, orientador e coordenação.
- has_pending / count_approved: gates de negócio consumidos pelo service.

Sem lógica de negócio: apenas acesso ao Firestore. A resolução de aluno,
orientador e configuração do programa fica nos repositórios das respectivas
coleções (Student/Advisor/Program), consumidos pelo ExtensionService.
"""

from __future__ import annotations

from typing import Any

from backend.app.repositories.firebase_repository import FirebaseRepository

_COLLECTION = "extensions"
_STATUS_PENDENTE = "pendente"
_STATUS_APROVADA = "aprovada"


def _sort_by_created_desc(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordena por created_at desc em memória (evita índice composto no Firestore)."""
    return sorted(items, key=lambda d: d.get("created_at") or "", reverse=True)


class ExtensionRepository(FirebaseRepository):
    """Repositório da coleção raiz `extensions/`."""

    def __init__(self) -> None:
        super().__init__(_COLLECTION)

    async def create_extension(self, data: dict[str, Any]) -> str:
        """Cria uma prorrogação com auto-id e retorna o doc id gerado."""
        return await self.create(data)

    async def get_extension(self, extension_id: str) -> dict[str, Any] | None:
        """Lê uma prorrogação por id (inclui o campo `id`), ou None."""
        return await self.get(extension_id)

    async def update_extension(self, extension_id: str, data: dict[str, Any]) -> bool:
        """Atualiza parcialmente os campos de uma prorrogação."""
        return await self.update(extension_id, data)

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        """Lista as prorrogações de um aluno, mais recentes primeiro."""
        items = await self.query(filters=[("student_id", "==", student_id)])
        return _sort_by_created_desc(items)

    async def list_by_status(self, status: str) -> list[dict[str, Any]]:
        """Lista todas as prorrogações com um dado status, mais recentes primeiro."""
        items = await self.query(filters=[("status", "==", status)])
        return _sort_by_created_desc(items)

    async def list_pending_by_students(
        self,
        student_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Lista prorrogações pendentes restritas a um conjunto de alunos.

        Args:
            student_ids: Doc ids dos alunos (ex.: orientandos de um orientador).

        Returns:
            Prorrogações pendentes desses alunos, mais recentes primeiro.
        """
        if not student_ids:
            return []
        allowed = set(student_ids)
        pending = await self.list_by_status(_STATUS_PENDENTE)
        return [ext for ext in pending if ext.get("student_id") in allowed]

    async def has_pending(self, student_id: str) -> bool:
        """Indica se o aluno já possui uma solicitação pendente."""
        items = await self.query(
            filters=[("student_id", "==", student_id), ("status", "==", _STATUS_PENDENTE)],
            limit=1,
        )
        return bool(items)

    async def count_approved(self, student_id: str) -> int:
        """Conta as prorrogações já aprovadas do aluno (prorrogações usadas)."""
        items = await self.query(
            filters=[("student_id", "==", student_id), ("status", "==", _STATUS_APROVADA)],
        )
        return len(items)

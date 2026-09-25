"""
Repositório concreto para operações na coleção advisors/.

Responsabilidades:
- Herdar FirebaseRepository e especializar operações para a coleção advisors/.
- get_advisor(advisor_id), create_advisor(data), update_advisor(advisor_id, data),
  delete_advisor(advisor_id): CRUD básico.
- get_advisors_with_student_count(): lista orientadores enriquecidos com contagem de
  orientandos_ativos via query na coleção students/ filtrada por orientador_id e
  situacao_registrada não-terminal.
- check_advisor_capacity(advisor_id): verifica se orientador ainda está abaixo do
  limite_orientandos configurado (leitura isolada, sujeita a race condition — usar
  apenas para validação prévia de UI, não como guarda final de escrita).
- transfer_student_atomic(advisor_id, student_id, update_data): checa capacidade e
  escreve o novo vínculo do aluno em uma única transação Firestore.
"""

from __future__ import annotations

import asyncio

from google.cloud import firestore as gcloud_firestore

from backend.app.core.firebase import get_firestore_client
from backend.app.repositories.firebase_repository import FirebaseRepository
from backend.app.repositories.student_repository import StudentRepository

_TERMINAL_STUDENT_STATUSES = {"concluido", "desligado"}


class AdvisorCapacityExceededError(Exception):
    """Levantada quando o orientador destino atingiu limite_orientandos dentro da transação."""


class AdvisorRepository(FirebaseRepository):
    def __init__(self) -> None:
        super().__init__("advisors")

    async def get_advisors_with_student_count(
        self,
    ) -> list[dict]:

        advisors = await self.list_all()

        students = await StudentRepository().list_all()

        for advisor in advisors:
            advisor["orientandos_ativos"] = sum(
                1
                for student in students
                if student.get("orientador_id") == advisor["id"]
                and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
            )

        return advisors

    async def count_active_students(
        self,
        advisor_id: str,
    ) -> int:
        students = await StudentRepository().list_all()

        return sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
        )

    async def check_advisor_capacity(
        self,
        advisor_id: str,
    ) -> bool:

        advisor = await self.get(advisor_id)

        if advisor is None:
            return False

        students = await StudentRepository().list_all()

        current = sum(
            1
            for student in students
            if student.get("orientador_id") == advisor_id
            and student.get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
        )

        return current < advisor.get(
            "limite_orientandos",
            5,
        )

    async def transfer_student_atomic(
        self,
        advisor_id: str,
        student_id: str,
        update_data: dict,
    ) -> None:
        """Checa capacidade e escreve o vínculo do aluno em uma única transação Firestore.

        Substitui o par check_advisor_capacity() + StudentRepository.update() usado nos
        fluxos de transferência: leitura da contagem, leitura do limite e escrita do
        orientador_id/coorientador_id acontecem atomicamente, eliminando a janela em que
        duas transferências concorrentes poderiam ultrapassar limite_orientandos.

        Args:
            advisor_id: Orientador destino cuja capacidade deve ser respeitada.
            student_id: Aluno cujo vínculo será atualizado.
            update_data: Campos a aplicar em students/{student_id} (orientador_id e,
                quando aplicável, coorientador_id/programa_id).

        Raises:
            AdvisorCapacityExceededError: se o orientador destino não existe ou já está
                no limite de orientandos.
        """

        client = get_firestore_client()
        advisor_ref = client.collection("advisors").document(advisor_id)
        student_ref = client.collection("students").document(student_id)

        @gcloud_firestore.transactional
        def _run(transaction: gcloud_firestore.Transaction) -> None:
            advisor_snapshot = advisor_ref.get(transaction=transaction)
            if not advisor_snapshot.exists:
                raise AdvisorCapacityExceededError("Orientador destino não encontrado")

            limite = advisor_snapshot.to_dict().get("limite_orientandos", 5)

            students_query = client.collection("students").where(
                "orientador_id", "==", advisor_id
            )
            current = sum(
                1
                for doc in students_query.stream(transaction=transaction)
                if doc.to_dict().get("situacao_registrada") not in _TERMINAL_STUDENT_STATUSES
            )

            if current >= limite:
                raise AdvisorCapacityExceededError(
                    "Orientador destino atingiu o limite de orientandos"
                )

            transaction.update(student_ref, update_data)

        transaction = client.transaction()
        await asyncio.to_thread(_run, transaction)

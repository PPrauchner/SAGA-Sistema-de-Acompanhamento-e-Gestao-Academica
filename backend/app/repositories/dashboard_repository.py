"""
Repository de Dashboard — queries Firestore puras (US-AN03).

Responsabilidades:
- Encapsular exclusivamente o acesso ao Firestore: sem lógica de negócio,
  sem cálculos de índice, sem decisões de domínio.
- Todas as funções são assíncronas e recebem o cliente Firestore por injeção,
  facilitando o mock nos testes.

Coleções acessadas:
    advisors/             — localizar advisor por advisor_uid
    students/             — listar orientandos de um advisor
    students/{uid}/activities — filtrar atividades aprovadas do aluno
    productions/          — buscar pontuacao_calculada de cada produção
"""

from __future__ import annotations

from google.cloud.firestore_v1.async_client import AsyncClient


_PROG_ID = "prog_default"  # Single-tenant conforme PRD


class DashboardRepository:
    """Acesso a dados Firestore para o dashboard do orientador."""

    def __init__(self, db: AsyncClient) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Advisor
    # ------------------------------------------------------------------

    async def get_advisor_doc_id_by_uid(self, advisor_uid: str) -> str | None:
        """Retorna o doc-id do documento em `advisors` cujo campo
        `advisor_uid` seja igual ao UID fornecido.

        O doc-id em `advisors` é auto-id (não o UID do usuário), portanto
        é necessário fazer uma query por campo.

        Args:
            advisor_uid: UID do usuário com papel de orientador.

        Returns:
            Doc-id do documento em `advisors`, ou None se não encontrado.
        """
        query = (
            self._db.collection("advisors")
            .where("advisor_uid", "==", advisor_uid)
            .limit(1)
        )
        docs = [doc async for doc in query.stream()]
        return docs[0].id if docs else None

    # ------------------------------------------------------------------
    # Orientandos do advisor
    # ------------------------------------------------------------------

    async def get_student_uids_de_advisor(self, advisor_uid: str) -> list[str]:
        """Retorna os UIDs dos alunos orientados pelo advisor.

        Busca na coleção `students` todos os documentos cujo campo
        `advisor_uid` corresponda ao orientador. Retorna lista vazia se o
        advisor não tiver orientandos ativos.

        Args:
            advisor_uid: UID do orientador.

        Returns:
            Lista de UIDs dos alunos (pode ser vazia).
        """
        query = self._db.collection("students").where("advisor_uid", "==", advisor_uid)
        return [doc.id async for doc in query.stream()]

    # ------------------------------------------------------------------
    # Produções aprovadas
    # ------------------------------------------------------------------

    async def get_pontuacao_aprovada_de_aluno(self, student_uid: str) -> float:
        """Soma as pontuações das produções com status 'aprovado' do aluno.

        Percurso:
            1. Lista as `activities` do aluno com status == 'aprovado'.
            2. Para cada activity, resolve o `producao_id` na coleção raiz
               `productions` e acumula `pontuacao_calculada`.

        Args:
            student_uid: UID do aluno.

        Returns:
            Soma total das pontuações aprovadas. Retorna 0.0 se não houver
            nenhuma atividade aprovada ou nenhuma produção vinculada.
        """
        activities_ref = (
            self._db.collection("students")
            .document(student_uid)
            .collection("activities")
            .where("status", "==", "aprovado")
        )

        total: float = 0.0
        async for act_doc in activities_ref.stream():
            producao_id: str | None = act_doc.get("producao_id")
            if not producao_id:
                continue

            prod_doc = await self._db.collection("productions").document(producao_id).get()
            if prod_doc.exists:
                pontuacao = prod_doc.get("pontuacao_calculada") or 0.0
                total += float(pontuacao)

        return total

    # ------------------------------------------------------------------
    # Todos os advisors (para cálculo anônimo do programa)
    # ------------------------------------------------------------------

    async def get_todos_advisor_uids(self) -> list[str]:
        """Retorna a lista de todos os `advisor_uid` cadastrados no programa.

        Usado exclusivamente para calcular a posição relativa anônima —
        NUNCA deve ser serializado diretamente para o cliente.

        Returns:
            Lista de advisor_uids de todos os orientadores cadastrados.
        """
        query = self._db.collection("advisors")
        return [
            doc.get("advisor_uid")
            async for doc in query.stream()
            if doc.get("advisor_uid")
        ]
"""
Repositório concreto para as sub-coleções de atividades e produções no Firestore.

Responsabilidades:
- Acessar e persistir dados em students/{id}/activities/ e students/{id}/productions/.
- Métodos de atividade: create_activity(student_id, data), get_activity(activity_id),
  update_activity(activity_id, data), list_activities(student_id, filters).
- Métodos de produção: create_production(student_id, data), list_productions(student_id).
- get_approved_activities_by_category(student_id): agrega créditos por categoria
  (básico, específico, tecnológico) para alimentar os fatos creditos_grupo_* do motor.
- get_approved_productions(student_id): lista produções aprovadas para verificação do
  fato producao_bibliografica_validada.
- Salvar histórico de tipos de atividade em activity_types/{id}/history/ para o aspecto A03.
"""

from datetime import datetime, timezone
from typing import Optional

from backend.app.core.firebase import get_firestore_client


class ActivityRepository:
    COLLECTION = "activities"

    def _db(self):
        return get_firestore_client()

    def get_by_id(self, activity_id: str) -> Optional[dict]:
        doc = self._db().collection(self.COLLECTION).document(activity_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def update(self, activity_id: str, data: dict) -> dict:
        data["atualizado_em"] = datetime.now(timezone.utc)
        ref = self._db().collection(self.COLLECTION).document(activity_id)
        ref.update(data)
        doc = ref.get()
        return {"id": doc.id, **doc.to_dict()}

    def get_advisor_uid_by_student(self, student_id: str) -> Optional[str]:
        """Retorna o uid do orientador responsável pelo aluno."""
        doc = self._db().collection("students").document(student_id).get()
        if not doc.exists:
            return None
        return doc.to_dict().get("orientador_uid")

    def get_student_uid_by_activity(self, activity_id: str) -> Optional[str]:
        """
        Retorna o uid Firebase Auth do aluno dono da atividade.

        Usado pelo aspecto A05 para determinar o destinatário da notificação
        de resultado da validação.
        """
        activity = self.get_by_id(activity_id)
        if not activity:
            return None
        student_id = activity.get("student_id")
        if not student_id:
            return None
        doc = self._db().collection("students").document(student_id).get()
        if not doc.exists:
            return None
        return doc.to_dict().get("uid")

    def get_activity_type(self, tipo_id: str) -> Optional[dict]:
        """
        Retorna os metadados do tipo de atividade (pontuacao_base, categoria, etc.).

        Usado pelo service para determinar créditos a contabilizar quando a
        coordenação não fornece creditos_concedidos explícitos.
        """
        doc = self._db().collection("activity_types").document(tipo_id).get()
        if not doc.exists:
            return None
        return {"id": doc.id, **doc.to_dict()}

    def count_approved_productions(self, student_id: str) -> int:
        """
        Conta produções bibliográficas aprovadas do aluno.

        Usado para decidir se o fato producao_bibliografica_validada deve
        ser gerado após uma aprovação.
        """
        docs = (
            self._db()
            .collection(self.COLLECTION)
            .where("student_id", "==", student_id)
            .where("categoria", "==", "producao_bibliografica")
            .where("status", "==", "aprovada")
            .stream()
        )
        return sum(1 for _ in docs)
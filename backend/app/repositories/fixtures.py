"""
Repositório em memória que implementa InferenceDataSource com dados representativos.

Responsabilidades:
- Fornecer dados de alunos, programa, atividades, tasks e produções com as mesmas
  assinaturas de método que os repositórios reais do Firestore exporão, de forma que
  InferenceService e ChecklistService não dependam da origem.
- Cobrir três cenários: aluno apto (fase_defesa), aluno em risco (com conflito
  situacao_registrada != situacao_inferida) e aluno regular/qualificado.

Restrição: sem lógica de negócio — apenas dados e leitura.
"""

from __future__ import annotations

import uuid
from typing import Any

_PROGRAM: dict[str, Any] = {
    "id": "prog_default",
    "min_creditos_basico": 12,
    "min_creditos_especifico": 8,
    "max_creditos_tecnologico": 4,
    "min_creditos_total": 24,
    "max_prorrogacoes": 2,
    "relevancia_pesos": {"A1": 2.0, "A2": 1.5, "B": 1.0, "C": 0.5},
}

# aluno_apto    — prazo no futuro, todos os requisitos cumpridos.
# aluno_risco   — prazo já expirado (prazo_estourado) + créditos insuficientes.
# aluno_regular — prazo no futuro, qualificado, mas sem produção/plano concluído.
_STUDENTS: dict[str, dict[str, Any]] = {
    "aluno_apto": {
        "id": "aluno_apto",
        "nome": "Ana Apta",
        "programa_id": "prog_default",
        "situacao_registrada": "fase_defesa",
        "data_ingresso": "2022-03-01",
        "prazo_final": "2027-03-01",
        "prazo_qualificacao": "2023-09-01",
        "proficiencia_comprovada": True,
        "proficiencia_data": "2022-08-10",
        "qualificacao_aprovada": True,
        "qualificacao_data": "2023-08-15",
    },
    "aluno_risco": {
        "id": "aluno_risco",
        "nome": "Rui Risco",
        "programa_id": "prog_default",
        "situacao_registrada": "regular",  # diverge da inferida (em_risco) → conflito
        "data_ingresso": "2019-03-01",
        "prazo_final": "2024-03-01",
        "prazo_qualificacao": "2020-09-01",
        "proficiencia_comprovada": False,
        "proficiencia_data": None,
        "qualificacao_aprovada": False,
        "qualificacao_data": None,
    },
    "aluno_regular": {
        "id": "aluno_regular",
        "nome": "Rita Regular",
        "programa_id": "prog_default",
        "situacao_registrada": "qualificado",
        "data_ingresso": "2024-03-01",
        "prazo_final": "2028-03-01",
        "prazo_qualificacao": "2025-09-01",
        "proficiencia_comprovada": True,
        "proficiencia_data": "2024-09-01",
        "qualificacao_aprovada": True,
        "qualificacao_data": "2025-08-20",
    },
}

# Atividades aprovadas por aluno. grupo ∈ {basico, especifico, tecnologico}.
_ACTIVITIES: dict[str, list[dict[str, Any]]] = {
    "aluno_apto": [
        {"id": "atv_apto_b", "grupo": "basico", "creditos": 14, "comprovante": "url/b", "tipo_ativo": True, "data": "2022-06-01"},
        {"id": "atv_apto_e", "grupo": "especifico", "creditos": 10, "comprovante": "url/e", "tipo_ativo": True, "data": "2022-09-01"},
        {"id": "atv_apto_t", "grupo": "tecnologico", "creditos": 3, "comprovante": "url/t", "tipo_ativo": True, "data": "2023-01-15"},
    ],
    "aluno_risco": [
        {"id": "atv_risco_b", "grupo": "basico", "creditos": 6, "comprovante": "url/b", "tipo_ativo": True, "data": "2019-06-01"},
        {"id": "atv_risco_e", "grupo": "especifico", "creditos": 4, "comprovante": "", "tipo_ativo": True, "data": "2019-09-01"},
        {"id": "atv_risco_t", "grupo": "tecnologico", "creditos": 1, "comprovante": "url/t", "tipo_ativo": False, "data": "2020-01-15"},
    ],
    "aluno_regular": [
        {"id": "atv_reg_b", "grupo": "basico", "creditos": 14, "comprovante": "url/b", "tipo_ativo": True, "data": "2024-06-01"},
        {"id": "atv_reg_e", "grupo": "especifico", "creditos": 9, "comprovante": "url/e", "tipo_ativo": True, "data": "2024-09-01"},
        {"id": "atv_reg_t", "grupo": "tecnologico", "creditos": 2, "comprovante": "url/t", "tipo_ativo": True, "data": "2025-01-15"},
    ],
}

# Tasks do plano por aluno. is_defesa=True são etapas excluídas do cálculo de plano_concluido.
_TASKS: dict[str, list[dict[str, Any]]] = {
    "aluno_apto": [
        {"id": "t1", "is_defesa": False, "concluida": True},
        {"id": "t2", "is_defesa": False, "concluida": True},
        {"id": "t3", "is_defesa": False, "concluida": True},
        {"id": "t_def", "is_defesa": True, "concluida": False},
    ],
    "aluno_risco": [
        {"id": "t1", "is_defesa": False, "concluida": False},
        {"id": "t2", "is_defesa": False, "concluida": False},
        {"id": "t3", "is_defesa": False, "concluida": False},
    ],
    "aluno_regular": [
        {"id": "t1", "is_defesa": False, "concluida": True},
        {"id": "t2", "is_defesa": False, "concluida": True},
        {"id": "t3", "is_defesa": False, "concluida": True},
        {"id": "t4", "is_defesa": False, "concluida": True},
        {"id": "t5", "is_defesa": False, "concluida": False},
    ],
}

# Produções aprovadas por aluno.
_PRODUCTIONS: dict[str, list[dict[str, Any]]] = {
    "aluno_apto": [
        {"id": "p_apto1", "veiculo_id": "v_a1", "nivel": "A1", "pontuacao_base": 10, "bibliografica": True},
    ],
    "aluno_risco": [],
    "aluno_regular": [
        {"id": "p_reg1", "veiculo_id": "v_b", "nivel": "B", "pontuacao_base": 8, "bibliografica": False},
    ],
}


class FixtureRepository:
    """Fonte de dados em memória que implementa o contrato InferenceDataSource.

    Cada método espelha a assinatura que o repositório real do Firestore exporá, mantendo o
    InferenceService agnóstico à origem dos dados.
    """

    def __init__(self) -> None:
        self._inferred_status: dict[str, list[dict[str, Any]]] = {}

    async def get_student(self, student_id: str) -> dict[str, Any] | None:
        """Retorna o documento do aluno, ou None se não existir."""
        student = _STUDENTS.get(student_id)
        return dict(student) if student else None

    async def get_program(self, programa_id: str) -> dict[str, Any] | None:
        """Retorna a configuração do programa, ou None se não existir."""
        if programa_id == _PROGRAM["id"]:
            return dict(_PROGRAM)
        return None

    async def get_approved_activities(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as atividades aprovadas do aluno."""
        return [dict(a) for a in _ACTIVITIES.get(student_id, [])]

    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as tasks do plano de trabalho do aluno."""
        return [dict(t) for t in _TASKS.get(student_id, [])]

    async def get_approved_productions(self, student_id: str) -> list[dict[str, Any]]:
        """Retorna as produções aprovadas do aluno."""
        return [dict(p) for p in _PRODUCTIONS.get(student_id, [])]

    async def save_inferred_status(self, student_id: str, snapshot: dict[str, Any]) -> str:
        """Persiste um snapshot imutável e atualiza situacao_inferida; retorna o snapshot_id."""
        snapshot_id = uuid.uuid4().hex
        self._inferred_status.setdefault(student_id, []).append(
            {"id": snapshot_id, **snapshot}
        )
        if student_id in _STUDENTS:
            _STUDENTS[student_id]["situacao_inferida"] = snapshot.get("situacao_inferida")
        return snapshot_id

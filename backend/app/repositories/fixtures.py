"""
Repositório em memória que implementa InferenceDataSource com dados representativos.

Responsabilidades:
- Fornecer dados de alunos, programa, atividades, tasks e produções com as mesmas
  assinaturas de método que os repositórios reais do Firestore exporão, de forma que
  InferenceService e ChecklistService não dependam da origem.
- Cobrir sete cenários de aluno:
    - aluno_apto        — prazo no futuro, todos os requisitos cumpridos.
    - aluno_risco       — prazo expirado (prazo_estourado) + créditos insuficientes.
    - aluno_regular     — prazo no futuro, qualificado, mas sem produção/plano concluído.
    - aluno_recem       — primeiro dia, 0 créditos: nenhum flag de risco deve disparar.
    - aluno_credito_risco — metade do prazo sem créditos: creditos_insuficientes ativo.
    - aluno_qual_risco  — prazo_qualificacao < 90 dias e qualificação pendente.
    - aluno_plano_risco — ~75% do prazo decorrido com plano 0% concluído.

Restrição: sem lógica de negócio — apenas dados e leitura.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from backend.app.models.vehicle import PESO_POR_NIVEL

_TODAY = date.today()
from backend.app.repositories.work_plan_repository import WorkPlanRepository


def _iso(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


_PROGRAM: dict[str, Any] = {
    "id": "prog_default",
    "creditos_grupo_basico_min": 12,
    "creditos_grupo_especifico_min": 8,
    "creditos_grupo_tecnologico_max": 4,
    "creditos_total_min": 24,
    "max_prorrogacoes": 2,
    "relevancia_pesos": dict(PESO_POR_NIVEL),
}

# aluno_apto         — prazo no futuro, todos os requisitos cumpridos.
# aluno_risco        — prazo já expirado (prazo_estourado) + créditos insuficientes.
# aluno_regular      — prazo no futuro, qualificado, mas sem produção/plano concluído.
# aluno_recem        — primeiro dia do programa, 0 créditos: nenhum flag de risco.
# aluno_credito_risco — metade do prazo decorrida, 0 créditos: creditos_insuficientes.
# aluno_qual_risco   — prazo_qualificacao < 90 dias e qualificação pendente.
# aluno_plano_risco  — ~75% do prazo decorrido, plano 0% concluído: plano_atrasado.
_STUDENTS: dict[str, dict[str, Any]] = {
    "aluno_apto": {
        "id": "aluno_apto",
        "nome": "Ana Apta",
        "programa_id": "prog_default",
        "situacao_registrada": "em_fase_de_defesa",
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
    "aluno_recem": {
        "id": "aluno_recem",
        "nome": "Novo Aluno",
        "programa_id": "prog_default",
        "situacao_registrada": "regular",
        # Primeiro dia do programa: fração decorrida = 0 → nenhum risco de crédito.
        "data_ingresso": _iso(0),
        "prazo_final": _iso(730),
        "prazo_qualificacao": _iso(545),
        "proficiencia_comprovada": False,
        "proficiencia_data": None,
        "qualificacao_aprovada": False,
        "qualificacao_data": None,
    },
    "aluno_credito_risco": {
        "id": "aluno_credito_risco",
        "nome": "Carlos Crédito",
        "programa_id": "prog_default",
        "situacao_registrada": "regular",
        # ~Metade do prazo decorrida (fração 0.5), 0 créditos → creditos_insuficientes.
        "data_ingresso": _iso(-365),
        "prazo_final": _iso(365),
        "prazo_qualificacao": _iso(900),
        "proficiencia_comprovada": True,
        "proficiencia_data": "2025-09-01",
        "qualificacao_aprovada": True,
        "qualificacao_data": "2026-03-01",
    },
    "aluno_qual_risco": {
        "id": "aluno_qual_risco",
        "nome": "Queiroz Qualificação",
        "programa_id": "prog_default",
        "situacao_registrada": "regular",
        # Prazo de qualificação a 60 dias (< 90) com qualificação pendente → risco de qual.
        "data_ingresso": _iso(-700),
        "prazo_final": _iso(180),
        "prazo_qualificacao": _iso(60),
        "proficiencia_comprovada": True,
        "proficiencia_data": "2024-09-01",
        "qualificacao_aprovada": False,
        "qualificacao_data": None,
    },
    "aluno_plano_risco": {
        "id": "aluno_plano_risco",
        "nome": "Pedro Plano",
        "programa_id": "prog_default",
        "situacao_registrada": "regular",
        # ~75% do prazo decorrido (fração 0.75) com plano 0% concluído → plano_atrasado.
        "data_ingresso": _iso(-547),
        "prazo_final": _iso(183),
        "prazo_qualificacao": _iso(900),
        "proficiencia_comprovada": True,
        "proficiencia_data": "2025-03-01",
        "qualificacao_aprovada": True,
        "qualificacao_data": "2025-09-01",
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
    "aluno_recem": [],
    "aluno_credito_risco": [],
    # 15 básico + 9 específico = 24 créditos (≥ min_total=24 e > expected ~19.2 com fracao ~0.80).
    "aluno_qual_risco": [
        {"id": "atv_qr_b", "grupo": "basico", "creditos": 15, "comprovante": "url/b", "tipo_ativo": True, "data": _iso(-650)},
        {"id": "atv_qr_e", "grupo": "especifico", "creditos": 9, "comprovante": "url/e", "tipo_ativo": True, "data": _iso(-600)},
    ],
    # 15 básico + 9 específico = 24 créditos (≥ min_total=24 e > expected ~18 com fracao ~0.75).
    "aluno_plano_risco": [
        {"id": "atv_pr_b", "grupo": "basico", "creditos": 15, "comprovante": "url/b", "tipo_ativo": True, "data": _iso(-500)},
        {"id": "atv_pr_e", "grupo": "especifico", "creditos": 9, "comprovante": "url/e", "tipo_ativo": True, "data": _iso(-450)},
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
    "aluno_recem": [],
    "aluno_credito_risco": [],
    "aluno_qual_risco": [
        {"id": "t1", "is_defesa": False, "concluida": True},
        {"id": "t2", "is_defesa": False, "concluida": True},
        {"id": "t3", "is_defesa": False, "concluida": True},
    ],
    "aluno_plano_risco": [
        {"id": "t1", "is_defesa": False, "concluida": False},
        {"id": "t2", "is_defesa": False, "concluida": False},
        {"id": "t3", "is_defesa": False, "concluida": False},
    ],
}

# Produções aprovadas por aluno.
_PRODUCTIONS: dict[str, list[dict[str, Any]]] = {
    "aluno_apto": [
        {"id": "p_apto1", "veiculo_id": "v_a1", "nivel": "A1", "pontuacao_base": 10, "bibliografica": True},
    ],
    "aluno_risco": [],
    "aluno_regular": [
        {"id": "p_reg1", "veiculo_id": "v_b1", "nivel": "B1", "pontuacao_base": 8, "bibliografica": False},
    ],
    "aluno_recem": [],
    "aluno_credito_risco": [],
    "aluno_qual_risco": [],
    "aluno_plano_risco": [],
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
        work_plan_tasks = await WorkPlanRepository().get_plan_tasks(student_id)
        if work_plan_tasks:
            return work_plan_tasks
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

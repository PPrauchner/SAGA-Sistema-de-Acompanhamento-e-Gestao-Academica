"""
Script de seed para popular o Firestore com dados de configuração iniciais do SAGA.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Criar o documento departments/dept_default (ADR-0004) — pai estrutural do programa.
- Criar o documento programs/prog_default com as configurações do PPGCC: duracao_meses=24,
  creditos_grupo_basico_min=12, creditos_grupo_especifico_min=8,
  creditos_grupo_tecnologico_max=4, creditos_total_min=24, max_prorrogacoes=1,
  duracao_prorrogacao_meses=6, meses_ate_qualificacao=12, departamento_id=dept_default.
- Popular programs/prog_default/qualis_weights/ com os níveis de relevância default
  (escala Qualis Único monotônica A1–A8 + fallback): A1 (1.0), A2 (0.9), A3 (0.8),
  A4 (0.7), A5 (0.6), A6 (0.5), A7 (0.4), A8 (0.3), SC (0.2).
- Criar a versão inicial (bootstrap) de pesos Qualis em
  programs/prog_default/qualis_weights/ a partir de PESO_POR_NIVEL — fonte versionada da
  RL05 (ADR-0003), vigente desde uma data-base que cobre toda produção histórica.
- Popular activity_types/ com os 6 tipos de atividade padrão: Artigo Publicado (específico,
  pontuacao_base=10), Artigo Submetido (específico, 5), Disciplina Cursada (básico, 4),
  Estágio Docência (básico, 2), Software Registrado (tecnológico, 3, limite=4),
  Participação Banca (básico, 1).
- Executar uma única vez no setup do ambiente de desenvolvimento ou produção.
- Idempotente: verificar existência de documentos antes de criar para evitar duplicatas.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.firebase import shutdown_firebase  # noqa: E402
from backend.app.models.vehicle import PESO_POR_NIVEL  # noqa: E402
from backend.app.models.work_plan import STATUS_CONCLUIDO  # noqa: E402
from backend.app.repositories.firebase_repository import (
    FirebaseRepository,
)  # noqa: E402
from backend.app.repositories.work_plan_repository import (
    WorkPlanRepository,
)  # noqa: E402

PROGRAM_ID = "prog_default"
DEPARTMENT_ID = "dept_default"
SEED_USER_ID = "seed_firestore"
SEED_STUDENT_ID = "seed_aluno_exemplo"

DEPARTMENT_DEFAULT: dict[str, Any] = {
    "nome": "Departamento Padrão",
    "instituicao": "UNIPAMPA",
}

# Versão inicial dos pesos Qualis. O id é fixo para idempotência; vigente_desde usa uma
# data-base bem anterior para que qualquer produção (mesmo histórica) resolva esta versão.
QUALIS_WEIGHTS_BOOTSTRAP_ID = "bootstrap"
QUALIS_WEIGHTS_BASELINE_DATE = datetime(2000, 1, 1, tzinfo=timezone.utc)

PROGRAM_DEFAULT: dict[str, Any] = {
    "nome": "PPGCC — Programa de Pós-Graduação em Ciência da Computação",
    "instituicao": "UNIPAMPA",
    "departamento_id": DEPARTMENT_ID,
    "duracao_meses": 24,
    "creditos_grupo_basico_min": 12,
    "creditos_grupo_especifico_min": 8,
    "creditos_grupo_tecnologico_max": 4,
    "creditos_total_min": 24,
    "max_prorrogacoes": 1,
    "duracao_prorrogacao_meses": 6,
    "meses_ate_qualificacao": 12,
}

VEHICLE_LEVELS_DEFAULT: dict[str, dict[str, Any]] = {
    f"v_placeholder_{nivel.lower()}": {
        "veiculo_id": f"v_placeholder_{nivel.lower()}",
        "nivel": nivel,
        "peso": peso,
    }
    for nivel, peso in PESO_POR_NIVEL.items()
}

ACTIVITY_TYPES_DEFAULT: dict[str, dict[str, Any]] = {
    "artigo_publicado": {
        "nome": "Artigo Publicado",
        "categoria": "especifico",
        "pontuacao_base": 10.0,
    },
    "artigo_submetido": {
        "nome": "Artigo Submetido",
        "categoria": "especifico",
        "pontuacao_base": 5.0,
    },
    "disciplina_cursada": {
        "nome": "Disciplina Cursada",
        "categoria": "basico",
        "pontuacao_base": 4.0,
    },
    "estagio_docencia": {
        "nome": "Estágio Docência",
        "categoria": "basico",
        "pontuacao_base": 2.0,
    },
    "software_registrado": {
        "nome": "Software Registrado",
        "categoria": "tecnologico",
        "pontuacao_base": 3.0,
        "limite_maximo_creditos": 4.0,
    },
    "participacao_banca": {
        "nome": "Participação Banca",
        "categoria": "basico",
        "pontuacao_base": 1.0,
    },
}


def _seed_student(now: datetime) -> dict[str, Any]:
    """Documento minimo de um aluno real para acompanhar o plano de exemplo."""
    return {
        "uid": SEED_STUDENT_ID,
        "nome": "Aluno Exemplo (seed)",
        "email": "aluno.exemplo@example.com",
        "matricula": "0000000",
        "orientador_id": None,
        "coorientador_id": None,
        "programa_id": PROGRAM_ID,
        "nivel": "mestrado",
        "data_ingresso": datetime(2025, 3, 1, tzinfo=timezone.utc),
        "prazo_final": datetime(2027, 3, 1, tzinfo=timezone.utc),
        "situacao_registrada": "regular",
        "situacao_inferida": "regular",
        "proficiencia_comprovada": False,
        "qualificacao_aprovada": False,
        "criado_em": now,
        "atualizado_em": now,
        "atualizado_por": SEED_USER_ID,
    }


async def _seed_example_work_plan(now: datetime) -> int:
    """Cria, de forma idempotente, um plano de exemplo para o aluno real de seed.

    Cria o aluno SEED_STUDENT_ID se ausente e, se ele ainda nao tiver plano, monta um
    plano com uma etapa e duas tasks (uma concluida, uma pendente) para que dashboards
    e a pagina de Plano de Trabalho exibam progresso real.

    Args:
        now: Timestamp de auditoria.

    Returns:
        Numero de planos criados (0 ou 1).
    """
    students = FirebaseRepository("students")
    await _create_if_missing(students, SEED_STUDENT_ID, _seed_student(now))

    work_plan = WorkPlanRepository()
    if await work_plan.get_plan(SEED_STUDENT_ID) is not None:
        return 0

    plan_id = await work_plan.create_plan(
        SEED_STUDENT_ID,
        {
            "titulo": "Plano de trabalho de exemplo",
            "data_inicio": datetime(2025, 3, 1, tzinfo=timezone.utc),
            "data_fim_prevista": datetime(2027, 3, 1, tzinfo=timezone.utc),
            "descricao": "Plano de exemplo gerado pelo seed.",
        },
    )
    stage_id = await work_plan.create_stage(
        plan_id,
        {
            "nome": "Revisao bibliografica",
            "ordem": 1,
            "data_inicio": datetime(2025, 3, 1, tzinfo=timezone.utc),
            "data_fim": datetime(2025, 8, 1, tzinfo=timezone.utc),
        },
    )
    concluida_id = await work_plan.create_task(
        stage_id,
        {
            "titulo": "Levantamento bibliografico",
            "descricao": "",
            "prazo": datetime(2025, 6, 1, tzinfo=timezone.utc),
            "prioridade": "alta",
        },
    )
    await work_plan.update_task(concluida_id, {"status": STATUS_CONCLUIDO, "progresso_percentual": 100.0})
    await work_plan.create_task(
        stage_id,
        {
            "titulo": "Sintese da literatura",
            "descricao": "",
            "prazo": datetime(2025, 8, 1, tzinfo=timezone.utc),
            "prioridade": "media",
        },
    )
    return 1


async def _create_if_missing(
    repository: FirebaseRepository,
    doc_id: str,
    data: dict[str, Any],
) -> bool:
    """Cria o documento com id explícito se ele ainda não existir (idempotente).

    Args:
        repository: Repositório já fixado na coleção (ou path de subcoleção) alvo.
        doc_id: Id explícito do documento.
        data: Conteúdo a persistir.

    Returns:
        True se o documento foi criado, False se já existia.
    """
    if await repository.get(doc_id) is not None:
        return False

    await repository.set(doc_id, data)
    return True


async def seed_firestore() -> dict[str, int]:
    now = datetime.now(timezone.utc)
    departments = FirebaseRepository("departments")
    programs = FirebaseRepository("programs")
    vehicle_levels = FirebaseRepository(f"programs/{PROGRAM_ID}/vehicle_levels")
    qualis_weights = FirebaseRepository(f"programs/{PROGRAM_ID}/qualis_weights")
    activity_types = FirebaseRepository("activity_types")

    created = {
        "departments": 0,
        "programs": 0,
        "vehicle_levels": 0,
        "qualis_weights": 0,
        "activity_types": 0,
        "work_plans": 0,
    }

    if await _create_if_missing(
        departments,
        DEPARTMENT_ID,
        {**DEPARTMENT_DEFAULT, "criado_em": now, "atualizado_em": now},
    ):
        created["departments"] += 1

    if await _create_if_missing(
        programs, PROGRAM_ID, {**PROGRAM_DEFAULT, "criado_em": now, "atualizado_em": now}
    ):
        created["programs"] += 1

    for doc_id, data in VEHICLE_LEVELS_DEFAULT.items():
        payload = {**data, "atualizado_por": SEED_USER_ID, "atualizado_em": now}
        if await _create_if_missing(vehicle_levels, doc_id, payload):
            created["vehicle_levels"] += 1

    qualis_bootstrap = {
        "pesos": dict(PESO_POR_NIVEL),
        "vigente_desde": QUALIS_WEIGHTS_BASELINE_DATE,
        "alterado_por": SEED_USER_ID,
        "alterado_em": now,
    }
    if await _create_if_missing(
        qualis_weights, QUALIS_WEIGHTS_BOOTSTRAP_ID, qualis_bootstrap
    ):
        created["qualis_weights"] += 1

    for doc_id, data in ACTIVITY_TYPES_DEFAULT.items():
        payload = {
            "limite_maximo_creditos": None,
            "exige_comprovante": True,
            "permite_multiplas": True,
            "ativo": True,
            "programa_id": PROGRAM_ID,
            "criado_por": SEED_USER_ID,
            "criado_em": now,
            "atualizado_em": now,
            **data,
        }
        if await _create_if_missing(activity_types, doc_id, payload):
            created["activity_types"] += 1

    created["work_plans"] += await _seed_example_work_plan(now)

    return created


def main() -> None:
    try:
        created = asyncio.run(seed_firestore())
    finally:
        shutdown_firebase()

    print("Seed Firestore concluído.")
    print(f"departments criados: {created['departments']}")
    print(f"programs criados: {created['programs']}")
    print(f"vehicle_levels criados: {created['vehicle_levels']}")
    print(f"qualis_weights criados: {created['qualis_weights']}")
    print(f"activity_types criados: {created['activity_types']}")
    print(f"work_plans criados: {created['work_plans']}")


if __name__ == "__main__":
    main()

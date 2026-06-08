"""
Script de seed para popular o Firestore com dados de configuração iniciais do SAGA.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Criar o documento programs/prog_default com as configurações do PPGCC: duracao_meses=24,
  creditos_grupo_basico_min=12, creditos_grupo_especifico_min=8,
  creditos_grupo_tecnologico_max=4, creditos_total_min=24, max_prorrogacoes=1,
  duracao_prorrogacao_meses=6, meses_ate_qualificacao=12.
- Popular programs/prog_default/vehicle_levels/ com os 4 níveis de relevância padrão:
  A1 (peso 2.0), A2 (peso 1.5), B (peso 1.0), C (peso 0.5).
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
from pathlib import Path
from typing import Any

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.firebase import shutdown_firebase  # noqa: E402
from backend.app.repositories.firebase_repository import (
    FirebaseRepository,
)  # noqa: E402

PROGRAM_ID = "prog_default"
SEED_USER_ID = "seed_firestore"

PROGRAM_DEFAULT: dict[str, Any] = {
    "nome": "PPGCC — Programa de Pós-Graduação em Ciência da Computação",
    "instituicao": "UNIPAMPA",
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
    "v_placeholder_a1": {"veiculo_id": "v_placeholder_a1", "nivel": "A1", "peso": 2.0},
    "v_placeholder_a2": {"veiculo_id": "v_placeholder_a2", "nivel": "A2", "peso": 1.5},
    "v_placeholder_b": {"veiculo_id": "v_placeholder_b", "nivel": "B", "peso": 1.0},
    "v_placeholder_c": {"veiculo_id": "v_placeholder_c", "nivel": "C", "peso": 0.5},
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


async def _exists(repository: FirebaseRepository, collection: str, doc_id: str) -> bool:
    try:
        await repository.get(collection, doc_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            return False
        raise
    return True


async def _create_if_missing(
    repository: FirebaseRepository,
    collection: str,
    doc_id: str,
    data: dict[str, Any],
) -> bool:
    if await _exists(repository, collection, doc_id):
        return False

    await repository.create(collection, data, doc_id=doc_id)
    return True


async def seed_firestore() -> dict[str, int]:
    repository = FirebaseRepository()
    created = {
        "programs": 0,
        "vehicle_levels": 0,
        "activity_types": 0,
    }

    if await _create_if_missing(repository, "programs", PROGRAM_ID, PROGRAM_DEFAULT):
        created["programs"] += 1

    vehicle_levels_collection = f"programs/{PROGRAM_ID}/vehicle_levels"
    for doc_id, data in VEHICLE_LEVELS_DEFAULT.items():
        payload = {**data, "atualizado_por": SEED_USER_ID}
        if await _create_if_missing(
            repository, vehicle_levels_collection, doc_id, payload
        ):
            created["vehicle_levels"] += 1

    for doc_id, data in ACTIVITY_TYPES_DEFAULT.items():
        payload = {
            "limite_maximo_creditos": None,
            "exige_comprovante": True,
            "permite_multiplas": True,
            "ativo": True,
            "programa_id": PROGRAM_ID,
            "criado_por": SEED_USER_ID,
            **data,
        }
        if await _create_if_missing(repository, "activity_types", doc_id, payload):
            created["activity_types"] += 1

    await repository.get("programs", PROGRAM_ID)
    return created


def main() -> None:
    try:
        created = asyncio.run(seed_firestore())
    finally:
        shutdown_firebase()

    print("Seed Firestore concluído.")
    print(f"programs criados: {created['programs']}")
    print(f"vehicle_levels criados: {created['vehicle_levels']}")
    print(f"activity_types criados: {created['activity_types']}")


if __name__ == "__main__":
    main()

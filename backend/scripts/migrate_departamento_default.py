"""
Migração one-off: semeia um Departamento default e aponta os programas existentes
para ele (ADR-0004 — Departamento como pai estrutural do Programa).

Contexto: `programa.departamento_id` passou a ser obrigatório. Programas criados antes
dessa mudança (hoje, apenas `programs/prog_default`) não têm esse campo. Este script:

- Cria (idempotente, id fixo) `departments/dept_default` se ainda não existir.
- Aponta todo documento em `programs/` sem `departamento_id` para `dept_default`.

Comportamento:
- Dry-run por padrão: apenas conta/lista o que seria alterado; não grava nada.
- Com --apply: grava as alterações.
- Idempotente: rodar de novo não altera nada (nenhum programa fica sem departamento_id).

Uso:
    python backend/scripts/migrate_departamento_default.py            # dry-run
    python backend/scripts/migrate_departamento_default.py --apply    # aplica
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.firebase import get_firestore_client, shutdown_firebase  # noqa: E402

DEFAULT_DEPARTMENT_ID = "dept_default"
DEFAULT_DEPARTMENT: dict[str, str] = {
    "nome": "Departamento Padrão",
    "instituicao": "UNIPAMPA",
}


def migrate(apply: bool) -> None:
    """Semeia o Departamento default e realinha programas sem departamento_id."""
    db = get_firestore_client()
    now = datetime.now(timezone.utc)

    print("== Migracao Departamento default (ADR-0004) ==\n")

    department_ref = db.collection("departments").document(DEFAULT_DEPARTMENT_ID)
    department_exists = department_ref.get().exists
    if department_exists:
        print(f"departments/{DEFAULT_DEPARTMENT_ID} ja existe — nada a criar.")
    else:
        print(f"departments/{DEFAULT_DEPARTMENT_ID} sera criado: {DEFAULT_DEPARTMENT}")
        if apply:
            department_ref.set(
                {**DEFAULT_DEPARTMENT, "criado_em": now, "atualizado_em": now}
            )

    programs_sem_departamento = [
        doc
        for doc in db.collection("programs").stream()
        if not (doc.to_dict() or {}).get("departamento_id")
    ]
    print(f"\nprogramas sem departamento_id: {len(programs_sem_departamento)}")
    for doc in programs_sem_departamento:
        print(f"  programs/{doc.id} -> departamento_id={DEFAULT_DEPARTMENT_ID!r}")
        if apply:
            doc.reference.update(
                {"departamento_id": DEFAULT_DEPARTMENT_ID, "atualizado_em": now}
            )

    print("\nAPLICADO." if apply else "\nDRY-RUN — nada foi alterado. Rode com --apply para gravar.")


if __name__ == "__main__":
    should_apply = "--apply" in sys.argv
    try:
        migrate(should_apply)
    finally:
        shutdown_firebase()

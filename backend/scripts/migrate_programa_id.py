"""
Migração one-off: realinha programa_id de "SAGA" para "prog_default" nas coleções raiz.

Contexto: dados de teste (alunos/produções e afins) foram criados sob programa_id="SAGA",
enquanto o coordenador e toda a configuração do programa (programs/prog_default,
vehicle_levels, qualis_weights) vivem sob "prog_default". Como get_productions_report é o
único relatório que filtra por programa (list_by_program/list_productions_by_program), esse
descasamento deixava o relatório de produção vazio. Este script alinha os documentos afetados.

Comportamento:
- Dry-run por padrão: apenas conta/lista o que seria alterado; não grava nada.
- Com --apply: grava programa_id="prog_default" nos documentos com programa_id="SAGA".
- Para a coleção users, além do doc Firestore, sincroniza os custom claims do Firebase Auth
  (mantendo role) e revoga refresh tokens, para que novos logins/produções não voltem a nascer
  sob "SAGA".
- Idempotente: rodar de novo não altera nada (não restam docs com "SAGA").

Uso:
    python backend/scripts/migrate_programa_id.py            # dry-run
    python backend/scripts/migrate_programa_id.py --apply    # aplica
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.firebase import (  # noqa: E402
    get_auth_client,
    get_firestore_client,
    shutdown_firebase,
)

SOURCE_PROGRAMA_ID = "SAGA"
TARGET_PROGRAMA_ID = "prog_default"

# Coleções raiz que carregam programa_id como FK lógica (data-model §1-4). A coleção programs/
# é identidade do tenant (keyed pelo próprio id) e não é migrada aqui.
ROOT_COLLECTIONS = [
    "users",
    "invites",
    "students",
    "advisors",
    "productions",
    "activity_types",
    "vehicles",
    "extensions",
    "transfer_requests",
    "coordination_transfers",
    "audit_logs",
    "notifications",
]


def migrate(apply: bool) -> None:
    """Realinha programa_id SOURCE→TARGET nas coleções raiz (dry-run se apply=False)."""
    db = get_firestore_client()
    total = 0
    affected_users: list[tuple[str, dict]] = []

    print(f"== Migracao programa_id {SOURCE_PROGRAMA_ID!r} -> {TARGET_PROGRAMA_ID!r} ==\n")
    for collection in ROOT_COLLECTIONS:
        docs = list(
            db.collection(collection)
            .where("programa_id", "==", SOURCE_PROGRAMA_ID)
            .stream()
        )
        total += len(docs)
        print(f"[{collection}] {len(docs)} doc(s) a alterar")
        for doc in docs:
            if collection == "users":
                affected_users.append((doc.id, doc.to_dict() or {}))
            if apply:
                doc.reference.update({"programa_id": TARGET_PROGRAMA_ID})

    # Visibilidade: quais program ids existem em programs/ e quais outros valores de
    # programa_id aparecem nas coleções raiz (anomalias além de SAGA).
    program_ids = [doc.id for doc in db.collection("programs").stream()]
    print(f"\nprograms/ existentes: {program_ids}")

    print("\n-- Outros programa_id (!= alvo) ainda presentes --")
    for collection in ROOT_COLLECTIONS:
        counts: dict[str, int] = {}
        for doc in db.collection(collection).stream():
            pid = (doc.to_dict() or {}).get("programa_id")
            counts[repr(pid)] = counts.get(repr(pid), 0) + 1
        distinct = {k: v for k, v in counts.items() if k != repr(TARGET_PROGRAMA_ID)}
        if distinct:
            print(f"[{collection}] {distinct}")

    # Sincroniza custom claims dos usuários afetados para não regredir no próximo login.
    if affected_users:
        print(f"\n-- {len(affected_users)} usuário(s) afetado(s): sincronização de claims --")
        auth = get_auth_client()
        for uid, data in affected_users:
            role = data.get("role")
            print(f"  users/{uid} role={role!r} -> claims programa_id={TARGET_PROGRAMA_ID!r}")
            if apply and role:
                auth.set_custom_user_claims(uid, {"role": role, "programa_id": TARGET_PROGRAMA_ID})
                auth.revoke_refresh_tokens(uid)

    print(f"\nTotal de docs com {SOURCE_PROGRAMA_ID!r}: {total}")
    print("APLICADO." if apply else "DRY-RUN — nada foi alterado. Rode com --apply para gravar.")


if __name__ == "__main__":
    should_apply = "--apply" in sys.argv
    try:
        migrate(should_apply)
    finally:
        shutdown_firebase()

"""
Resolver de uid -> nome para exibicao no read path.

Responsabilidades:
- resolve(uids): traduz um conjunto de uids em um mapa uid -> nome legivel, buscando
  apenas os documentos solicitados em users/ (get por uid, em paralelo) — sem reler a
  colecao inteira a cada chamada. Faz fallback para o email e, na ausencia deste, para o
  proprio uid, garantindo que a leitura sempre exibe algo util.
- Consumido exclusivamente por services de leitura (auditoria, historico de versoes) para
  substituir o id cru pelo nome na resposta de API. Nenhuma escrita: o id permanece a
  chave canonica em storage, FKs, claims e auditoria; este modulo so traduz na exibicao.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from backend.app.repositories.firebase_repository import FirebaseRepository


class UserNameResolver:
    """Traduz uids em nomes de exibicao a partir da colecao users/."""

    def __init__(self, user_repo: FirebaseRepository | None = None) -> None:
        self._users = user_repo or FirebaseRepository("users")

    async def resolve(self, uids: Iterable[str]) -> dict[str, str]:
        """Resolve os nomes de exibicao dos uids informados.

        Args:
            uids: uids a resolver. Valores falsy (None, "") sao ignorados.

        Returns:
            Mapa uid -> nome de exibicao, apenas para os uids conhecidos na colecao
            users/. O nome cai para email e depois para o proprio uid quando ausente.
            uids nao encontrados ficam de fora do mapa.
        """
        wanted = list({uid for uid in uids if uid})
        if not wanted:
            return {}

        users = await asyncio.gather(*(self._users.get(uid) for uid in wanted))
        return {
            uid: (user.get("nome") or user.get("email") or uid)
            for uid, user in zip(wanted, users)
            if user
        }

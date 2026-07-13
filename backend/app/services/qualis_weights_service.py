"""
Serviço de negócio dos pesos Qualis versionados por programa (fonte da RL05).

Responsabilidades:
- set_weights(): cria uma nova versão de pesos (nunca sobrescreve a anterior), carimbando
  vigente_desde/alterado_por/alterado_em. O escopo por programa é garantido por construção:
  o programa vem sempre do usuário autenticado.
- get_weights_at(): resolve o conjunto de pesos vigente em uma data — a versão de maior
  vigente_desde <= data; faz fallback para a escala default PESO_POR_NIVEL quando não há
  nenhuma versão aplicável (bootstrap).
- get_active_weights(): atalho para o conjunto vigente hoje.
- list_history(): retorna o histórico de versões (mais recente primeiro), enriquecendo cada
  versão com alterado_por_nome resolvido no read path a partir de alterado_por (uid).

Restrição: única camada que conhece a regra de resolução por data; o repositório apenas
persiste e lê.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.models.qualis_weights import QualisWeightsUpdate
from backend.app.models.vehicle import PESO_POR_NIVEL
from backend.app.repositories.qualis_weights_repository import QualisWeightsRepository
from backend.app.services.user_name_resolver import UserNameResolver


def _as_aware(value: Any) -> datetime:
    """Normaliza um valor de data/hora para datetime timezone-aware (UTC).

    Aceita o Timestamp do Firestore (datetime aware), datetime naive (assume UTC) e None
    (tratado como o início dos tempos, para nunca vencer a resolução).

    Args:
        value: Valor lido do documento (datetime, Timestamp Firestore ou None).

    Returns:
        datetime timezone-aware em UTC.
    """
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def resolve_weights_at(
    versions: list[dict[str, Any]],
    when: datetime,
) -> dict[str, float] | None:
    """Resolve o conjunto de pesos vigente em `when`, ou None se nenhuma versão se aplica.

    Função pura (sem I/O), compartilhada pelo QualisWeightsService e pelo InferenceService:
    seleciona a versão de maior vigente_desde que não ultrapassa `when`.

    Args:
        versions: Versões de pesos do programa (cada uma com pesos e vigente_desde).
        when: Momento de referência (ex: data de publicação da produção).

    Returns:
        Mapa nível -> peso da versão vigente, ou None se não houver versão aplicável.
    """
    aware_when = _as_aware(when)
    candidates = [v for v in versions if _as_aware(v.get("vigente_desde")) <= aware_when]
    if not candidates:
        return None
    best = max(candidates, key=lambda v: _as_aware(v.get("vigente_desde")))
    return dict(best.get("pesos") or {}) or None


class QualisWeightsService:
    """Serviço de negócio das versões de pesos Qualis de um programa."""

    def __init__(self, names: UserNameResolver | None = None) -> None:
        self._repo = QualisWeightsRepository()
        # Resolve alterado_por→nome na leitura do histórico (read path). Injetável em teste.
        self._names = names or UserNameResolver()

    async def set_weights(
        self,
        programa_id: str,
        alterado_por: str,
        data: QualisWeightsUpdate,
    ) -> dict[str, Any]:
        """Cria uma nova versão vigente dos pesos do programa.

        Args:
            programa_id: Programa do coordenador (escopo da configuração).
            alterado_por: uid do coordenador que altera os pesos.
            data: Conjunto completo de pesos validado.

        Returns:
            Dict com id da versão criada, vigente_desde (ISO) e os pesos aplicados.
        """
        now = datetime.now(timezone.utc)
        version = {
            "pesos": dict(data.pesos),
            "vigente_desde": now,
            "alterado_por": alterado_por,
            "alterado_em": now,
        }
        version_id = await self._repo.create_version(programa_id, version)
        return {
            "id": version_id,
            "vigente_desde": now.isoformat(),
            "pesos": version["pesos"],
        }

    async def get_weights_at(
        self,
        programa_id: str,
        when: datetime,
    ) -> dict[str, float]:
        """Resolve os pesos vigentes em `when` (versão de maior vigente_desde <= when).

        Args:
            programa_id: Programa cujos pesos se quer resolver.
            when: Momento de referência (ex: data de publicação da produção).

        Returns:
            Mapa nível -> peso vigente, ou a escala default PESO_POR_NIVEL se não houver
            versão aplicável.
        """
        versions = await self._repo.list_versions(programa_id)
        return resolve_weights_at(versions, when) or dict(PESO_POR_NIVEL)

    async def get_active_weights(self, programa_id: str) -> dict[str, float]:
        """Atalho para os pesos vigentes hoje."""
        return await self.get_weights_at(programa_id, datetime.now(timezone.utc))

    async def list_history(self, programa_id: str) -> list[dict[str, Any]]:
        """Retorna o histórico de versões de pesos, da mais recente para a mais antiga.

        Cada versão é enriquecida com `alterado_por_nome` (resolvido de `alterado_por` no
        read path); o uid `alterado_por` persistido permanece inalterado.
        """
        versions = await self._repo.list_versions(programa_id)
        versions.sort(key=lambda v: _as_aware(v.get("vigente_desde")), reverse=True)
        nomes = await self._names.resolve(v.get("alterado_por") for v in versions)
        for version in versions:
            version["alterado_por_nome"] = nomes.get(version.get("alterado_por"))
        return versions

"""
Veículo de publicação e escala de relevância Qualis (fonte de verdade dos pesos RL05).

Responsabilidades:
- Declarar RelevanceLevel: os 7 níveis canônicos do Qualis Único da CAPES.
- Declarar PESO_POR_NIVEL: a escala de pesos monotônica única consumida pela RL05,
  fonte de verdade para inference_repository, fixtures e seed_firestore.
"""

from __future__ import annotations

from typing import Literal

RelevanceLevel = Literal["A1", "A2", "A3", "A4", "B1", "B2", "SC"]

# Escala monotônica canônica da RL05 (decisão R1/R4, issue #133): estritamente
# decrescente — um nível superior sempre pondera mais que um inferior. 'SC'
# (Sem Classificação) é o peso de fallback para veículo sem nível configurado.
PESO_POR_NIVEL: dict[RelevanceLevel, float] = {
    "A1": 1.0,
    "A2": 0.85,
    "A3": 0.7,
    "A4": 0.55,
    "B1": 0.4,
    "B2": 0.3,
    "SC": 0.2,
}

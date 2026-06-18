"""
Testes da resolução de pontuação base de produções (ProductionService).

Cobre _resolve_pontuacao_base: artigo modulado por status_publicacao (publicado/aceito/
submetido) e tipos de base única (livro/capítulo). Função pura — sem acesso ao Firebase.
"""

from __future__ import annotations

import pytest

from backend.app.services.production_service import _resolve_pontuacao_base


@pytest.mark.parametrize(
    "status, esperado",
    [
        ("publicado", 1.0),
        ("aceito", 0.8),
        ("submetido", 0.3),
    ],
)
def test_artigo_varia_por_status(status: str, esperado: float) -> None:
    assert _resolve_pontuacao_base("artigo", status) == esperado


@pytest.mark.parametrize(
    "tipo, esperado",
    [
        ("livro", 1.0),
        ("capitulo", 0.6),
    ],
)
def test_tipo_base_unica_ignora_status(tipo: str, esperado: float) -> None:
    # Para livro/capítulo o status não altera a base.
    assert _resolve_pontuacao_base(tipo, "publicado") == esperado
    assert _resolve_pontuacao_base(tipo, "submetido") == esperado

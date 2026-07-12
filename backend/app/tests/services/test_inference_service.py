"""
Testes para InferenceService.

Responsabilidades:
- Verificar a integração entre o motor de inferência e a carga de dados.
- Garantir que mudanças nas configurações do programa (Issue #47) reflitam no status do aluno.
"""

from typing import Any

import pytest

from backend.app.models.program_config import DEFAULT_PROGRAM_CREDIT_CONFIG
from backend.app.services.inference_service import InferenceService
from backend.app.repositories.fixtures import FixtureRepository, _PROGRAM

@pytest.fixture
def anyio_backend():
    return 'asyncio'


class _ProgramOverrideRepository(FixtureRepository):
    def __init__(self, program: dict[str, Any]) -> None:
        super().__init__()
        self._program_override = program

    async def get_program(self, programa_id: str) -> dict[str, Any] | None:
        return {"id": programa_id, **self._program_override}

@pytest.mark.anyio
async def test_inference_reflects_program_config_change(monkeypatch):
    """
    Testa se a mudança na configuração do programa (Issue #47) altera a situação inferida.
    Cenário: aluno_regular tem 25 créditos totais (14 basico, 9 especifico, 2 tecnologico).
    Com min_creditos_total=24 (padrão) -> Regular.
    Com min_creditos_total=30 (nova config) -> Em Risco.
    """
    # 1. Setup com configuração padrão (24 créditos mínimos)
    # _PROGRAM em fixtures.py já tem creditos_total_min=24
    repo = FixtureRepository()
    service = InferenceService(data_source=repo)

    # 2. Primeira inferência: deve ser 'qualificado' (pois o fixture aluno_regular já qualificou)
    result_before = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")
    assert result_before.situacao_inferida == "qualificado"
    assert result_before.creditos_validos is True
    assert result_before.em_risco is False

    # 3. Alterar configuração do programa (Simulando Issue #47)
    # Usamos monkeypatch para alterar a constante no módulo de fixtures durante o teste
    monkeypatch.setitem(_PROGRAM, "creditos_total_min", 100)

    # 4. Segunda inferência: deve ser 'em_risco' pois o aluno tem apenas 25 créditos
    result_after = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")

    # 5. Asserções
    assert result_after.situacao_inferida == "em_risco"
    assert result_after.creditos_validos is False
    assert result_after.em_risco is True
    assert any("Créditos insuficientes (25/100)" in msg for msg in result_after.riscos_detectados)


@pytest.mark.anyio
async def test_defaults_canonicos_alimentam_fatos_checklist_e_riscos(monkeypatch):
    monkeypatch.setitem(DEFAULT_PROGRAM_CREDIT_CONFIG, "creditos_total_min", 80)
    repo = _ProgramOverrideRepository({})
    service = InferenceService(data_source=repo)

    result = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")

    assert result.checklist.creditos_minimos.minimo == 80
    assert any("Créditos insuficientes (25/80)" in msg for msg in result.riscos_detectados)
    assert any("min_creditos_total" in fact and "80" in fact for fact in result.fatos_usados)


@pytest.mark.anyio
async def test_configuracao_do_programa_sobrepoe_default_canonico(monkeypatch):
    monkeypatch.setitem(DEFAULT_PROGRAM_CREDIT_CONFIG, "creditos_total_min", 40)
    repo = _ProgramOverrideRepository({"creditos_total_min": 100})
    service = InferenceService(data_source=repo)

    result = await service.run_inference(student_id="aluno_regular", programa_id="prog_default")

    assert result.checklist.creditos_minimos.minimo == 100
    assert any("Créditos insuficientes (25/100)" in msg for msg in result.riscos_detectados)

@pytest.mark.anyio
async def test_aptidao_defesa_aluno_apto():
    """Verifica se o aluno_apto é inferido corretamente como em_fase_de_defesa."""
    repo = FixtureRepository()
    service = InferenceService(data_source=repo)

    result = await service.run_inference(student_id="aluno_apto", programa_id="prog_default")

    assert result.situacao_inferida == "em_fase_de_defesa"
    assert result.apto_defesa is True
    assert result.checklist.creditos_minimos.status == "cumprido"
    assert result.checklist.producao_validada.status == "cumprido"

@pytest.mark.anyio
async def test_inference_with_non_existent_student():
    """Garante que o serviço levanta erro para aluno inexistente."""
    from backend.app.services.inference_service import StudentNotFoundError

    repo = FixtureRepository()
    service = InferenceService(data_source=repo)

    with pytest.raises(StudentNotFoundError):
        await service.run_inference(student_id="inexistente", programa_id="prog_default")

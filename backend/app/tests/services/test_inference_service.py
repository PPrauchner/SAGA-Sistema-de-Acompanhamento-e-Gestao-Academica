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
from backend.app.repositories.inference_repository import InferenceRepository

@pytest.fixture
def anyio_backend():
    return 'asyncio'


class _ProgramOverrideRepository(FixtureRepository):
    def __init__(self, program: dict[str, Any]) -> None:
        super().__init__()
        self._program_override = program

    async def get_program(self, programa_id: str) -> dict[str, Any] | None:
        return {"id": programa_id, **self._program_override}


class _StubProgramsCollection:
    """Coleção programs/ falsa: devolve sempre o mesmo documento, sem tocar no Firestore."""

    def __init__(self, doc: dict[str, Any]) -> None:
        self._doc = doc

    async def get(self, doc_id: str) -> dict[str, Any]:
        return dict(self._doc)


class _RealProgramDataSource(FixtureRepository):
    """FixtureRepository cujo get_program vem do InferenceRepository real.

    Exercita a costura repositório → serviço: é ali que os nomes de campo da configuração
    do programa precisam casar. Só a coleção programs/ é stubada; o resto vem das fixtures.
    """

    def __init__(self, program_doc: dict[str, Any]) -> None:
        super().__init__()
        self._inference_repo = InferenceRepository()
        self._inference_repo._programs = _StubProgramsCollection(program_doc)

    async def get_program(self, programa_id: str) -> dict[str, Any] | None:
        return await self._inference_repo.get_program(programa_id)

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
async def test_program_config_overrides_defaults_nos_quatro_requisitos():
    """Os 4 requisitos de crédito seguem a configuração do programa, não os defaults.

    aluno_regular tem 14 básico / 9 específico / 2 tecnológico = 25 totais, o que cumpre
    os 4 requisitos nos defaults (12/8/4/24). Com um programa que exige 20/15/1/40, os 4
    passam a não ser cumpridos — se os limites do programa fossem ignorados, o checklist
    ainda mostraria os defaults e creditos_validos continuaria True.
    """
    program_doc = {
        "id": "prog_exigente",
        "creditos_grupo_basico_min": 20,
        "creditos_grupo_especifico_min": 15,
        "creditos_grupo_tecnologico_max": 1,
        "creditos_total_min": 40,
    }
    service = InferenceService(data_source=_RealProgramDataSource(program_doc))

    result = await service.run_inference(student_id="aluno_regular", programa_id="prog_exigente")

    checklist = result.checklist
    assert checklist.creditos_grupo_basico.minimo == 20
    assert checklist.creditos_grupo_especifico.minimo == 15
    assert checklist.creditos_grupo_tecnologico.maximo == 1
    assert checklist.creditos_minimos.minimo == 40

    assert checklist.creditos_grupo_basico.status != "cumprido"
    assert checklist.creditos_grupo_especifico.status != "cumprido"
    assert checklist.creditos_grupo_tecnologico.status != "cumprido"
    assert checklist.creditos_minimos.status != "cumprido"

    assert result.creditos_validos is False


@pytest.mark.anyio
async def test_mensagem_de_risco_usa_total_minimo_do_programa():
    """A mensagem de créditos insuficientes cita o mínimo do programa, não o default.

    aluno_credito_risco tem 0 créditos com metade do prazo decorrida, então a flag de risco
    dispara; o denominador da mensagem deve vir da configuração (40), não do default (24).
    """
    program_doc = {"id": "prog_exigente", "creditos_total_min": 40}
    service = InferenceService(data_source=_RealProgramDataSource(program_doc))

    result = await service.run_inference(
        student_id="aluno_credito_risco", programa_id="prog_exigente"
    )

    assert any("Créditos insuficientes (0/40)" in msg for msg in result.riscos_detectados)


@pytest.mark.anyio
async def test_inference_with_non_existent_student():
    """Garante que o serviço levanta erro para aluno inexistente."""
    from backend.app.services.inference_service import StudentNotFoundError

    repo = FixtureRepository()
    service = InferenceService(data_source=repo)

    with pytest.raises(StudentNotFoundError):
        await service.run_inference(student_id="inexistente", programa_id="prog_default")

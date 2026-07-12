"""
Testes do ReportService — agregação dos cinco relatórios gerenciais da coordenação.

Usa repositórios fake injetados via construtor (StudentRepository, AdvisorRepository,
ProductionRepository, ActivityRepository), sem acesso real ao Firestore. Cobre alunos em
risco com razões, agrupamento por situação e por orientador, tempo de integralização e
produção creditada por aluno/orientador.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.services.report_service import ReportService

# Programa do solicitante usado nos testes do relatório de produção (escopo US-AN06).
_PROG = "prog_default"


class _FakeStudentRepository:
    """Fake de StudentRepository: lista alunos e snapshots inferred_status em memória."""

    def __init__(
        self,
        students: list[dict[str, Any]],
        snapshots: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self._students = students
        self._snapshots = snapshots or {}

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(student) for student in self._students]

    async def list_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            dict(student)
            for student in self._students
            if student.get("programa_id") == programa_id
        ]

    async def list_subcollection(self, doc_id: str, subcollection: str) -> list[dict[str, Any]]:
        return [dict(snap) for snap in self._snapshots.get(doc_id, [])]


class _FakeAdvisorRepository:
    """Fake de AdvisorRepository: lista orientadores em memória."""

    def __init__(self, advisors: list[dict[str, Any]]) -> None:
        self._advisors = advisors

    async def list_all(self) -> list[dict[str, Any]]:
        return [dict(advisor) for advisor in self._advisors]


class _FakeProductionRepository:
    """Fake de ProductionRepository: produções já normalizadas em memória."""

    def __init__(self, productions: list[dict[str, Any]]) -> None:
        self._productions = productions

    async def list_productions(self) -> list[dict[str, Any]]:
        return [dict(production) for production in self._productions]

    async def list_productions_by_program(self, programa_id: str) -> list[dict[str, Any]]:
        return [
            dict(production)
            for production in self._productions
            if production.get("programa_id") == programa_id
        ]


class _FakeActivityRepository:
    """Fake de ActivityRepository: atividades por aluno em memória."""

    def __init__(self, by_student: dict[str, list[dict[str, Any]]]) -> None:
        self._by_student = by_student

    async def list_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return [dict(activity) for activity in self._by_student.get(student_id, [])]

    async def list_all_grouped(self) -> list[dict[str, Any]]:
        return [
            {**activity, "student_id": student_id}
            for student_id, activities in self._by_student.items()
            for activity in activities
        ]


def _build_service(
    students: list[dict[str, Any]],
    *,
    advisors: list[dict[str, Any]] | None = None,
    snapshots: dict[str, list[dict[str, Any]]] | None = None,
    productions: list[dict[str, Any]] | None = None,
    activities: dict[str, list[dict[str, Any]]] | None = None,
) -> ReportService:
    return ReportService(
        students=_FakeStudentRepository(students, snapshots),
        advisors=_FakeAdvisorRepository(advisors or []),
        productions=_FakeProductionRepository(productions or []),
        activities=_FakeActivityRepository(activities or {}),
    )


# -- students-at-risk -----------------------------------------------------------------


async def test_students_at_risk_filtra_por_situacao_inferida_e_usa_snapshot_mais_recente() -> None:
    prazo = "2026-12-31"
    service = _build_service(
        students=[
            {
                "id": "s1",
                "nome": "Ana",
                "orientador_id": "a1",
                "situacao_inferida": "em_risco",
                "prazo_final": prazo,
            },
            {"id": "s2", "nome": "Bruno", "orientador_id": "a1", "situacao_inferida": "regular"},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
        snapshots={
            "s1": [
                {"timestamp": "2026-06-01T00:00:00", "riscos_detectados": ["Antigo"]},
                {"timestamp": "2026-06-10T00:00:00", "riscos_detectados": ["Créditos insuficientes"]},
            ]
        },
    )

    result = await service.get_students_at_risk()

    assert result.total == 1
    item = result.items[0]
    assert item.student_id == "s1"
    assert item.orientador_nome == "Prof. X"
    assert item.razoes_risco == ["Créditos insuficientes"]
    assert item.dias_restantes_prazo == (date.fromisoformat(prazo) - date.today()).days


async def test_students_at_risk_sem_snapshot_retorna_razoes_vazias() -> None:
    service = _build_service(
        students=[{"id": "s1", "nome": "Ana", "orientador_id": "a1", "situacao_inferida": "em_risco"}],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
    )

    result = await service.get_students_at_risk()

    assert result.total == 1
    assert result.items[0].razoes_risco == []
    assert result.items[0].dias_restantes_prazo is None


async def test_students_at_risk_vazio_quando_ninguem_em_risco() -> None:
    service = _build_service(
        students=[{"id": "s1", "nome": "Ana", "situacao_inferida": "regular"}],
    )

    result = await service.get_students_at_risk()

    assert result.total == 0
    assert result.items == []


# -- students-by-status ---------------------------------------------------------------


async def test_students_by_status_agrupa_e_ignora_situacao_ausente() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "nome": "Ana", "orientador_id": "a1", "nivel": "mestrado", "situacao_registrada": "regular"},
            {"id": "s2", "nome": "Bruno", "orientador_id": "a1", "nivel": "mestrado", "situacao_registrada": "regular"},
            {"id": "s3", "nome": "Caio", "orientador_id": "a2", "nivel": "doutorado", "situacao_registrada": "em_risco"},
            {"id": "s4", "nome": "Dora"},  # sem situacao_registrada → ignorada
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}, {"id": "a2", "nome": "Profa. Y"}],
    )

    result = await service.get_students_by_status()

    assert result.por_situacao["regular"].total == 2
    assert {a.nome for a in result.por_situacao["regular"].alunos} == {"Ana", "Bruno"}
    assert result.por_situacao["regular"].alunos[0].orientador_nome == "Prof. X"
    assert result.por_situacao["em_risco"].total == 1
    assert result.por_situacao["em_risco"].alunos[0].nivel == "doutorado"


# -- students-by-advisor --------------------------------------------------------------


async def test_students_by_advisor_conta_em_risco_e_regulares() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "orientador_id": "a1", "situacao_registrada": "em_risco"},
            {"id": "s2", "orientador_id": "a1", "situacao_registrada": "regular"},
            {"id": "s3", "orientador_id": "a1", "situacao_registrada": "concluido"},
            {"id": "s4", "orientador_id": "a2", "situacao_registrada": "regular"},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}, {"id": "a2", "nome": "Profa. Y"}],
    )

    result = await service.get_students_by_advisor()

    por_id = {item.advisor_id: item for item in result.items}
    assert por_id["a1"].total_orientandos == 3
    assert por_id["a1"].em_risco == 1
    assert por_id["a1"].regulares == 1
    assert por_id["a2"].total_orientandos == 1
    assert por_id["a2"].regulares == 1


# -- completion-time ------------------------------------------------------------------


async def test_completion_time_calcula_media_min_max_e_usa_fallback_atualizado_em() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "nome": "Ana", "situacao_registrada": "concluido",
             "data_ingresso": "2022-01-01", "data_conclusao": "2024-01-01"},  # ~24 meses
            {"id": "s2", "nome": "Bruno", "situacao_registrada": "concluido",
             "data_ingresso": "2022-01-01",
             "atualizado_em": datetime(2023, 1, 1, tzinfo=timezone.utc)},  # fallback ~12 meses
            {"id": "s3", "nome": "Caio", "situacao_registrada": "regular",
             "data_ingresso": "2024-01-01"},  # não concluído → ignorado
        ],
    )

    result = await service.get_completion_time_avg()

    assert result.total_concluidos == 2
    assert len(result.historico) == 2
    assert result.minimo_meses == 12.0
    assert result.maximo_meses == 24.0
    assert result.media_meses == 18.0
    ano_por_nome = {item.student_nome: item.ano_conclusao for item in result.historico}
    assert ano_por_nome == {"Ana": 2024, "Bruno": 2023}


async def test_completion_time_conta_concluido_sem_data_mas_fora_do_historico() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "nome": "Ana", "situacao_registrada": "concluido"},  # sem datas
        ],
    )

    result = await service.get_completion_time_avg()

    assert result.total_concluidos == 1
    assert result.historico == []
    assert result.media_meses is None
    assert result.minimo_meses is None
    assert result.maximo_meses is None


# -- productions ----------------------------------------------------------------------


async def test_productions_credita_so_aprovadas_e_agrega_por_aluno_e_orientador() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
            {"id": "s2", "nome": "Bruno", "orientador_id": "a1", "programa_id": _PROG},
            {"id": "s3", "nome": "Caio", "orientador_id": "a2", "programa_id": _PROG},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}, {"id": "a2", "nome": "Profa. Y"}],
        productions=[
            {"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
            {"id": "p2", "nivel": "A5", "pontuacao_calculada": 1.0, "programa_id": _PROG},
        ],
        activities={
            "s1": [
                {"producao_id": "p1", "status": "aprovado"},
                {"producao_id": "p2", "status": "enviado"},  # não aprovada → ignorada
            ],
            "s3": [{"producao_id": "p2", "status": "aprovado"}],
        },
    )

    result = await service.get_productions_report(_PROG, "coordenacao", "")

    assert result.total_producoes_aprovadas == 2  # p1 e p2, sem duplicação
    por_aluno = {item.student_nome: item for item in result.por_aluno}
    assert set(por_aluno) == {"Ana", "Caio"}  # Bruno não tem produção creditada
    assert por_aluno["Ana"].total == 1
    assert por_aluno["Ana"].pontuacao_total == 4.0
    assert por_aluno["Ana"].por_nivel.A1 == 1
    assert por_aluno["Caio"].por_nivel.A5 == 1

    por_orientador = {item.advisor_id: item for item in result.por_orientador}
    # Prof. X tem 2 orientandos (Ana=4.0, Bruno=0.0) → soma 4.0, média 2.0; 1 produção.
    assert por_orientador["a1"].total == 1
    assert por_orientador["a1"].pontuacao_total == 4.0
    assert por_orientador["a1"].pontuacao_media_orientandos == 2.0
    assert por_orientador["a2"].pontuacao_total == 1.0
    assert por_orientador["a2"].pontuacao_media_orientandos == 1.0


async def test_productions_soma_multiplas_producoes_do_mesmo_aluno() -> None:
    service = _build_service(
        students=[{"id": "s1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG}],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
        productions=[
            {"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
            {"id": "p2", "nivel": "A2", "pontuacao_calculada": 1.5, "programa_id": _PROG},
            {"id": "p3", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
        ],
        activities={
            "s1": [
                {"producao_id": "p1", "status": "aprovado"},
                {"producao_id": "p2", "status": "aprovado"},
                {"producao_id": "p3", "status": "aprovado"},
            ]
        },
    )

    result = await service.get_productions_report(_PROG, "coordenacao", "")

    assert result.total_producoes_aprovadas == 3
    item = result.por_aluno[0]
    assert item.total == 3
    assert item.pontuacao_total == 9.5
    assert item.por_nivel.A1 == 2
    assert item.por_nivel.A2 == 1
    assert result.por_orientador[0].total == 3
    assert result.por_orientador[0].pontuacao_total == 9.5
    assert result.por_orientador[0].pontuacao_media_orientandos == 9.5


async def test_productions_nivel_ausente_cai_para_SC_e_classifica_a3() -> None:
    service = _build_service(
        students=[{"id": "s1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG}],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
        productions=[
            {"id": "p1", "pontuacao_calculada": 0.2, "programa_id": _PROG},  # sem nivel → padrão "SC"
            {"id": "p2", "nivel": "A3", "pontuacao_calculada": 2.0, "programa_id": _PROG},  # nível Qualis válido
        ],
        activities={
            "s1": [
                {"producao_id": "p1", "status": "aprovado"},
                {"producao_id": "p2", "status": "aprovado"},
            ]
        },
    )

    result = await service.get_productions_report(_PROG, "coordenacao", "")

    item = result.por_aluno[0]
    assert item.total == 2  # ambas creditadas
    assert item.pontuacao_total == 2.2
    assert item.por_nivel.SC == 1  # nivel ausente cai para SC
    assert item.por_nivel.A3 == 1  # "A3" agora tem bucket próprio
    assert item.por_nivel.A1 == 0
    assert item.por_nivel.A2 == 0


async def test_productions_ignora_producao_id_inexistente() -> None:
    service = _build_service(
        students=[{"id": "s1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG}],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
        productions=[{"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG}],
        activities={"s1": [{"producao_id": "p_fantasma", "status": "aprovado"}]},
    )

    result = await service.get_productions_report(_PROG, "coordenacao", "")

    assert result.total_producoes_aprovadas == 0
    assert result.por_aluno == []


async def test_productions_filtra_por_programa_id_do_solicitante() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
            {"id": "s2", "nome": "Bia", "orientador_id": "a2", "programa_id": "prog_outro"},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}, {"id": "a2", "nome": "Profa. Y"}],
        productions=[
            {"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
            {"id": "p2", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": "prog_outro"},
        ],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado"}],
            "s2": [{"producao_id": "p2", "status": "aprovado"}],
        },
    )

    result = await service.get_productions_report(_PROG, "coordenacao", "")

    # Apenas dados do próprio programa entram no relatório; o outro programa fica fora de escopo.
    assert result.total_producoes_aprovadas == 1
    assert {item.student_nome for item in result.por_aluno} == {"Ana"}
    assert {item.advisor_id for item in result.por_orientador} == {"a1"}


async def test_productions_discente_ve_so_a_propria_linha() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "uid": "u1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
            {"id": "s2", "uid": "u2", "nome": "Bia", "orientador_id": "a1", "programa_id": _PROG},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
        productions=[
            {"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
            {"id": "p2", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
        ],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado"}],
            "s2": [{"producao_id": "p2", "status": "aprovado"}],
        },
    )

    result = await service.get_productions_report(_PROG, "aluno", "u1")

    # Discente vê apenas a própria produção; sem agregados por orientador.
    assert {item.student_nome for item in result.por_aluno} == {"Ana"}
    assert result.por_orientador == []
    assert result.total_producoes_aprovadas == 1


async def test_productions_discente_sem_registro_no_programa_retorna_403() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "uid": "u1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X"}],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_productions_report(_PROG, "aluno", "u_fantasma")

    assert exc_info.value.status_code == 403


async def test_productions_orientador_ve_orientandos_identificados_e_resto_anonimo() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "uid": "u1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
            {"id": "s2", "uid": "u2", "nome": "Bia", "orientador_id": "a2", "programa_id": _PROG},
        ],
        advisors=[
            {"id": "a1", "nome": "Prof. X", "uid": "ua1"},
            {"id": "a2", "nome": "Profa. Y", "uid": "ua2"},
        ],
        productions=[
            {"id": "p1", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
            {"id": "p2", "nivel": "A1", "pontuacao_calculada": 4.0, "programa_id": _PROG},
        ],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado"}],
            "s2": [{"producao_id": "p2", "status": "aprovado"}],
        },
    )

    result = await service.get_productions_report(_PROG, "orientador", "ua1")

    # Orientando próprio: identificado.
    proprios = [item for item in result.por_aluno if not item.anonimo]
    assert len(proprios) == 1
    assert proprios[0].student_id == "s1"
    assert proprios[0].student_nome == "Ana"

    # Aluno de outro orientador: anônimo, sem id/nome, mas com as métricas preservadas.
    anonimos = [item for item in result.por_aluno if item.anonimo]
    assert len(anonimos) == 1
    assert anonimos[0].student_id is None
    assert anonimos[0].student_nome is None
    assert anonimos[0].total == 1

    # por_orientador traz apenas o próprio orientador.
    assert {item.advisor_id for item in result.por_orientador} == {"a1"}


async def test_productions_orientador_sem_registro_retorna_403() -> None:
    service = _build_service(
        students=[
            {"id": "s1", "uid": "u1", "nome": "Ana", "orientador_id": "a1", "programa_id": _PROG},
        ],
        advisors=[{"id": "a1", "nome": "Prof. X", "uid": "ua1"}],
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_productions_report(_PROG, "orientador", "ua_fantasma")

    assert exc_info.value.status_code == 403


# -- productions-by-month -------------------------------------------------------------


def _month_offset(n: int) -> tuple[str, date]:
    """Chave 'YYYY-MM' e uma data (dia 1) `n` meses atrás de hoje, para testes da janela."""
    today = date.today()
    year, month = today.year, today.month - n
    while month <= 0:
        month += 12
        year -= 1
    return f"{year:04d}-{month:02d}", date(year, month, 1)


async def test_productions_by_month_conta_producao_no_validado_em_mais_antigo() -> None:
    mes_atual, hoje = _month_offset(0)
    mes_antigo, antes = _month_offset(2)
    # Mesma produção creditada a dois alunos, validada em meses distintos (co-autoria).
    service = _build_service(
        students=[
            {"id": "s1", "programa_id": _PROG},
            {"id": "s2", "programa_id": _PROG},
        ],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado", "validado_em": hoje.isoformat()}],
            "s2": [{"producao_id": "p1", "status": "aprovado", "validado_em": antes.isoformat()}],
        },
    )

    result = await service.get_productions_by_month(_PROG, meses=12)

    por_mes = {item.mes: item.total for item in result}
    assert por_mes[mes_antigo] == 1  # contada uma vez, no mês mais antigo
    assert por_mes[mes_atual] == 0  # não recontada no mês mais recente
    assert sum(item.total for item in result) == 1


async def test_productions_by_month_ignora_aprovada_sem_data_de_validacao() -> None:
    service = _build_service(
        students=[{"id": "s1", "programa_id": _PROG}],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={"s1": [{"producao_id": "p1", "status": "aprovado"}]},  # sem validado_em/aprovado_em
    )

    result = await service.get_productions_by_month(_PROG)

    assert sum(item.total for item in result) == 0


async def test_productions_by_month_usa_aprovado_em_como_fallback() -> None:
    mes_atual, hoje = _month_offset(0)
    # Dado legado: só o campo aprovado_em preenchido (sem validado_em), como nos
    # registros antigos que ActivityResponse normaliza para validado_em.
    service = _build_service(
        students=[{"id": "s1", "programa_id": _PROG}],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={"s1": [{"producao_id": "p1", "status": "aprovado", "aprovado_em": hoje.isoformat()}]},
    )

    result = await service.get_productions_by_month(_PROG)

    por_mes = {item.mes: item.total for item in result}
    assert por_mes[mes_atual] == 1
    assert sum(item.total for item in result) == 1


async def test_productions_by_month_ignora_nao_aprovada_e_producao_orfa() -> None:
    _, hoje = _month_offset(0)
    service = _build_service(
        students=[{"id": "s1", "programa_id": _PROG}],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={
            "s1": [
                {"producao_id": "p1", "status": "enviado", "validado_em": hoje.isoformat()},
                {"producao_id": "p_fantasma", "status": "aprovado", "validado_em": hoje.isoformat()},
            ]
        },
    )

    result = await service.get_productions_by_month(_PROG)

    assert sum(item.total for item in result) == 0


async def test_productions_by_month_validacao_fora_da_janela_nao_conta() -> None:
    mes_fora, fora = _month_offset(13)  # além dos 12 meses da janela
    service = _build_service(
        students=[{"id": "s1", "programa_id": _PROG}],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado", "validado_em": fora.isoformat()}]
        },
    )

    result = await service.get_productions_by_month(_PROG, meses=12)

    assert all(item.mes != mes_fora for item in result)
    assert sum(item.total for item in result) == 0


async def test_productions_by_month_preenche_janela_ordenada_com_zeros() -> None:
    mes_atual, hoje = _month_offset(0)
    service = _build_service(
        students=[{"id": "s1", "programa_id": _PROG}],
        productions=[{"id": "p1", "programa_id": _PROG}],
        activities={
            "s1": [{"producao_id": "p1", "status": "aprovado", "validado_em": hoje.isoformat()}]
        },
    )

    result = await service.get_productions_by_month(_PROG, meses=6)

    assert len(result) == 6
    assert [item.mes for item in result] == sorted(item.mes for item in result)
    assert result[-1].mes == mes_atual  # mês corrente por último
    assert result[-1].total == 1
    assert all(item.total == 0 for item in result if item.mes != mes_atual)

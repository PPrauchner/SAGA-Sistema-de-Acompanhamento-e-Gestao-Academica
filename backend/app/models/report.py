"""
Modelos Pydantic de resposta para os relatórios gerenciais da coordenação.

Responsabilidades:
- Definir os response models dos 5 endpoints de relatórios:
  StudentsAtRiskResponse, StudentsByStatusResponse, StudentsByAdvisorResponse,
  CompletionTimeResponse e ProductionsReportResponse.
- Modelar alunos em risco com as razões do risco (RL03), agrupamentos por situação e por
  orientador, tempo médio de integralização dos concluídos e produção bibliográfica por
  aluno e por orientador.
- Espelhar o contrato definido em docs/specs/09_relatorios_dashboard.json → contratos_api
  (paths /reports/*).
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.models.student import SituacaoRegistrada


class StudentAtRiskItem(BaseModel):
    """Aluno em risco com o motivo inferido pelo motor (RL03)."""

    student_id: str
    nome: str
    orientador_nome: str
    situacao_inferida: str
    dias_restantes_prazo: int | None = None
    razoes_risco: list[str]


class StudentsAtRiskResponse(BaseModel):
    """Lista de alunos em situação de risco inferida pelo motor."""

    total: int
    items: list[StudentAtRiskItem]


class StudentStatusSummary(BaseModel):
    """Resumo de um aluno dentro de um agrupamento por situação."""

    student_id: str
    nome: str
    orientador_nome: str
    nivel: str


class StatusGroup(BaseModel):
    """Contagem e lista resumida de alunos de uma mesma situação registrada."""

    total: int
    alunos: list[StudentStatusSummary]


class StudentsByStatusResponse(BaseModel):
    """Alunos agrupados por situação registrada (chave = valor do enum de situação)."""

    por_situacao: dict[SituacaoRegistrada, StatusGroup]


class AdvisorGroupItem(BaseModel):
    """Distribuição de orientandos de um orientador por situação."""

    advisor_id: str
    advisor_nome: str
    total_orientandos: int
    em_risco: int
    regulares: int


class StudentsByAdvisorResponse(BaseModel):
    """Alunos agrupados por orientador com distribuição de status."""

    items: list[AdvisorGroupItem]


class CompletionTimeItem(BaseModel):
    """Tempo de integralização de um aluno concluído."""

    student_nome: str
    meses: float
    ano_conclusao: int


class CompletionTimeResponse(BaseModel):
    """Tempo médio de integralização dos alunos concluídos."""

    media_meses: float | None = None
    total_concluidos: int
    minimo_meses: float | None = None
    maximo_meses: float | None = None
    historico: list[CompletionTimeItem]


class ProductionLevelBreakdown(BaseModel):
    """Distribuição de produções pelos níveis Qualis Único do veículo (A1–A8 + SC)."""

    A1: int = 0
    A2: int = 0
    A3: int = 0
    A4: int = 0
    A5: int = 0
    A6: int = 0
    A7: int = 0
    A8: int = 0
    SC: int = 0


class ProductionByStudentItem(BaseModel):
    """Produção bibliográfica aprovada de um aluno."""

    student_id: str
    student_nome: str
    total: int
    pontuacao_total: float
    por_nivel: ProductionLevelBreakdown


class ProductionByAdvisorItem(BaseModel):
    """Produção bibliográfica agregada dos orientandos de um orientador."""

    advisor_id: str
    advisor_nome: str
    total: int
    pontuacao_media_orientandos: float


class ProductionsReportResponse(BaseModel):
    """Produção bibliográfica por aluno e por orientador."""

    total_producoes_aprovadas: int
    por_aluno: list[ProductionByStudentItem]
    por_orientador: list[ProductionByAdvisorItem]

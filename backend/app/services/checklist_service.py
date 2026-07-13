"""
Serviço de negócio para geração do checklist de integralização.

Responsabilidades:
- get_checklist(student_id) -> ChecklistResponse: delega execução ao InferenceService e
  formata o resultado como checklist de 8 requisitos (créditos mínimos totais, créditos
  por grupo básico, específico e tecnológico, proficiência, qualificação, produção
  validada, plano concluído). Cada requisito retorna status 'cumprido' | 'pendente' |
  'em_risco' com valores obtidos vs mínimos/máximos requeridos.
- Detectar conflito entre situacao_registrada e situacao_inferida.
- Calcular riscos_detectados[] a partir das regras RL03 (em_risco e suas 4 cláusulas).
- Utilizado pelo endpoint GET /api/v1/checklist/{student_id} e pela ChecklistPage do
  frontend, que exibe dados reais em substituição aos dados hardcoded.
"""

from __future__ import annotations

from typing import Any

from backend.app.models.checklist import (
    ChecklistRequisitos,
    ChecklistResponse,
    CreditoMaximoRequisito,
    CreditoMinimoRequisito,
    PlanoRequisito,
    ProducaoRequisito,
    ProficienciaRequisito,
    QualificacaoRequisito,
)
from backend.app.models.inference import InferenceChecklist
from backend.app.services.inference_service import (
    InferenceDataSource,
    InferenceService,
    StudentNotFoundError,
)


class ChecklistService:
    """Formata o resultado do motor como checklist de integralização e detecta conflitos."""

    def __init__(self, inference_service: InferenceService, data_source: InferenceDataSource) -> None:
        """Inicializa o serviço com suas dependências.

        Args:
            inference_service: Executor do motor lógico para o aluno.
            data_source: Fonte de dados para alunos, produções e tarefas.
        """
        self._inference = inference_service
        self._data = data_source

    async def get_checklist(self, student_id: str) -> ChecklistResponse:
        """Executa o motor e monta o checklist completo do aluno.

        Args:
            student_id: ID do documento do aluno.

        Returns:
            ChecklistResponse com os 7 requisitos, flag de conflito de situação, riscos
            detectados e o id do snapshot persistido.

        Raises:
            StudentNotFoundError: Se o aluno não existir na fonte de dados.
        """
        student = await self._data.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        programa_id = student.get("programa_id", "")
        result = await self._inference.run_inference(student_id, programa_id)
        productions = await self._data.get_approved_productions(student_id)
        tasks = await self._data.get_plan_tasks(student_id)

        situacao_registrada = student.get("situacao_registrada", "")
        conflito = situacao_registrada != result.situacao_inferida

        requisitos = self._build_requisitos(result.checklist, student, productions, tasks)

        return ChecklistResponse(
            student_id=student_id,
            student_nome=student.get("nome", ""),
            timestamp=result.timestamp,
            situacao_registrada=situacao_registrada,
            situacao_inferida=result.situacao_inferida,
            conflito_situacao=conflito,
            apto_defesa=result.apto_defesa,
            requisitos=requisitos,
            riscos_detectados=result.riscos_detectados,
            snapshot_id=result.snapshot_id,
        )

    def _build_requisitos(
        self,
        checklist: InferenceChecklist,
        student: dict[str, Any],
        productions: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
    ) -> ChecklistRequisitos:
        """Combina os status inferidos com os campos de apresentação de cada requisito.

        Args:
            checklist: Resultado estruturado do motor com status por requisito.
            student: Documento do aluno com campos de proficiência e qualificação.
            productions: Lista de produções aprovadas do aluno.
            tasks: Lista de tarefas do plano de trabalho do aluno.

        Returns:
            ChecklistRequisitos com todos os 8 campos preenchidos.
        """
        non_defesa = [t for t in tasks if not t.get("is_defesa")]
        tasks_concluidas = len([t for t in non_defesa if t.get("concluida")])
        qtd_bibliografica = len([p for p in productions if p.get("bibliografica")])

        return ChecklistRequisitos(
            creditos_minimos=CreditoMinimoRequisito(
                status=checklist.creditos_minimos.status,
                obtidos=checklist.creditos_minimos.obtidos,
                minimo=checklist.creditos_minimos.minimo,
                descricao=f"Mínimo de {checklist.creditos_minimos.minimo} créditos totais",
            ),
            creditos_grupo_basico=CreditoMinimoRequisito(
                status=checklist.creditos_grupo_basico.status,
                obtidos=checklist.creditos_grupo_basico.obtidos,
                minimo=checklist.creditos_grupo_basico.minimo,
                descricao=f"Mínimo de {checklist.creditos_grupo_basico.minimo} créditos em disciplinas básicas",
            ),
            creditos_grupo_especifico=CreditoMinimoRequisito(
                status=checklist.creditos_grupo_especifico.status,
                obtidos=checklist.creditos_grupo_especifico.obtidos,
                minimo=checklist.creditos_grupo_especifico.minimo,
                descricao=f"Mínimo de {checklist.creditos_grupo_especifico.minimo} créditos em atividades específicas",
            ),
            creditos_grupo_tecnologico=CreditoMaximoRequisito(
                status=checklist.creditos_grupo_tecnologico.status,
                obtidos=checklist.creditos_grupo_tecnologico.obtidos,
                maximo=checklist.creditos_grupo_tecnologico.maximo,
                descricao=f"Máximo de {checklist.creditos_grupo_tecnologico.maximo} créditos em atividades tecnológicas",
            ),
            proficiencia=ProficienciaRequisito(
                status=checklist.proficiencia.status,
                data_comprovacao=student.get("proficiencia_data"),
                comprovante_url=student.get("proficiencia_comprovante_url"),
            ),
            qualificacao=QualificacaoRequisito(
                status=checklist.qualificacao.status,
                data_aprovacao=student.get("qualificacao_data"),
                comprovante_url=student.get("qualificacao_comprovante_url"),
            ),
            producao_validada=ProducaoRequisito(
                status=checklist.producao_validada.status,
                quantidade_aprovadas=qtd_bibliografica,
            ),
            plano_concluido=PlanoRequisito(
                status=checklist.plano_concluido.status,
                tasks_concluidas=tasks_concluidas,
                tasks_total_nao_defesa=len(non_defesa),
            ),
        )

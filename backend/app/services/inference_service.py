"""
Serviço orquestrador da carga de fatos e execução do motor de inferência.

Responsabilidades:
- run_inference(student_id, programa_id) -> InferenceResult: método principal que:
    1. Carrega student do Firestore (data_ingresso, prazo_final, proficiencia_comprovada,
       qualificacao_aprovada).
    2. Carrega configurações do programa (créditos mínimos, pesos de relevância).
    3. Carrega atividades aprovadas e calcula créditos por categoria (básico, específico,
       tecnológico).
    4. Carrega tasks do plano e determina quais etapas estão concluídas.
    5. Carrega produções aprovadas e verifica ao menos 1 bibliográfica.
    6. Calcula fatos derivados temporais: prazo_estourado, prazo_qualificacao_proximo,
       plano_atrasado, qualificacao_pendente, creditos_insuficientes.
    7. Monta FactBase com todos os fatos coletados.
    8. Instancia InferenceEngine (de backend/inference_engine/) com FactBase + RuleBase.
    9. Executa queries: apto_defesa, creditos_validos, em_risco, atividades_elegiveis,
       pontuacoes_producoes.
   10. Persiste snapshot em students/{id}/inferred_status/ e atualiza situacao_inferida.
- É o único módulo que instancia o InferenceEngine — outros serviços não acessam o motor
  diretamente.

A origem dos dados é injetada via InferenceDataSource — os métodos definem o contrato
esperado pelos repositórios concretos.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Protocol

from inference_engine.knowledge_base import FactBase, InferenceEngine, RuleBase
from inference_engine.rules import register_all
from inference_engine.terms import Atom, Compound, Variable

from backend.app.models.inference import (
    CreditoMaximoItem,
    CreditoMinimoItem,
    InferenceChecklist,
    InferenceResult,
    PontuacaoProducao,
    RequisitoStatus,
    SituacaoInferida,
    StatusItem,
)

# Janela (em dias) para considerar o prazo de qualificação "próximo" (~3 meses).
_RISK_HORIZON_DAYS = 90


class StudentNotFoundError(Exception):
    """Lançada quando o aluno consultado não existe na fonte de dados."""

    def __init__(self, student_id: str) -> None:
        super().__init__(f"Aluno não encontrado: {student_id}")
        self.student_id = student_id


class InferenceDataSource(Protocol):
    """Contrato de leitura/escrita consumido pelo InferenceService.

    Implementado por InferenceRepository (produção) e FixtureRepository (testes).
    """

    async def get_student(self, student_id: str) -> dict[str, Any] | None: ...
    async def get_program(self, programa_id: str) -> dict[str, Any] | None: ...
    async def get_approved_activities(self, student_id: str) -> list[dict[str, Any]]: ...
    async def get_plan_tasks(self, student_id: str) -> list[dict[str, Any]]: ...
    async def get_approved_productions(self, student_id: str) -> list[dict[str, Any]]: ...
    async def save_inferred_status(self, student_id: str, snapshot: dict[str, Any]) -> str: ...


def _parse_date(value: Any) -> date | None:
    """Converte uma string ISO 'YYYY-MM-DD' em date, ou None se inválida/ausente."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


class InferenceService:
    """Único orquestrador do motor de inferência: monta a FactBase e executa as regras."""

    def __init__(self, data_source: InferenceDataSource) -> None:
        self._data = data_source

    async def evaluate_student(self, student_id: str) -> InferenceResult:
        """Executa a inferência derivando o programa do próprio aluno.

        Conveniência para o endpoint GET /inference/{student_id}, que recebe apenas o id do
        aluno.

        Raises:
            StudentNotFoundError: Se o aluno não existir na fonte de dados.
        """
        student = await self._data.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return await self.run_inference(student_id, student.get("programa_id", ""))

    async def run_inference(self, student_id: str, programa_id: str) -> InferenceResult:
        """Executa todas as inferências para o aluno e persiste o snapshot.

        Args:
            student_id: ID do documento do aluno.
            programa_id: ID do programa do aluno (fonte da configuração de créditos/pesos).

        Returns:
            InferenceResult com situação inferida, booleanos das regras, checklist resumido,
            atividades elegíveis (RL04), pontuações de produção (RL05) e fatos usados.

        Raises:
            StudentNotFoundError: Se o aluno não existir na fonte de dados.
        """
        student = await self._data.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        program = await self._data.get_program(programa_id) or {}
        activities = await self._data.get_approved_activities(student_id)
        tasks = await self._data.get_plan_tasks(student_id)
        productions = await self._data.get_approved_productions(student_id)

        facts, totals, risk_flags = self._build_facts(
            student_id, programa_id, student, program, activities, tasks, productions
        )
        engine = self._build_engine(facts)

        apto = bool(engine.query(Compound("apto_defesa", [Atom(student_id)])))
        creditos_validos = bool(engine.query(Compound("creditos_validos", [Atom(student_id)])))
        em_risco = bool(engine.query(Compound("em_risco", [Atom(student_id)])))
        atividades_elegiveis = self._query_eligible_activities(engine, student_id, activities)
        pontuacoes = self._query_production_scores(engine, productions)

        situacao = self._derive_situacao(apto, em_risco, student)
        checklist = self._build_checklist(totals, program, student, productions, tasks, risk_flags)
        riscos = self._risk_messages(risk_flags, student, totals, program)

        result = InferenceResult(
            student_id=student_id,
            programa_id=programa_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            situacao_inferida=situacao,
            apto_defesa=apto,
            creditos_validos=creditos_validos,
            em_risco=em_risco,
            checklist=checklist,
            atividades_elegiveis=atividades_elegiveis,
            pontuacoes_producoes=pontuacoes,
            fatos_usados=[repr(f) for f in facts],
            riscos_detectados=riscos,
        )

        snapshot_id = await self._data.save_inferred_status(student_id, result.model_dump())
        result.snapshot_id = snapshot_id
        return result

    # -- construção de fatos ------------------------------------------------------------

    def _build_facts(
        self,
        student_id: str,
        programa_id: str,
        student: dict[str, Any],
        program: dict[str, Any],
        activities: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        productions: list[dict[str, Any]],
    ) -> tuple[list[Compound], dict[str, int], dict[str, bool]]:
        """Traduz os dados de domínio em fatos lógicos (Compounds) para a FactBase.

        Returns:
            (facts, totals, risk_flags) — a lista de fatos, os totais de crédito por grupo e
            os gatilhos de risco detectados (para montagem das mensagens).
        """
        sid = Atom(student_id)
        prog = Atom(programa_id)
        facts: list[Compound] = []

        # Créditos por grupo a partir das atividades aprovadas.
        totals = {"basico": 0, "especifico": 0, "tecnologico": 0}
        for activity in activities:
            grupo = activity.get("grupo")
            if grupo in totals:
                totals[grupo] += int(activity.get("creditos", 0))
        total = totals["basico"] + totals["especifico"] + totals["tecnologico"]
        totals["total"] = total
        facts.append(Compound("creditos_grupo_basico", [sid, Atom(totals["basico"])]))
        facts.append(Compound("creditos_grupo_especifico", [sid, Atom(totals["especifico"])]))
        facts.append(Compound("creditos_grupo_tecnologico", [sid, Atom(totals["tecnologico"])]))
        facts.append(Compound("total_creditos", [sid, Atom(total)]))

        # Configuração do programa.
        min_basico = int(program.get("min_creditos_basico", 12))
        min_especifico = int(program.get("min_creditos_especifico", 8))
        max_tecnologico = int(program.get("max_creditos_tecnologico", 4))
        min_total = int(program.get("min_creditos_total", 24))
        facts.append(Compound("min_creditos_basico", [prog, Atom(min_basico)]))
        facts.append(Compound("min_creditos_especifico", [prog, Atom(min_especifico)]))
        facts.append(Compound("max_creditos_tecnologico", [prog, Atom(max_tecnologico)]))
        facts.append(Compound("min_creditos_total", [prog, Atom(min_total)]))

        # Requisitos booleanos.
        if student.get("proficiencia_comprovada"):
            facts.append(Compound("proficiencia_comprovada", [sid]))
        if student.get("qualificacao_aprovada"):
            facts.append(Compound("qualificacao_aprovada", [sid]))
        else:
            facts.append(Compound("qualificacao_pendente", [sid]))
        if any(p.get("bibliografica") for p in productions):
            facts.append(Compound("producao_bibliografica_validada", [sid]))
        if self._is_plano_concluido(tasks):
            facts.append(Compound("plano_concluido", [sid]))

        # Fatos temporais derivados (gatilhos de RL03).
        today = date.today()
        risk_flags = {
            "prazo_estourado": False,
            "creditos_insuficientes": False,
            "qualificacao_prazo_proximo": False,
            "plano_atrasado": False,
        }
        prazo_final = _parse_date(student.get("prazo_final"))
        if prazo_final is not None and prazo_final < today:
            facts.append(Compound("prazo_estourado", [sid]))
            risk_flags["prazo_estourado"] = True
        expected_total = min_total * self._fracao_prazo_decorrida(student)
        if total < expected_total:
            facts.append(Compound("creditos_insuficientes", [sid]))
            risk_flags["creditos_insuficientes"] = True
        prazo_qual = _parse_date(student.get("prazo_qualificacao"))
        if (
            not student.get("qualificacao_aprovada")
            and prazo_qual is not None
            and (prazo_qual - today).days <= _RISK_HORIZON_DAYS
        ):
            facts.append(Compound("prazo_qualificacao_proximo", [sid]))
            risk_flags["qualificacao_prazo_proximo"] = True
        if self._is_plano_atrasado(student, tasks):
            facts.append(Compound("plano_atrasado", [sid]))
            risk_flags["plano_atrasado"] = True

        # Fatos por atividade (RL04).
        category_running = {"basico": 0, "especifico": 0, "tecnologico": 0}
        ingresso = _parse_date(student.get("data_ingresso"))
        for activity in activities:
            atv = Atom(activity["id"])
            activity_date = _parse_date(activity.get("data"))
            if activity_date is not None and ingresso is not None and activity_date >= ingresso:
                facts.append(Compound("dentro_periodo_curso", [atv, sid]))
            if activity.get("comprovante"):
                facts.append(Compound("tem_comprovante", [atv]))
            if activity.get("tipo_ativo"):
                facts.append(Compound("tipo_ativo", [atv]))
            grupo = activity.get("grupo")
            creditos = int(activity.get("creditos", 0))
            running = (category_running.get(grupo, 0) if grupo is not None else 0) + creditos
            limite = max_tecnologico if grupo == "tecnologico" else None
            if limite is None or running <= limite:
                facts.append(Compound("nao_excede_limite_categoria", [atv, sid]))
            if grupo is not None and grupo in category_running:
                category_running[grupo] = running

        # Fatos de configuração de pesos (RL05) — uma vez por nível configurado.
        pesos: dict[str, float] = program.get("relevancia_pesos", {})
        for nivel, peso in pesos.items():
            facts.append(Compound("relevancia_peso", [Atom(nivel), Atom(float(peso))]))

        # Fatos por produção (RL05).
        for production in productions:
            pid = Atom(production["id"])
            vid = Atom(production["veiculo_id"])
            facts.append(Compound("producao_veiculo", [pid, vid]))
            nivel = production.get("nivel")
            if nivel:
                facts.append(Compound("nivel_relevancia", [vid, prog, Atom(nivel)]))
            facts.append(Compound("pontuacao_base", [pid, Atom(float(production.get("pontuacao_base", 0)))]))

        return facts, totals, risk_flags

    def _build_engine(self, facts: list[Compound]) -> InferenceEngine:
        """Instancia o motor com os fatos coletados e as regras RL01-RL05."""
        fact_base = FactBase()
        for fact in facts:
            fact_base.add_fact(fact)
        rule_base = RuleBase()
        register_all(rule_base)
        return InferenceEngine(fact_base, rule_base)

    # -- consultas ao motor -------------------------------------------------------------

    def _query_eligible_activities(
        self,
        engine: InferenceEngine,
        student_id: str,
        activities: list[dict[str, Any]],
    ) -> list[str]:
        """Retorna os IDs das atividades que satisfazem RL04 (atividade_elegivel)."""
        eligible: list[str] = []
        for activity in activities:
            goal = Compound("atividade_elegivel", [Atom(activity["id"]), Atom(student_id)])
            if engine.query(goal):
                eligible.append(activity["id"])
        return eligible

    def _query_production_scores(
        self,
        engine: InferenceEngine,
        productions: list[dict[str, Any]],
    ) -> list[PontuacaoProducao]:
        """Retorna as pontuações ponderadas (RL05) das produções com veículo classificado."""
        scores: list[PontuacaoProducao] = []
        for production in productions:
            goal = Compound("pontuacao_producao", [Atom(production["id"]), Variable("Score")])
            results = engine.query(goal)
            if not results:
                continue
            score_term = results[0].get("Score")
            score = float(score_term.value) if isinstance(score_term, Atom) else 0.0
            base = float(production.get("pontuacao_base", 0)) or 1.0
            scores.append(
                PontuacaoProducao(
                    producao_id=production["id"],
                    score=score,
                    nivel_veiculo=production.get("nivel", ""),
                    peso_aplicado=round(score / base, 4),
                )
            )
        return scores

    # -- derivações de apresentação -----------------------------------------------------

    def _derive_situacao(self, apto: bool, em_risco: bool, student: dict[str, Any]) -> SituacaoInferida:
        """Mapeia os booleanos das regras para a situação inferida do aluno."""
        if apto:
            return "em_fase_de_defesa"
        if em_risco:
            return "em_risco"
        if student.get("qualificacao_aprovada"):
            return "qualificado"
        return "regular"

    def _build_checklist(
        self,
        totals: dict[str, int],
        program: dict[str, Any],
        student: dict[str, Any],
        productions: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        risk_flags: dict[str, bool],
    ) -> InferenceChecklist:
        """Monta o checklist resumido por item (status cumprido/pendente/em_risco)."""
        min_basico = int(program.get("min_creditos_basico", 12))
        min_especifico = int(program.get("min_creditos_especifico", 8))
        max_tecnologico = int(program.get("max_creditos_tecnologico", 4))
        min_total = int(program.get("min_creditos_total", 24))

        risco_creditos = risk_flags["creditos_insuficientes"]
        risco_qualificacao = risk_flags["qualificacao_prazo_proximo"]
        risco_plano = risk_flags["plano_atrasado"]
        risco_prazo_estourado = risk_flags["prazo_estourado"]

        def status_min(obtidos: int, minimo: int, em_risco_item: bool) -> RequisitoStatus:
            if obtidos >= minimo:
                return "cumprido"
            return "em_risco" if em_risco_item else "pendente"

        def status_max(obtidos: int, maximo: int, em_risco_item: bool) -> RequisitoStatus:
            if obtidos <= maximo:
                return "cumprido"
            return "em_risco" if em_risco_item else "pendente"

        def status_bool(ok: bool, em_risco_item: bool) -> RequisitoStatus:
            if ok:
                return "cumprido"
            return "em_risco" if em_risco_item else "pendente"

        return InferenceChecklist(
            creditos_minimos=CreditoMinimoItem(
                status=status_min(totals["total"], min_total, risco_creditos),
                obtidos=totals["total"],
                minimo=min_total,
            ),
            creditos_grupo_basico=CreditoMinimoItem(
                status=status_min(totals["basico"], min_basico, risco_creditos),
                obtidos=totals["basico"],
                minimo=min_basico,
            ),
            creditos_grupo_especifico=CreditoMinimoItem(
                status=status_min(totals["especifico"], min_especifico, risco_creditos),
                obtidos=totals["especifico"],
                minimo=min_especifico,
            ),
            creditos_grupo_tecnologico=CreditoMaximoItem(
                status=status_max(totals["tecnologico"], max_tecnologico, risco_creditos),
                obtidos=totals["tecnologico"],
                maximo=max_tecnologico,
            ),
            proficiencia=StatusItem(
                status=status_bool(bool(student.get("proficiencia_comprovada")), risco_prazo_estourado)
            ),
            qualificacao=StatusItem(
                status=status_bool(bool(student.get("qualificacao_aprovada")), risco_qualificacao)
            ),
            producao_validada=StatusItem(
                status=status_bool(any(p.get("bibliografica") for p in productions), risco_prazo_estourado)
            ),
            plano_concluido=StatusItem(status=status_bool(self._is_plano_concluido(tasks), risco_plano)),
        )

    def _risk_messages(
        self,
        risk_flags: dict[str, bool],
        student: dict[str, Any],
        totals: dict[str, int],
        program: dict[str, Any],
    ) -> list[str]:
        """Converte os gatilhos de risco em mensagens legíveis para a UI."""
        messages: list[str] = []
        if risk_flags["prazo_estourado"]:
            messages.append(f"Prazo final expirado em {student.get('prazo_final')}")
        if risk_flags["creditos_insuficientes"]:
            messages.append(
                f"Créditos insuficientes ({totals['total']}/{program.get('min_creditos_total', 24)})"
            )
        if risk_flags["qualificacao_prazo_proximo"]:
            messages.append("Qualificação pendente com prazo próximo")
        if risk_flags["plano_atrasado"]:
            messages.append("Plano de trabalho atrasado em relação ao cronograma")
        return messages

    # -- helpers de plano ---------------------------------------------------------------

    def _fracao_prazo_decorrida(self, student: dict[str, Any]) -> float:
        """Fração do prazo já decorrida desde data_ingresso até prazo_final.

        Args:
            student: Documento do aluno com campos data_ingresso e prazo_final.

        Returns:
            Float em [0.0, 1.0]: 0.0 se datas ausentes/inválidas ou se o prazo não
            começou; 1.0 se o prazo já expirou; valor proporcional caso contrário.
        """
        ingresso = _parse_date(student.get("data_ingresso"))
        prazo = _parse_date(student.get("prazo_final"))
        if ingresso is None or prazo is None or prazo <= ingresso:
            return 0.0
        elapsed = (date.today() - ingresso).days
        span = (prazo - ingresso).days
        return max(0.0, min(1.0, elapsed / span))

    def _is_plano_concluido(self, tasks: list[dict[str, Any]]) -> bool:
        """True se todas as tasks não-defesa estiverem concluídas (e houver ao menos uma)."""
        non_defesa = [t for t in tasks if not t.get("is_defesa")]
        return bool(non_defesa) and all(t.get("concluida") for t in non_defesa)

    def _is_plano_atrasado(self, student: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
        """True se a fração concluída do plano está abaixo do esperado para a data atual."""
        non_defesa = [t for t in tasks if not t.get("is_defesa")]
        if not non_defesa:
            return False
        expected = self._fracao_prazo_decorrida(student)
        concluidas = len([t for t in non_defesa if t.get("concluida")])
        actual = concluidas / len(non_defesa)
        return actual < expected

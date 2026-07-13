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

from calendar import monthrange
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
from backend.app.models.program_config import DEFAULT_PROGRAM_CREDIT_CONFIG
from backend.app.models.vehicle import PESO_POR_NIVEL
from backend.app.services.qualis_weights_service import resolve_weights_at

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
    async def get_qualis_weights_versions(self, programa_id: str) -> list[dict[str, Any]]: ...
    async def save_inferred_status(self, student_id: str, snapshot: dict[str, Any]) -> str: ...


def _parse_date(value: Any) -> date | None:
    """Converte uma string ISO 'YYYY-MM-DD' em date, ou None se inválida/ausente."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _to_datetime(value: Any) -> datetime | None:
    """Converte datetime/date/string ISO em datetime, ou None se ausente/inválido."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _add_months(start: date, months: int) -> date:
    """Soma `months` meses a `start`, ajustando o dia ao último dia do mês de destino."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _program_credit(program: dict[str, Any], key: str) -> int:
    return int(program.get(key, DEFAULT_PROGRAM_CREDIT_CONFIG[key]))


class InferenceService:
    """Único orquestrador do motor de inferência: monta a FactBase e executa as regras."""

    def __init__(self, data_source: InferenceDataSource) -> None:
        self._data = data_source

    async def evaluate_student(self, student_id: str) -> InferenceResult:
        """Executa a inferência derivando o programa do próprio aluno."""
        student = await self._data.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return await self.run_inference(student_id, student.get("programa_id", ""))

    def score_production(self, nivel: str, peso: float, pontuacao_base: float) -> float:
        """Calcula a pontuação RL05 de uma única produção via motor de inferência.

        Monta os fatos RL05 (producao_veiculo, nivel_relevancia, relevancia_peso,
        pontuacao_base) para uma produção isolada e resolve pontuacao_producao. Usado por
        ProductionService.create_production() para gravar pontuacao_calculada no registro,
        mantendo o cálculo dentro do motor (e não como aritmética no service).

        Args:
            nivel: Nível de relevância do veículo (ex: 'A1').
            peso: Peso associado ao nível (ex: 2.0).
            pontuacao_base: Pontuação base da produção.

        Returns:
            Pontuação ponderada resolvida pelo motor, ou 0.0 se não houver solução.
        """
        prod = Atom("p")
        veiculo = Atom("v")
        facts = [
            Compound("producao_veiculo", [prod, veiculo]),
            Compound("nivel_relevancia", [veiculo, Atom("prog"), Atom(nivel)]),
            Compound("relevancia_peso", [Atom(nivel), Atom(float(peso))]),
            Compound("pontuacao_base", [prod, Atom(float(pontuacao_base))]),
        ]
        engine = self._build_engine(facts)
        results = engine.query(Compound("pontuacao_producao", [prod, Variable("Score")]))
        if not results:
            return 0.0
        score_term = results[0].get("Score")
        return float(score_term.value) if isinstance(score_term, Atom) else 0.0

    async def run_inference(self, student_id: str, programa_id: str) -> InferenceResult:
        """Executa todas as inferências para o aluno e persiste o snapshot."""
        student = await self._data.get_student(student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        program = await self._data.get_program(programa_id) or {}
        activities = await self._data.get_approved_activities(student_id)
        tasks = await self._data.get_plan_tasks(student_id)
        productions = await self._data.get_approved_productions(student_id)
        weight_versions = await self._data.get_qualis_weights_versions(programa_id)

        facts, totals, risk_flags = self._build_facts(
            student_id, programa_id, student, program, activities, tasks, productions
        )
        engine = self._build_engine(facts)

        apto = bool(engine.query(Compound("apto_defesa", [Atom(student_id)])))
        creditos_validos = bool(engine.query(Compound("creditos_validos", [Atom(student_id)])))
        em_risco = bool(engine.query(Compound("em_risco", [Atom(student_id)])))
        atividades_elegiveis = self._query_eligible_activities(engine, student_id, activities)
        pontuacoes = self._score_productions(productions, weight_versions)

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
        sid = Atom(student_id)
        prog = Atom(programa_id)
        facts: list[Compound] = []

        totals = {"basico": 0, "especifico": 0, "tecnologico": 0}
        for activity in activities:
            grupo = activity.get("grupo")
            if grupo in totals:
                # Trata creditos de forma resiliente tanto se vier float ou int
                totals[grupo] += int(float(activity.get("creditos", 0)))
        total = totals["basico"] + totals["especifico"] + totals["tecnologico"]
        totals["total"] = total
        facts.append(Compound("creditos_grupo_basico", [sid, Atom(totals["basico"])]))
        facts.append(Compound("creditos_grupo_especifico", [sid, Atom(totals["especifico"])]))
        facts.append(Compound("creditos_grupo_tecnologico", [sid, Atom(totals["tecnologico"])]))
        facts.append(Compound("total_creditos", [sid, Atom(total)]))

        # M2 Correção: Alinhamento exato de chaves com o data-model gerado pelas seeds do banco
        min_basico = _program_credit(program, "creditos_grupo_basico_min")
        min_especifico = _program_credit(program, "creditos_grupo_especifico_min")
        max_tecnologico = _program_credit(program, "creditos_grupo_tecnologico_max")
        min_total = _program_credit(program, "creditos_total_min")

        facts.append(Compound("min_creditos_basico", [prog, Atom(min_basico)]))
        facts.append(Compound("min_creditos_especifico", [prog, Atom(min_especifico)]))
        facts.append(Compound("max_creditos_tecnologico", [prog, Atom(max_tecnologico)]))
        facts.append(Compound("min_creditos_total", [prog, Atom(min_total)]))

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
        if prazo_qual is None:
            prazo_qual = self._derive_prazo_qualificacao(student, program)
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
            creditos = int(float(activity.get("creditos", 0)))
            running = (category_running.get(grupo, 0) if grupo is not None else 0) + creditos
            limite = max_tecnologico if grupo == "tecnologico" else None
            if limite is None or running <= limite:
                facts.append(Compound("nao_excede_limite_categoria", [atv, sid]))
            if grupo is not None and grupo in category_running:
                category_running[grupo] = running

        # Pontuação RL05 de produções é calculada à parte (_score_productions), pois cada
        # produção resolve o peso vigente na sua data de publicação (ADR-0003) — um fato
        # global relevancia_peso(Nivel, Peso) não comportaria pesos distintos por versão.
        return facts, totals, risk_flags

    def _build_engine(self, facts: list[Compound]) -> InferenceEngine:
        fact_base = FactBase()
        for fact in facts:
            fact_base.add_fact(fact)
        rule_base = RuleBase()
        register_all(rule_base)
        return InferenceEngine(fact_base, rule_base)

    # -- consultas ao motor -------------------------------------------------------------

    def evaluate_activity_eligibility(
        self,
        *,
        activity_id: str,
        student_id: str,
        data_ingresso: str | None,
        data_realizacao: str | None,
        tem_comprovante: bool,
        tipo_ativo: bool,
        categoria_creditos_aprovados: float,
        pontuacao_base: float,
        limite_categoria: float | None,
    ) -> bool:
        """Avalia RL04 (atividade_elegivel) para uma única atividade recém-registrada."""
        sid = Atom(student_id)
        atv = Atom(activity_id)
        facts: list[Compound] = []

        ingresso = _parse_date(data_ingresso)
        realizacao = _parse_date(data_realizacao)
        if realizacao is not None and ingresso is not None and realizacao >= ingresso:
            facts.append(Compound("dentro_periodo_curso", [atv, sid]))
        if tem_comprovante:
            facts.append(Compound("tem_comprovante", [atv]))
        if tipo_ativo:
            facts.append(Compound("tipo_ativo", [atv]))
        if limite_categoria is None or categoria_creditos_aprovados + pontuacao_base <= limite_categoria:
            facts.append(Compound("nao_excede_limite_categoria", [atv, sid]))

        engine = self._build_engine(facts)
        return bool(engine.query(Compound("atividade_elegivel", [atv, sid])))

    def _query_eligible_activities(
        self,
        engine: InferenceEngine,
        student_id: str,
        activities: list[dict[str, Any]],
    ) -> list[str]:
        eligible: list[str] = []
        for activity in activities:
            goal = Compound("atividade_elegivel", [Atom(activity["id"]), Atom(student_id)])
            if engine.query(goal):
                eligible.append(activity["id"])
        return eligible

    def _score_productions(
        self,
        productions: list[dict[str, Any]],
        weight_versions: list[dict[str, Any]],
    ) -> list[PontuacaoProducao]:
        """Pontua cada produção (RL05) com o peso vigente na sua data de publicação.

        Para cada produção resolve o conjunto de pesos vigente em `_publication_when`
        (data_realizacao se publicada; agora, provisório, se submetida/aceita) e delega o
        cálculo `base × peso` ao motor via score_production, mantendo o engine isolado.

        Args:
            productions: Produções aprovadas do aluno (com nível e dados de publicação).
            weight_versions: Versões de pesos Qualis do programa.

        Returns:
            Lista de PontuacaoProducao para as produções com nível classificado.
        """
        scores: list[PontuacaoProducao] = []
        for production in productions:
            nivel = production.get("nivel")
            if not nivel:
                continue
            when = self._publication_when(production)
            weights = resolve_weights_at(weight_versions, when) or PESO_POR_NIVEL
            peso = weights.get(nivel)
            if peso is None:
                continue
            base = float(production.get("pontuacao_base", 0))
            score = self.score_production(nivel, float(peso), base)
            scores.append(
                PontuacaoProducao(
                    producao_id=production["id"],
                    score=score,
                    nivel_veiculo=nivel,
                    peso_aplicado=round(float(peso), 4),
                )
            )
        return scores

    def _publication_when(self, production: dict[str, Any]) -> datetime:
        """Resolve a data de referência para o peso de uma produção.

        Produção publicada usa a data de publicação (reaproveita data_realizacao) — o peso
        fica travado na versão vigente naquela data. Produção submetida/aceita usa o momento
        atual (peso vigente provisório).
        """
        if production.get("status_publicacao") == "publicado":
            when = _to_datetime(production.get("data_realizacao"))
            if when is not None:
                return when
        return datetime.now(timezone.utc)

    def _derive_situacao(self, apto: bool, em_risco: bool, student: dict[str, Any]) -> SituacaoInferida:
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
        # M2 Correção: Sincronização de chaves no checklist de saída
        min_basico = _program_credit(program, "creditos_grupo_basico_min")
        min_especifico = _program_credit(program, "creditos_grupo_especifico_min")
        max_tecnologico = _program_credit(program, "creditos_grupo_tecnologico_max")
        min_total = _program_credit(program, "creditos_total_min")

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
        messages: list[str] = []
        if risk_flags["prazo_estourado"]:
            messages.append(f"Prazo final expirado em {student.get('prazo_final')}")
        if risk_flags["creditos_insuficientes"]:
            # M2 Correção: Chave de exibição da mensagem de log sincronizada
            messages.append(
                f"Créditos insuficientes ({totals['total']}/{_program_credit(program, 'creditos_total_min')})"
            )
        if risk_flags["qualificacao_prazo_proximo"]:
            messages.append("Qualificação pendente com prazo próximo")
        if risk_flags["plano_atrasado"]:
            messages.append("Plano de trabalho atrasado em relação ao cronograma")
        return messages

    def _fracao_prazo_decorrida(self, student: dict[str, Any]) -> float:
        ingresso = _parse_date(student.get("data_ingresso"))
        prazo = _parse_date(student.get("prazo_final"))
        if ingresso is None or prazo is None or prazo <= ingresso:
            return 0.0
        elapsed = (date.today() - ingresso).days
        span = (prazo - ingresso).days
        return max(0.0, min(1.0, elapsed / span))

    def _derive_prazo_qualificacao(
        self, student: dict[str, Any], program: dict[str, Any]
    ) -> date | None:
        ingresso = _parse_date(student.get("data_ingresso"))
        meses = program.get("meses_ate_qualificacao")
        if ingresso is None or meses is None:
            return None
        return _add_months(ingresso, int(meses))

    def _is_plano_concluido(self, tasks: list[dict[str, Any]]) -> bool:
        non_defesa = [t for t in tasks if not t.get("is_defesa")]
        return bool(non_defesa) and all(t.get("concluida") for t in non_defesa)

    def _is_plano_atrasado(self, student: dict[str, Any], tasks: list[dict[str, Any]]) -> bool:
        non_defesa = [t for t in tasks if not t.get("is_defesa")]
        if not non_defesa:
            return False
        expected = self._fracao_prazo_decorrida(student)
        concluidas = len([t for t in non_defesa if t.get("concluida")])
        actual = concluidas / len(non_defesa)
        return actual < expected

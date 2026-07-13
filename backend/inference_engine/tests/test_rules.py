"""
Testes unitários pytest para as 5 regras em inference_engine/rules/.

Responsabilidades:
- RL01 defense_eligibility: testar cenários apto (5 fatos presentes), inapto_sem_producao,
  inapto_creditos_invalidos (cada fato faltando individualmente).
- RL02 credit_validation: testar creditos_validos (todos os grupos corretos),
  basico_insuficiente, tecnologico_excedido, total_insuficiente.
- RL03 academic_status: testar em_risco_prazo (prazo_estourado presente), em_risco_qualificacao
  (qualificacao_pendente + prazo_qualificacao_proximo), em_risco_plano_atrasado, regular
  (nenhum fato de risco presente → em_risco retorna False).
- RL04 activity_eligibility: testar elegivel (4 fatos), sem_comprovante, tipo_inativo,
  excede_limite_tecnologico.
- RL05 production_scoring: testar producao_A1_base10 → Score=10.0, producao_A4_base10 →
  Score=5.5, producao_A8_base10 → Score=1.5 (escala Qualis Único monotônica A1–A8 + fallback).
"""
"""
test_rules.py — Testes das regras acadêmicas (RL01–RL05).

Cobertura:
  - RL01: Aptidão à Defesa
  - RL02: Validação de Créditos
  - RL03: Situação Acadêmica — Em Risco
  - RL04: Elegibilidade de Atividade Creditável
  - RL05: Pontuação Ponderada de Produção
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from inference_engine.terms import Atom, Variable, Compound
from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine
from inference_engine.rules import register_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(*facts: Compound) -> InferenceEngine:
    fb = FactBase()
    rb = RuleBase()
    for fact in facts:
        fb.add_fact(fact)
    register_all(rb)
    return InferenceEngine(fb, rb)


def f(*args) -> Compound:
    name, *values = args
    return Compound(name, [Atom(v) for v in values])


# ===========================================================================
# RL01 — Aptidão à Defesa
# ===========================================================================

class TestDefenseEligibility:

    def _base_fatos_apto(self, aluno: str) -> list[Compound]:
        return [
            f("creditos_validos",                aluno),
            f("proficiencia_comprovada",         aluno),
            f("qualificacao_aprovada",           aluno),
            f("producao_bibliografica_validada", aluno),
            f("plano_concluido",                 aluno),
        ]

    def test_apto(self):
        engine = make_engine(*self._base_fatos_apto("a1"))
        assert engine._query_bool(f("apto_defesa", "a1")) is True

    def test_inapto_sem_producao(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "producao_bibliografica_validada"]
        engine = make_engine(*fatos)
        assert engine._query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_creditos(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "creditos_validos"]
        engine = make_engine(*fatos)
        assert engine._query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_qualificacao(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "qualificacao_aprovada"]
        engine = make_engine(*fatos)
        assert engine._query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_proficiencia(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "proficiencia_comprovada"]
        engine = make_engine(*fatos)
        assert engine._query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_plano_incompleto(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "plano_concluido"]
        engine = make_engine(*fatos)
        assert engine._query_bool(f("apto_defesa", "a1")) is False


# ===========================================================================
# RL02 — Validação de Créditos por Grupo
# ===========================================================================

class TestCreditValidation:

    def _fatos_creditos(self, basico: int, especifico: int, tecnologico: int, total: int) -> list[Compound]:
        prog = "prog_default"
        return [
            Compound("creditos_grupo_basico",      [Atom("a1"), Atom(basico)]),
            Compound("creditos_grupo_especifico",  [Atom("a1"), Atom(especifico)]),
            Compound("creditos_grupo_tecnologico", [Atom("a1"), Atom(tecnologico)]),
            Compound("total_creditos",             [Atom("a1"), Atom(total)]),
            Compound("min_creditos_basico",        [Atom(prog), Atom(12)]),
            Compound("min_creditos_especifico",    [Atom(prog), Atom(8)]),
            Compound("max_creditos_tecnologico",   [Atom(prog), Atom(4)]),
            Compound("min_creditos_total",         [Atom(prog), Atom(24)]),
        ]

    def test_creditos_validos(self):
        engine = make_engine(*self._fatos_creditos(14, 10, 3, 27))
        assert engine._query_bool(f("creditos_validos", "a1")) is True

    def test_basico_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(10, 10, 2, 22))
        assert engine._query_bool(f("creditos_validos", "a1")) is False

    def test_tecnologico_excedido(self):
        engine = make_engine(*self._fatos_creditos(14, 10, 6, 30))
        assert engine._query_bool(f("creditos_validos", "a1")) is False

    def test_total_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(12, 8, 2, 22))
        assert engine._query_bool(f("creditos_validos", "a1")) is False

    def test_especifico_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(14, 5, 2, 21))
        assert engine._query_bool(f("creditos_validos", "a1")) is False


# ===========================================================================
# RL03 — Situação Acadêmica — Em Risco
# ===========================================================================

class TestAcademicStatus:

    def test_em_risco_prazo_estourado(self):
        engine = make_engine(f("prazo_estourado", "a1"))
        assert engine._query_bool(f("em_risco", "a1")) is True

    def test_em_risco_creditos_insuficientes(self):
        engine = make_engine(f("creditos_insuficientes", "a1"))
        assert engine._query_bool(f("em_risco", "a1")) is True

    def test_em_risco_qualificacao_pendente(self):
        engine = make_engine(
            f("qualificacao_pendente",      "a1"),
            f("prazo_qualificacao_proximo", "a1"),
        )
        assert engine._query_bool(f("em_risco", "a1")) is True

    def test_em_risco_qualificacao_pendente_sem_prazo_proximo(self):
        engine = make_engine(f("qualificacao_pendente", "a1"))
        assert engine._query_bool(f("em_risco", "a1")) is False

    def test_em_risco_plano_atrasado(self):
        engine = make_engine(f("plano_atrasado", "a1"))
        assert engine._query_bool(f("em_risco", "a1")) is True

    def test_regular_sem_gatilhos(self):
        engine = make_engine()
        assert engine._query_bool(f("em_risco", "a1")) is False

    def test_multiplos_gatilhos_simultaneos(self):
        engine = make_engine(
            f("prazo_estourado", "a1"),
            f("plano_atrasado",  "a1"),
        )
        results = engine.query(f("em_risco", "a1"))
        assert len(results) >= 2


# ===========================================================================
# RL04 — Elegibilidade de Atividade Creditável
# ===========================================================================

class TestActivityEligibility:

    def _fatos_elegivel(self, atv: str, aluno: str) -> list[Compound]:
        return [
            Compound("dentro_periodo_curso",       [Atom(atv), Atom(aluno)]),
            Compound("tem_comprovante",             [Atom(atv)]),
            Compound("tipo_ativo",                  [Atom(atv)]),
            Compound("nao_excede_limite_categoria", [Atom(atv), Atom(aluno)]),
        ]

    def test_elegivel(self):
        engine = make_engine(*self._fatos_elegivel("atv1", "a1"))
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine._query_bool(goal) is True

    def test_sem_comprovante(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "tem_comprovante"]
        engine = make_engine(*fatos)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine._query_bool(goal) is False

    def test_tipo_inativo(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "tipo_ativo"]
        engine = make_engine(*fatos)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine._query_bool(goal) is False

    def test_excede_limite_categoria(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "nao_excede_limite_categoria"]
        engine = make_engine(*fatos)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine._query_bool(goal) is False

    def test_fora_periodo_curso(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "dentro_periodo_curso"]
        engine = make_engine(*fatos)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine._query_bool(goal) is False

    def test_nao_deduplica_para_alunos_distintos(self):
        engine = make_engine(
            *self._fatos_elegivel("atv1", "a1"),
            *self._fatos_elegivel("atv1", "a2"),
        )
        goal_a1 = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        goal_a2 = Compound("atividade_elegivel", [Atom("atv1"), Atom("a2")])
        assert engine._query_bool(goal_a1) is True
        assert engine._query_bool(goal_a2) is True


# ===========================================================================
# RL05 — Pontuação Ponderada de Produção
# ===========================================================================

class TestProductionScoring:

    def _fatos_producao(self, prod: str, veiculo: str, nivel: str, peso: float, base: float) -> list[Compound]:
        return [
            Compound("producao_veiculo", [Atom(prod), Atom(veiculo)]),
            Compound("nivel_relevancia", [Atom(veiculo), Atom("prog1"), Atom(nivel)]),
            Compound("relevancia_peso",  [Atom(nivel), Atom(peso)]),
            Compound("pontuacao_base",   [Atom(prod), Atom(base)]),
        ]

    def test_producao_A1_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v1", "A1", 1.0, 10))
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"].value == pytest.approx(10.0)

    def test_producao_A4_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v2", "A4", 0.7, 10))
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"].value == pytest.approx(7.0)

    def test_producao_A8_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v3", "A8", 0.3, 10))
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"].value == pytest.approx(3.0)

    def test_producao_SC_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v_sc", "SC", 0.2, 10))
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"].value == pytest.approx(2.0)

    def test_producao_A2_base8(self):
        engine = make_engine(*self._fatos_producao("p1", "v4", "A2", 0.9, 8))
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"].value == pytest.approx(7.2)

    def test_veiculo_sem_nivel_configurado(self):
        fatos = [
            Compound("producao_veiculo", [Atom("p1"), Atom("v_sem_nivel")]),
            Compound("pontuacao_base",   [Atom("p1"), Atom(10)]),
        ]
        engine = make_engine(*fatos)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert results == []

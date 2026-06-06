"""
Testes unitários pytest para o módulo inference_engine/resolver.py.

Responsabilidades:
- Testar solve() com goal que unifica diretamente com fato na FactBase → yield substituição.
- Testar solve() com goal que requer encadeamento de regra (head + body) → yield substituição.
- Testar solve() quando nenhum fato ou regra satisfaz o goal → iterador vazio.
- Testar solve() com built-in aritmético Compound('gte', [Atom(14), Atom(12)]) → resolvido.
- Testar que renomeação de variáveis evita colisão entre cláusulas da RuleBase.
- Testar ausência de backtracking: falha parcial em body não tenta caminho alternativo.
"""
"""
test_resolver.py — Testes do motor de inferência.

Cobertura:
  - Unificação (terms + unification + substitution)
  - Resolver com fatos diretos, regras simples e built-ins aritméticos
  - RL01: Aptidão à Defesa
  - RL02: Validação de Créditos
  - RL03: Situação Acadêmica — Em Risco
  - RL04: Elegibilidade de Atividade Creditável
  - RL05: Pontuação Ponderada de Produção

Os testes de domínio usam fatos e regras simples antes de testar as regras acadêmicas,
validando o ciclo completo conforme a Definição de Concluído.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from inference_engine.terms import Atom, Variable, Compound
from inference_engine.unification import unify
from inference_engine.substitution import apply
from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine
from inference_engine.rules import register_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(*facts: Compound, academic_rules: bool = False) -> InferenceEngine:
    """Cria um InferenceEngine com os fatos fornecidos."""
    fb = FactBase()
    rb = RuleBase()
    for fact in facts:
        fb.add_fact(fact)
    if academic_rules:
        register_all(rb)
    return InferenceEngine(fb, rb)


def f(*args) -> Compound:
    """Atalho: constrói Compound('nome', [Atom(a), ...])."""
    name, *values = args
    return Compound(name, [Atom(v) for v in values])


# ===========================================================================
# 1. Testes de unificação e substituição
# ===========================================================================

class TestUnification:

    def test_atom_igual(self):
        result = unify(Atom(42), Atom(42), {})
        assert result == {}

    def test_atom_diferente(self):
        result = unify(Atom("a"), Atom("b"), {})
        assert result is None

    def test_variable_bind(self):
        X = Variable("X")
        result = unify(X, Atom("hello"), {})
        assert result == {"X": Atom("hello")}

    def test_variable_ja_vinculada(self):
        X = Variable("X")
        subst = {"X": Atom(10)}
        result = unify(X, Atom(10), subst)
        assert result is not None

    def test_variable_ja_vinculada_diferente(self):
        X = Variable("X")
        subst = {"X": Atom(10)}
        result = unify(X, Atom(99), subst)
        assert result is None

    def test_occur_check(self):
        # X não pode ser unificado com f(X)
        X = Variable("X")
        compound = Compound("f", [X])
        result = unify(X, compound, {})
        assert result is None

    def test_compound_mesmo_functor(self):
        c1 = Compound("pai", [Atom("joao"), Variable("Y")])
        c2 = Compound("pai", [Atom("joao"), Atom("maria")])
        result = unify(c1, c2, {})
        assert result == {"Y": Atom("maria")}

    def test_compound_functor_diferente(self):
        c1 = Compound("pai", [Atom("a")])
        c2 = Compound("mae", [Atom("a")])
        assert unify(c1, c2, {}) is None

    def test_compound_aridade_diferente(self):
        c1 = Compound("f", [Atom(1)])
        c2 = Compound("f", [Atom(1), Atom(2)])
        assert unify(c1, c2, {}) is None

    def test_apply_atom(self):
        assert apply(Atom(5), {}) == Atom(5)

    def test_apply_variable_vinculada(self):
        X = Variable("X")
        result = apply(X, {"X": Atom("valor")})
        assert result == Atom("valor")

    def test_apply_variable_nao_vinculada(self):
        X = Variable("X")
        assert apply(X, {}) == X

    def test_apply_compound(self):
        c = Compound("f", [Variable("X"), Atom(2)])
        result = apply(c, {"X": Atom(1)})
        assert result == Compound("f", [Atom(1), Atom(2)])

    def test_apply_cadeia_substituicao(self):
        # X→Y, Y→42: apply(X) deve retornar Atom(42)
        result = apply(Variable("X"), {"X": Variable("Y"), "Y": Atom(42)})
        assert result == Atom(42)


# ===========================================================================
# 2. Testes simples do resolver (não acadêmicos) — ciclo completo
# ===========================================================================

class TestResolverSimples:

    def test_fato_direto(self):
        """Motor encontra um fato diretamente na FactBase."""
        engine = make_engine(f("gosta", "joao", "pizza"))
        results = engine.query(f("gosta", "joao", "pizza"))
        assert len(results) >= 1

    def test_fato_ausente(self):
        """Motor retorna vazio quando o fato não existe."""
        engine = make_engine(f("gosta", "joao", "pizza"))
        results = engine.query(f("gosta", "joao", "sushi"))
        assert results == []

    def test_variavel_no_goal(self):
        """Motor unifica variável com fato existente."""
        engine = make_engine(
            f("cidade", "sao_paulo", "sp"),
            f("cidade", "recife", "pe"),
        )
        goal = Compound("cidade", [Variable("Nome"), Atom("sp")])
        results = engine.query(goal)
        assert len(results) == 1
        assert results[0]["Nome"] == Atom("sao_paulo")

    def test_regra_simples_dois_fatos(self):
        """Regra: avô(X,Z) :- pai(X,Y), pai(Y,Z)."""
        fb = FactBase()
        rb = RuleBase()
        fb.add_fact(Compound("pai", [Atom("ana"), Atom("beto")]))
        fb.add_fact(Compound("pai", [Atom("beto"), Atom("carla")]))
        X, Y, Z = Variable("X"), Variable("Y"), Variable("Z")
        rb.add_rule(
            head=Compound("avo", [X, Z]),
            body=[Compound("pai", [X, Y]), Compound("pai", [Y, Z])],
        )
        engine = InferenceEngine(fb, rb)
        results = engine.query(Compound("avo", [Atom("ana"), Atom("carla")]))
        assert len(results) >= 1

    def test_regra_falha_conjuncao(self):
        """Regra falha se segunda condição do body não for satisfeita."""
        fb = FactBase()
        rb = RuleBase()
        fb.add_fact(Compound("pai", [Atom("ana"), Atom("beto")]))
        # pai(beto, carla) ausente
        X, Y, Z = Variable("X"), Variable("Y"), Variable("Z")
        rb.add_rule(
            head=Compound("avo", [X, Z]),
            body=[Compound("pai", [X, Y]), Compound("pai", [Y, Z])],
        )
        engine = InferenceEngine(fb, rb)
        results = engine.query(Compound("avo", [Atom("ana"), Atom("carla")]))
        assert results == []

    def test_query_bool(self):
        engine = make_engine(f("ativo", "modulo_a"))
        assert engine.query_bool(f("ativo", "modulo_a")) is True
        assert engine.query_bool(f("ativo", "modulo_b")) is False


# ===========================================================================
# 3. Testes de built-ins aritméticos
# ===========================================================================

class TestBuiltins:

    def test_gte_true(self):
        engine = make_engine()
        goal = Compound("gte", [Atom(10), Atom(5)])
        assert engine.query_bool(goal) is True

    def test_gte_false(self):
        engine = make_engine()
        goal = Compound("gte", [Atom(3), Atom(5)])
        assert engine.query_bool(goal) is False

    def test_lte_true(self):
        engine = make_engine()
        goal = Compound("lte", [Atom(2), Atom(4)])
        assert engine.query_bool(goal) is True

    def test_lte_false(self):
        engine = make_engine()
        goal = Compound("lte", [Atom(7), Atom(4)])
        assert engine.query_bool(goal) is False

    def test_mul_resultado(self):
        engine = make_engine()
        Score = Variable("Score")
        goal = Compound("mul", [Atom(10), Atom(2.0), Score])
        results = engine.query(goal)
        assert len(results) == 1
        assert results[0]["Score"] == Atom(20.0)


# ===========================================================================
# 4. RL01 — Aptidão à Defesa
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
        engine = make_engine(*self._base_fatos_apto("a1"), academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is True

    def test_inapto_sem_producao(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "producao_bibliografica_validada"]
        engine = make_engine(*fatos, academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_creditos(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "creditos_validos"]
        engine = make_engine(*fatos, academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_qualificacao(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "qualificacao_aprovada"]
        engine = make_engine(*fatos, academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_sem_proficiencia(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "proficiencia_comprovada"]
        engine = make_engine(*fatos, academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is False

    def test_inapto_plano_incompleto(self):
        fatos = [ft for ft in self._base_fatos_apto("a1")
                 if ft.functor != "plano_concluido"]
        engine = make_engine(*fatos, academic_rules=True)
        assert engine.query_bool(f("apto_defesa", "a1")) is False


# ===========================================================================
# 5. RL02 — Validação de Créditos por Grupo
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
        engine = make_engine(*self._fatos_creditos(14, 10, 3, 27), academic_rules=True)
        assert engine.query_bool(f("creditos_validos", "a1")) is True

    def test_basico_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(10, 10, 2, 22), academic_rules=True)
        assert engine.query_bool(f("creditos_validos", "a1")) is False

    def test_tecnologico_excedido(self):
        engine = make_engine(*self._fatos_creditos(14, 10, 6, 30), academic_rules=True)
        assert engine.query_bool(f("creditos_validos", "a1")) is False

    def test_total_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(12, 8, 2, 22), academic_rules=True)
        assert engine.query_bool(f("creditos_validos", "a1")) is False

    def test_especifico_insuficiente(self):
        engine = make_engine(*self._fatos_creditos(14, 5, 2, 21), academic_rules=True)
        assert engine.query_bool(f("creditos_validos", "a1")) is False


# ===========================================================================
# 6. RL03 — Situação Acadêmica — Em Risco
# ===========================================================================

class TestAcademicStatus:

    def test_em_risco_prazo_estourado(self):
        engine = make_engine(f("prazo_estourado", "a1"), academic_rules=True)
        assert engine.query_bool(f("em_risco", "a1")) is True

    def test_em_risco_creditos_insuficientes(self):
        engine = make_engine(f("creditos_insuficientes", "a1"), academic_rules=True)
        assert engine.query_bool(f("em_risco", "a1")) is True

    def test_em_risco_qualificacao_pendente(self):
        engine = make_engine(
            f("qualificacao_pendente",      "a1"),
            f("prazo_qualificacao_proximo", "a1"),
            academic_rules=True,
        )
        assert engine.query_bool(f("em_risco", "a1")) is True

    def test_em_risco_qualificacao_pendente_sem_prazo_proximo(self):
        """Qualificação pendente mas prazo não próximo → não deve ser em risco por esta cláusula."""
        engine = make_engine(f("qualificacao_pendente", "a1"), academic_rules=True)
        # Nenhum outro gatilho presente → não em risco
        assert engine.query_bool(f("em_risco", "a1")) is False

    def test_em_risco_plano_atrasado(self):
        engine = make_engine(f("plano_atrasado", "a1"), academic_rules=True)
        assert engine.query_bool(f("em_risco", "a1")) is True

    def test_regular_sem_gatilhos(self):
        """Nenhum fato de risco → aluno não é em_risco."""
        engine = make_engine(academic_rules=True)
        assert engine.query_bool(f("em_risco", "a1")) is False

    def test_multiplos_gatilhos_simultaneos(self):
        """Dois gatilhos simultâneos devem retornar múltiplas soluções."""
        engine = make_engine(
            f("prazo_estourado",  "a1"),
            f("plano_atrasado",   "a1"),
            academic_rules=True,
        )
        results = engine.query(f("em_risco", "a1"))
        assert len(results) >= 2


# ===========================================================================
# 7. RL04 — Elegibilidade de Atividade Creditável
# ===========================================================================

class TestActivityEligibility:

    def _fatos_elegivel(self, atv: str, aluno: str) -> list[Compound]:
        return [
            Compound("dentro_periodo_curso",         [Atom(atv), Atom(aluno)]),
            Compound("tem_comprovante",               [Atom(atv)]),
            Compound("tipo_ativo",                    [Atom(atv)]),
            Compound("nao_excede_limite_categoria",   [Atom(atv), Atom(aluno)]),
        ]

    def test_elegivel(self):
        engine = make_engine(*self._fatos_elegivel("atv1", "a1"), academic_rules=True)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine.query_bool(goal) is True

    def test_sem_comprovante(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "tem_comprovante"]
        engine = make_engine(*fatos, academic_rules=True)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine.query_bool(goal) is False

    def test_tipo_inativo(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "tipo_ativo"]
        engine = make_engine(*fatos, academic_rules=True)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine.query_bool(goal) is False

    def test_excede_limite_categoria(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "nao_excede_limite_categoria"]
        engine = make_engine(*fatos, academic_rules=True)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine.query_bool(goal) is False

    def test_fora_periodo_curso(self):
        fatos = [ft for ft in self._fatos_elegivel("atv1", "a1")
                 if ft.functor != "dentro_periodo_curso"]
        engine = make_engine(*fatos, academic_rules=True)
        goal = Compound("atividade_elegivel", [Atom("atv1"), Atom("a1")])
        assert engine.query_bool(goal) is False


# ===========================================================================
# 8. RL05 — Pontuação Ponderada de Produção
# ===========================================================================

class TestProductionScoring:

    def _fatos_producao(self, prod: str, veiculo: str, nivel: str, peso: float, base: float) -> list[Compound]:
        return [
            Compound("producao_veiculo",  [Atom(prod), Atom(veiculo)]),
            Compound("nivel_relevancia",  [Atom(veiculo), Atom("prog1"), Atom(nivel)]),
            Compound("relevancia_peso",   [Atom(nivel), Atom(peso)]),
            Compound("pontuacao_base",    [Atom(prod), Atom(base)]),
        ]

    def test_producao_A1_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v1", "A1", 2.0, 10), academic_rules=True)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"] == Atom(20.0)

    def test_producao_B_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v2", "B", 1.0, 10), academic_rules=True)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"] == Atom(10.0)

    def test_producao_C_base10(self):
        engine = make_engine(*self._fatos_producao("p1", "v3", "C", 0.5, 10), academic_rules=True)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"] == Atom(5.0)

    def test_producao_A2_base8(self):
        engine = make_engine(*self._fatos_producao("p1", "v4", "A2", 1.5, 8), academic_rules=True)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert len(results) == 1
        assert results[0]["Score"] == Atom(12.0)

    def test_veiculo_sem_nivel_configurado(self):
        """Produção sem nivel_relevancia cadastrado → sem pontuação."""
        fatos = [
            Compound("producao_veiculo", [Atom("p1"), Atom("v_sem_nivel")]),
            Compound("pontuacao_base",   [Atom("p1"), Atom(10)]),
        ]
        engine = make_engine(*fatos, academic_rules=True)
        Score = Variable("Score")
        results = engine.query(Compound("pontuacao_producao", [Atom("p1"), Score]))
        assert results == []
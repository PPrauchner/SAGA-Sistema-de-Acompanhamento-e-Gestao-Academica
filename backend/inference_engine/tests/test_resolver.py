"""
test_resolver.py — Testes do motor de inferência (camada base).

Cobertura:
  - Unificação (terms + unification + substitution)
  - Resolver com fatos diretos, regras simples e built-ins aritméticos

Testes das regras acadêmicas (RL01–RL05) estão em test_rules.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from inference_engine.terms import Atom, Variable, Compound
from inference_engine.unification import unify
from inference_engine.substitution import apply
from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine


def make_engine(*facts: Compound) -> InferenceEngine:
    fb = FactBase()
    rb = RuleBase()
    for fact in facts:
        fb.add_fact(fact)
    return InferenceEngine(fb, rb)


def f(*args) -> Compound:
    name, *values = args
    return Compound(name, [Atom(v) for v in values])


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
        result = apply(Variable("X"), {"X": Variable("Y"), "Y": Atom(42)})
        assert result == Atom(42)


class TestResolverSimples:

    def test_fato_direto(self):
        engine = make_engine(f("gosta", "joao", "pizza"))
        results = engine.query(f("gosta", "joao", "pizza"))
        assert len(results) >= 1

    def test_fato_ausente(self):
        engine = make_engine(f("gosta", "joao", "pizza"))
        results = engine.query(f("gosta", "joao", "sushi"))
        assert results == []

    def test_variavel_no_goal(self):
        engine = make_engine(
            f("cidade", "sao_paulo", "sp"),
            f("cidade", "recife", "pe"),
        )
        goal = Compound("cidade", [Variable("Nome"), Atom("sp")])
        results = engine.query(goal)
        assert len(results) == 1
        assert results[0]["Nome"] == Atom("sao_paulo")

    def test_regra_simples_dois_fatos(self):
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
        fb = FactBase()
        rb = RuleBase()
        fb.add_fact(Compound("pai", [Atom("ana"), Atom("beto")]))
        X, Y, Z = Variable("X"), Variable("Y"), Variable("Z")
        rb.add_rule(
            head=Compound("avo", [X, Z]),
            body=[Compound("pai", [X, Y]), Compound("pai", [Y, Z])],
        )
        engine = InferenceEngine(fb, rb)
        results = engine.query(Compound("avo", [Atom("ana"), Atom("carla")]))
        assert results == []

    def test__query_bool(self):
        engine = make_engine(f("ativo", "modulo_a"))
        assert engine._query_bool(f("ativo", "modulo_a")) is True
        assert engine._query_bool(f("ativo", "modulo_b")) is False


class TestBuiltins:

    def test_gte_true(self):
        engine = make_engine()
        goal = Compound("gte", [Atom(10), Atom(5)])
        assert engine._query_bool(goal) is True

    def test_gte_false(self):
        engine = make_engine()
        goal = Compound("gte", [Atom(3), Atom(5)])
        assert engine._query_bool(goal) is False

    def test_lte_true(self):
        engine = make_engine()
        goal = Compound("lte", [Atom(2), Atom(4)])
        assert engine._query_bool(goal) is True

    def test_lte_false(self):
        engine = make_engine()
        goal = Compound("lte", [Atom(7), Atom(4)])
        assert engine._query_bool(goal) is False

    def test_mul_resultado(self):
        engine = make_engine()
        Score = Variable("Score")
        goal = Compound("mul", [Atom(10), Atom(2.0), Score])
        results = engine.query(goal)
        assert len(results) == 1
        assert results[0]["Score"] == Atom(20.0)
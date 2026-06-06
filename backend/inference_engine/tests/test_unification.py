"""
Testes unitários pytest para o módulo inference_engine/unification.py.

Responsabilidades:
- Testar unify(Atom, Atom) com mesmo valor → retorna subst inalterada.
- Testar unify(Atom, Atom) com valores diferentes → retorna None.
- Testar unify(Variable(X), Atom) quando X não está em subst → retorna {X: Atom}.
- Testar unify(Variable(X), term) quando X já está em subst → unifica subst[X] com term.
- Testar occur check: Variable(X) não pode ser unificado com Compound contendo X.
- Testar unify(Compound, Compound) com mesmo functor e aridade → unifica argumentos par a par.
- Testar unify(Compound, Compound) com functores ou aridades diferentes → retorna None.
"""
import pytest

from inference_engine.terms import Atom, Variable, Compound
from inference_engine.unification import unify


class TestUnifyAtomAtom:
    def test_same_atom_returns_subst(self):
        subst = {}
        result = unify(Atom("a"), Atom("a"), subst)
        assert result == {}

    def test_same_atom_preserves_existing_subst(self):
        subst = {"X": Atom("b")}
        result = unify(Atom("a"), Atom("a"), subst)
        assert result == {"X": Atom("b")}

    def test_different_atoms_returns_none(self):
        assert unify(Atom("a"), Atom("b"), {}) is None

    def test_same_integer_atom(self):
        assert unify(Atom(42), Atom(42), {}) == {}

    def test_different_integer_atoms(self):
        assert unify(Atom(1), Atom(2), {}) is None

    def test_atom_vs_compound_returns_none(self):
        assert unify(Atom("a"), Compound("f", [Atom("a")]), {}) is None


class TestUnifyVariableNotInSubst:
    def test_variable_unified_with_atom(self):
        result = unify(Variable("X"), Atom("a"), {})
        assert result == {"X": Atom("a")}

    def test_doe_example(self):
        """DoD: unify(Variable('X'), Atom('a'), {}) retorna {'X': Atom('a')}"""
        result = unify(Variable("X"), Atom("a"), {})
        assert result == {"X": Atom("a")}

    def test_variable_unified_with_compound(self):
        c = Compound("f", [Atom("b")])
        result = unify(Variable("X"), c, {})
        assert result == {"X": c}

    def test_variable_on_right_side(self):
        result = unify(Atom("a"), Variable("X"), {})
        assert result == {"X": Atom("a")}

    def test_two_fresh_variables(self):
        result = unify(Variable("X"), Variable("Y"), {})
        assert result == {"X": Variable("Y")}


class TestUnifyVariableInSubst:
    def test_variable_already_bound_matches(self):
        subst = {"X": Atom("a")}
        result = unify(Variable("X"), Atom("a"), subst)
        assert result == {"X": Atom("a")}

    def test_variable_already_bound_fails(self):
        subst = {"X": Atom("a")}
        result = unify(Variable("X"), Atom("b"), subst)
        assert result is None

    def test_variable_bound_to_variable(self):
        subst = {"X": Variable("Y")}
        result = unify(Variable("X"), Atom("a"), subst)
        assert result is not None
        assert result.get("Y") == Atom("a")


class TestOccurCheck:
    def test_variable_cannot_unify_with_compound_containing_itself(self):
        c = Compound("f", [Variable("X")])
        result = unify(Variable("X"), c, {})
        assert result is None

    def test_variable_can_unify_with_compound_without_itself(self):
        c = Compound("f", [Variable("Y")])
        result = unify(Variable("X"), c, {})
        assert result == {"X": c}

    def test_nested_occur_check(self):
        c = Compound("f", [Compound("g", [Variable("X")])])
        result = unify(Variable("X"), c, {})
        assert result is None


class TestUnifyCompoundCompound:
    def test_same_functor_no_args(self):
        result = unify(Compound("f", []), Compound("f", []), {})
        assert result == {}

    def test_same_functor_same_atom_args(self):
        c1 = Compound("f", [Atom("a"), Atom("b")])
        c2 = Compound("f", [Atom("a"), Atom("b")])
        assert unify(c1, c2, {}) == {}

    def test_same_functor_variable_arg(self):
        c1 = Compound("f", [Variable("X")])
        c2 = Compound("f", [Atom("a")])
        result = unify(c1, c2, {})
        assert result == {"X": Atom("a")}

    def test_different_functors_returns_none(self):
        assert unify(Compound("f", [Atom("a")]), Compound("g", [Atom("a")]), {}) is None

    def test_different_arities_returns_none(self):
        assert unify(Compound("f", [Atom("a")]), Compound("f", [Atom("a"), Atom("b")]), {}) is None

    def test_nested_compounds(self):
        c1 = Compound("f", [Compound("g", [Variable("X")])])
        c2 = Compound("f", [Compound("g", [Atom("a")])])
        result = unify(c1, c2, {})
        assert result == {"X": Atom("a")}

    def test_compound_arg_clash_returns_none(self):
        c1 = Compound("f", [Atom("a"), Atom("b")])
        c2 = Compound("f", [Atom("a"), Atom("c")])
        assert unify(c1, c2, {}) is None

    def test_multiple_variables_unified(self):
        c1 = Compound("f", [Variable("X"), Variable("Y")])
        c2 = Compound("f", [Atom("1"), Atom("2")])
        result = unify(c1, c2, {})
        assert result == {"X": Atom("1"), "Y": Atom("2")}

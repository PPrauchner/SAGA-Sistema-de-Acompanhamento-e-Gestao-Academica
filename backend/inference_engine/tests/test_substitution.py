"""
Testes unitários pytest para o módulo inference_engine/substitution.py.

Responsabilidades:
- Testar apply(Atom, subst) → retorna o Atom inalterado.
- Testar apply(Variable(X), subst) com X em subst → retorna apply(subst[X], subst).
- Testar apply(Variable(X), subst) com X fora de subst → retorna Variable(X).
- Testar apply(Compound, subst) → retorna Compound com args aplicados recursivamente.
- Testar substituição encadeada: Variable(X) → Variable(Y), Variable(Y) → Atom.
"""

from inference_engine.terms import Atom, Variable, Compound
from inference_engine.substitution import apply


class TestApplyAtom:
    def test_atom_returned_unchanged(self):
        a = Atom("a")
        assert apply(a, {}) is a

    def test_atom_with_nonempty_subst(self):
        a = Atom(42)
        subst = {"X": Atom("b")}
        assert apply(a, subst) is a


class TestApplyVariable:
    def test_variable_not_in_subst_returned_unchanged(self):
        v = Variable("X")
        result = apply(v, {})
        assert result == Variable("X")

    def test_variable_in_subst_returns_substituted_value(self):
        result = apply(Variable("X"), {"X": Atom("a")})
        assert result == Atom("a")

    def test_doe_example(self):
        """DoD: apply(Compound('f',[Variable('X')]), {'X': Atom('b')}) retorna Compound('f',[Atom('b')])"""
        result = apply(Compound("f", [Variable("X")]), {"X": Atom("b")})
        assert result == Compound("f", [Atom("b")])

    def test_variable_in_subst_recurses(self):
        """Variable(X) → Variable(Y), Variable(Y) → Atom('a')"""
        subst = {"X": Variable("Y"), "Y": Atom("a")}
        result = apply(Variable("X"), subst)
        assert result == Atom("a")

    def test_variable_bound_to_variable_not_in_subst(self):
        subst = {"X": Variable("Y")}
        result = apply(Variable("X"), subst)
        assert result == Variable("Y")


class TestApplyCompound:
    def test_compound_no_args(self):
        c = Compound("f", [])
        result = apply(c, {})
        assert result == Compound("f", [])

    def test_compound_with_atom_args_unchanged(self):
        c = Compound("f", [Atom("a"), Atom("b")])
        result = apply(c, {})
        assert result == c

    def test_compound_with_variable_arg_substituted(self):
        c = Compound("f", [Variable("X")])
        result = apply(c, {"X": Atom("b")})
        assert result == Compound("f", [Atom("b")])

    def test_compound_multiple_variable_args(self):
        c = Compound("f", [Variable("X"), Variable("Y")])
        subst = {"X": Atom("1"), "Y": Atom("2")}
        result = apply(c, subst)
        assert result == Compound("f", [Atom("1"), Atom("2")])

    def test_nested_compound(self):
        c = Compound("f", [Compound("g", [Variable("X")])])
        result = apply(c, {"X": Atom("a")})
        assert result == Compound("f", [Compound("g", [Atom("a")])])

    def test_compound_with_unbound_variable(self):
        c = Compound("f", [Variable("Z")])
        result = apply(c, {"X": Atom("a")})
        assert result == Compound("f", [Variable("Z")])


class TestChainedSubstitution:
    def test_chain_x_to_y_to_atom(self):
        subst = {"X": Variable("Y"), "Y": Atom("final")}
        assert apply(Variable("X"), subst) == Atom("final")

    def test_triple_chain(self):
        subst = {"X": Variable("Y"), "Y": Variable("Z"), "Z": Atom("end")}
        assert apply(Variable("X"), subst) == Atom("end")

    def test_compound_with_chain(self):
        c = Compound("p", [Variable("X"), Variable("Y")])
        subst = {"X": Variable("Y"), "Y": Atom("v")}
        result = apply(c, subst)
        assert result == Compound("p", [Atom("v"), Atom("v")])

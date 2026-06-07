"""
Testes unitários pytest para o módulo inference_engine/terms.py.

Responsabilidades:
- Testar instanciação e igualdade de Atom: str, int, float e bool.
- Testar instanciação e igualdade de Variable por nome.
- Testar instanciação de Compound com functor e argumentos aninhados.
- Testar que Term aceita Atom, Variable e Compound (checagem de tipo).
- Garantir imutabilidade de Atom (sem alteração de valor após criação).
"""

import pytest

from backend.inference_engine.terms import Atom, Variable, Compound


def test_atom_string_equality():
    assert Atom("a") == Atom("a")


def test_atom_int_equality():
    assert Atom(42) == Atom(42)


def test_atom_float_equality():
    assert Atom(3.14) == Atom(3.14)


def test_atom_bool_equality():
    assert Atom(True) == Atom(True)


def test_variable_equality():
    assert Variable("X") == Variable("X")


def test_variable_different_names():
    assert Variable("X") != Variable("Y")


def test_compound_creation():
    term = Compound("creditos_grupo_basico", [Atom("aluno_001"), Variable("N")])

    assert term.functor == "creditos_grupo_basico"
    assert len(term.args) == 2


def test_compound_equality():
    c1 = Compound("teste", [Atom("a")])
    c2 = Compound("teste", [Atom("a")])

    assert c1 == c2


def test_nested_compound():
    term = Compound("pai", [Atom("joao"), Compound("filho", [Atom("pedro")])])

    assert isinstance(term.args[1], Compound)
    assert term.args[1].functor == "filho"


def test_atom_immutable():
    atom = Atom("valor")

    with pytest.raises(AttributeError):
        atom.value = "novo"


def test_atom_repr():
    assert repr(Atom("a")) == "Atom('a')"


def test_variable_repr():
    assert repr(Variable("X")) == "Variable('X')"


def test_compound_repr():
    term = Compound("pai", [Atom("joao")])

    assert repr(term) == "Compound('pai', [Atom('joao')])"

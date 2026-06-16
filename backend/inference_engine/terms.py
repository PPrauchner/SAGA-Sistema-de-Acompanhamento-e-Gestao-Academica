"""
Representação das unidades de informação manipuladas pelo motor de inferência.

Responsabilidades:
- Definir a classe Atom: valor concreto imutável que aceita str, int, float ou bool.
  Igualdade por valor. Exemplos: Atom('aluno_001'), Atom(42), Atom(True).
- Definir a classe Variable: incógnita identificada por nome string. Igualdade por nome.
  Exemplos: Variable('X'), Variable('Aluno').
- Definir a classe Compound: functor (string) + lista de argumentos (Term). Representa
  predicados/fatos. Exemplos: Compound('creditos_grupo_basico', [Atom('aluno_001'),
  Variable('N')]).
- Definir o tipo union Term = Atom | Variable | Compound.
- Módulo completamente isolado — sem imports de FastAPI, Firebase ou qualquer ORM.
"""

from __future__ import annotations


class Atom:
    """Valor concreto imutável. Aceita str, int, float ou bool."""

    __slots__ = ("value",)

    def __init__(self, value: str | int | float | bool) -> None:
        object.__setattr__(self, "value", value)

    # Imutabilidade: impede atribuição após criação
    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Atom é imutável")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Atom) and self.value == other.value

    def __hash__(self) -> int:
        return hash(("Atom", self.value))

    def __repr__(self) -> str:
        return f"Atom({self.value!r})"


class Variable:
    """Incógnita identificada por nome string. Igualdade por nome."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "name", name)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Variable é imutável")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Variable) and self.name == other.name

    def __hash__(self) -> int:
        return hash(("Variable", self.name))

    def __repr__(self) -> str:
        return f"Variable({self.name!r})"


class Compound:
    """Functor (string) + lista de argumentos (Term). Representa predicados/fatos."""

    __slots__ = ("functor", "args")

    def __init__(self, functor: str, args: list[Term] | tuple[Term, ...]) -> None:
        object.__setattr__(self, "functor", functor)
        object.__setattr__(self, "args", tuple(args))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Compound é imutável")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Compound)
            and self.functor == other.functor
            and self.args == other.args
        )

    def __hash__(self) -> int:
        return hash(("Compound", self.functor, tuple(self.args)))

    def __repr__(self) -> str:
        return f"Compound({self.functor!r}, {self.args!r})"


Term = Atom | Variable | Compound

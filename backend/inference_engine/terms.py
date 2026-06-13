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

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class Atom:
    """Valor concreto imutável. Igualdade por valor."""

    value: str | int | float | bool

    def __repr__(self) -> str:
        return repr(self.value)


@dataclass(frozen=True)
class Variable:
    """Incógnita identificada por nome. Igualdade por nome."""

    name: str

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Compound:
    """Predicado com functor e lista de argumentos."""

    functor: str
    args: tuple["Term", ...] = field(default_factory=tuple)

    def __init__(self, functor: str, args: list["Term"] | tuple["Term", ...] = ()) -> None:
        object.__setattr__(self, "functor", functor)
        object.__setattr__(self, "args", tuple(args))

    def __repr__(self) -> str:
        if not self.args:
            return self.functor
        args_str = ", ".join(repr(a) for a in self.args)
        return f"{self.functor}({args_str})"


Term = Union[Atom, Variable, Compound]

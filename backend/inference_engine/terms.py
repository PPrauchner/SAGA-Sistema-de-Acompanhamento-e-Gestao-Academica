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

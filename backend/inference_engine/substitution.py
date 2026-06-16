"""
Representação e aplicação de substituições variável→valor no motor de inferência.

Responsabilidades:
- Definir o tipo substituição como dict[str, Term].
- Implementar `def apply(term: Term, subst: dict) -> Term`:
    - Atom → retorna inalterado.
    - Variable(X) em subst → aplica recursivamente apply(subst[X], subst).
    - Variable(X) fora de subst → retorna Variable(X).
    - Compound → retorna Compound(functor, [apply(arg, subst) for arg in args]).
- Módulo isolado: depende apenas de terms.py, sem imports externos.
"""
from inference_engine.terms import Atom, Variable, Compound, Term


def apply(term: Term, subst: dict) -> Term:
    """
    Aplica o ambiente de substituições subst ao termo term.

    Percorre term recursivamente, substituindo cada Variable ligada em subst
    pelo seu valor, e retorna o termo resultante com todas as variáveis
    resolvíveis já instanciadas.

    Cadeias de substituições são resolvidas automaticamente: se subst contém
    {'X': Variable('Y'), 'Y': Atom('a')}, então apply(Variable('X'), subst)
    retorna Atom('a').

    Args:
        term:  O termo a ser instanciado.
        subst: Dicionário de substituições (str → Term) produzido por unify().

    Returns:
        Um novo Term com as variáveis ligadas substituídas. Variáveis sem
        ligação e Atoms são retornados sem modificação.

    Exemplos:
        apply(Variable('X'), {'X': Atom('b')})
        # → Atom('b')

        apply(Compound('f', [Variable('X')]), {'X': Atom('b')})
        # → Compound('f', [Atom('b')])

        apply(Variable('Z'), {'X': Atom('b')})
        # → Variable('Z')   (sem ligação, retorna inalterada)
    """
    if isinstance(term, Atom):
        return term

    if isinstance(term, Variable):
        if term.name in subst:
            return apply(subst[term.name], subst)
        return term

    return Compound(term.functor, [apply(arg, subst) for arg in term.args])

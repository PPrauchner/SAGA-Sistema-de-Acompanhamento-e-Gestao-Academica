"""
Aplicação de substituições variável→termo no motor de inferência lógica.

Uma substituição é um dicionário do tipo dict[str, Term] que mapeia nomes
de variáveis a termos concretos. Após a unificação produzir esse dicionário,
apply() é usada para 'instanciar' um termo — ou seja, substituir todas as
variáveis ligadas pelos seus valores correspondentes.

Função pública:
    apply(term, subst) -> Term

    Percorre term recursivamente e substitui cada Variable pelo valor ligado
    em subst. Variáveis sem ligação permanecem inalteradas. O processo é
    não-destrutivo: nenhum termo original é modificado.

Comportamento por tipo de termo:
    - Atom      → retornado imediatamente sem modificação.
    - Variable(X) em subst   → aplica recursivamente apply(subst[X], subst),
                               resolvendo cadeias de substituições (X→Y, Y→a).
    - Variable(X) fora subst → retorna Variable(X) inalterada.
    - Compound  → retorna um novo Compound com cada argumento aplicado.

Isolamento: depende apenas de terms.py. Sem imports de FastAPI, Firebase ou
qualquer ORM.
"""
from __future__ import annotations

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

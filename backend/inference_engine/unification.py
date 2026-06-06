"""
Algoritmo de unificação entre termos do motor de inferência lógica.

Unificação é o mecanismo central da programação lógica: dado dois termos t1
e t2, a unificação determina se existe um conjunto de ligações
variável→termo (uma 'substituição') que, quando aplicado a ambos, os torna
sintaticamente idênticos.

Função pública:
    unify(t1, t2, subst) -> dict | None

    Recebe dois termos e um ambiente de substituições já existente. Retorna
    um novo dicionário de substituições (extensão de subst) se a unificação
    for possível, ou None em caso de falha. Nunca modifica subst in-place —
    o resultado é sempre um novo dicionário.

Casos tratados (em ordem de avaliação):
    1. Atom == Atom (mesmo valor)  → retorna subst inalterada.
    2. Atom != Atom                → falha (None).
    3. Variable(X) já em subst     → resolve subst[X] e tenta unificar com t2.
    4. Variable(X) nova            → occur check + adiciona X→t2 à subst.
    5. Compound vs Compound        → mesmo functor e aridade, unifica args par a par.
    6. Qualquer outra combinação   → falha (None).

Occur check (caso 4):
    Antes de ligar Variable(X) a um termo t2, verifica se X aparece dentro
    de t2. Se sim, retorna None — isso evita a criação de termos circulares
    infinitos (ex.: X = f(X) seria inválido).

Isolamento: depende apenas de terms.py. Sem imports de FastAPI, Firebase ou
qualquer ORM.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from backend.inference_engine.terms import Atom, Variable, Compound, Term


def _occurs(var: Variable, term: Term) -> bool:
    """
    Verifica se a variável var ocorre em algum lugar dentro de term.

    Usado pelo occur check em unify() para prevenir ligações circulares.
    Percorre term recursivamente: Atom nunca contém variáveis; Variable é
    comparada pelo nome; Compound delega para cada argumento.

    Retorna True se var aparecer em term, False caso contrário.
    """
    if isinstance(term, Atom):
        return False
    if isinstance(term, Variable):
        return var.name == term.name
    return any(_occurs(var, arg) for arg in term.args)


def unify(t1: Term, t2: Term, subst: dict) -> dict | None:
    """
    Tenta unificar os termos t1 e t2 no contexto do ambiente de substituições subst.

    A unificação procura um conjunto mínimo de ligações variável→termo que,
    ao ser aplicado a t1 e t2, torna os dois termos sintaticamente idênticos.

    Args:
        t1:    Primeiro termo a unificar.
        t2:    Segundo termo a unificar.
        subst: Dicionário de substituições já estabelecidas (str → Term).
               Não é modificado in-place — o retorno é sempre um novo dict.

    Returns:
        Um novo dicionário de substituições (extensão de subst) em caso de
        sucesso, ou None se t1 e t2 não puderem ser unificados.

    Exemplos:
        unify(Variable('X'), Atom('a'), {})
        # → {'X': Atom('a')}

        unify(Atom('a'), Atom('b'), {})
        # → None

        unify(Compound('f', [Variable('X')]), Compound('f', [Atom('b')]), {})
        # → {'X': Atom('b')}
    """
    if isinstance(t1, Atom) and isinstance(t2, Atom):
        return subst if t1.value == t2.value else None

    if isinstance(t1, Variable) and t1.name in subst:
        return unify(subst[t1.name], t2, subst)

    if isinstance(t2, Variable) and t2.name in subst:
        return unify(t1, subst[t2.name], subst)

    if isinstance(t1, Variable):
        if _occurs(t1, t2):
            return None
        return {**subst, t1.name: t2}

    if isinstance(t2, Variable):
        if _occurs(t2, t1):
            return None
        return {**subst, t2.name: t1}

    if isinstance(t1, Compound) and isinstance(t2, Compound):
        if t1.functor != t2.functor or len(t1.args) != len(t2.args):
            return None
        current_subst = subst
        for a1, a2 in zip(t1.args, t2.args):
            current_subst = unify(a1, a2, current_subst)
            if current_subst is None:
                return None
        return current_subst

    return None

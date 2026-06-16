"""
Algoritmo de unificação entre termos do motor de inferência.

Responsabilidades:
- Implementar `def unify(t1: Term, t2: Term, subst: dict) -> dict | None`.
- Casos tratados:
    - Atom == Atom com mesmo valor → retorna subst inalterada.
    - Atom != Atom → retorna None.
    - Variable(X) já em subst → unifica subst[X] com t2 recursivamente.
    - Variable(X) não em subst → retorna {**subst, X: t2} com occur check
      (X não pode aparecer em t2).
    - Compound vs Compound → mesmo functor e aridade; unifica argumentos par a par.
    - Qualquer outra combinação → retorna None.
- Módulo isolado: depende apenas de terms.py, sem imports externos.
"""
from inference_engine.terms import Atom, Variable, Compound, Term


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

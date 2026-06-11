# Template de Relatório de PR

Salvar em: `docs/relatorios/[BRANCH]/Sprint_[SPRINT]/Relatorio_PR_[N]_[ITERAÇÃO].md`

---

```markdown
# Relatório de Revisão — PR #[N] vs Issue #[M]

## Contexto

**Branch:** [headRefName]
**PR:** #[N] — "[título do PR]"
**Autor:** [nome do autor]
**Data:** [data atual]
**Issue de referência:** [#M] [título completo da issue]
**Specs:** [lista dos specs consultados]

---

## Resumo Executivo

[2-3 frases resumindo o que foi entregue e o veredito geral. Seja direto.]

---

## Incongruências por Severidade

### CRÍTICO — Bloqueadores da Definition of Done

#### C[N]. [Título curto e descritivo]

[Descrição precisa do problema, com referência a arquivos/linhas/spec quando possível.]

**Impacto:** [consequência prática]

---

### MODERADO — Desvios de Requisito ou Spec

#### M[N]. [Título]

[Descrição do desvio com citação direta da spec ou da issue quando relevante.]

---

### MENOR — Qualidade e Convenções

#### m[N]. [Título]

[Descrição do problema menor.]

---

## Matriz de Status por Arquivo

| Arquivo | Esperado pela Issue #[M] | Entregue | Status |
|---------|--------------------------|----------|--------|
| `path/arquivo.py` | [esperado] | [entregue] | OK / Parcial / **Bloqueador** |

---

## Ações Necessárias

1. **[Bloqueador]** [Ação específica e acionável]
2. **[Moderado]** [Ação específica e acionável]
3. **[Menor]** [Ação específica e acionável]
```

> Se não houver incongruências em alguma categoria, omita a seção inteira.

# Template de Relatório de Issue

Salvar em: `docs/Relatórios/Issues/Relatório_Issue_[NUMBER].md`

---

```markdown
# Relatório de Issue #[N] — [Título da Issue]

## Contexto

**Issue:** #[N] — [título completo]
**Sprint:** [sprint extraída do título]
**Responsável(is):** [assignees]
**Estado:** [OPEN / CLOSED]
**Data do relatório:** [data atual]
**Specs consultados:** [lista]
**URL:** [link da issue]

---

## O que foi solicitado

[Resumo do corpo da issue em prosa.]

**Definition of Done:**
- [ ] Critério 1
- [ ] Critério 2

---

## O que foi entregue

### PRs relacionados

| PR | Título | Estado | Branch | Autor |
|----|--------|--------|--------|-------|
| #N | título | MERGED/OPEN | branch | autor |

### Commits relacionados

| Hash | Mensagem |
|------|----------|
| `abc1234` | mensagem do commit |

### Resumo da implementação

[Descrição em prosa do que foi efetivamente implementado.]

---

## Conformidade com os Specs

| Requisito do Spec | Implementado? | Observação |
|-------------------|--------------|------------|
| [requisito] | ✅ Sim / ❌ Não / ⚠️ Parcial | [detalhe] |

---

## Gaps e Pendências

[Itens da DoD não cumpridos ou desvios dos specs. Use severidade CRÍTICO / MODERADO / MENOR.]

---

## Status Geral

**[✅ Completa / 🔄 Em progresso / ❌ Bloqueada / ⏳ Não iniciada]**

[1-2 frases de conclusão direta.]
```

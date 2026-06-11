---
name: review-pr
description: Revisa um Pull Request contra a issue e os specs relevantes, gera relatório estruturado e executa a ação escolhida (aprovar, reprovar, comentar). Use when reviewing a pull request. $ARGUMENTS
---

# Review PR

Revisa o PR `#$ARGUMENTS`.

## Workflow

### 1. Buscar dados do PR
```bash
gh pr view $ARGUMENTS --json number,title,body,headRefName,baseRefName,state,author,additions,deletions,files,commits,labels,url
```
Anote: número do PR, branch de origem, estado (OPEN/MERGED), issues referenciadas no corpo (`Closes #N`, `Fixes #N`, `Part of #N`).

### 2. Buscar dados de cada issue referenciada
```bash
gh issue view N --json number,title,body,labels,assignees,milestone
```
Extraia o número da sprint do título: `[Sprint N]` → formatar com dois dígitos (`01`, `02`...).

### 3. Ler o modelo de dados e identificar specs relevantes

**Sempre** leia o modelo de dados canônico:
```
Read docs/data-model.md
```

Use-o como referência cruzada ao analisar o diff:
- Verificar se campos, nomes de coleções e enums no código coincidem com o modelo (ex: `tipo_producao`, não `tipo`; `creditos_concedidos` é override da coordenação, `creditos_gerados` é o calc — não confundir)
- Sinalizar como **MODERADO** qualquer desvio de nome ou tipo em relação ao modelo
- Verificar invariantes: ex., toda `activities.producao_id` deve ter uma `productions` correspondente; `advisors` existe ⟺ usuário pode orientar

Em seguida, use a tabela do `CLAUDE.md` e o [mapa de specs](./specs-map.md). Leia cada spec identificado. Onde `data-model.md` e `03_firebase_schema.json` divergirem, o `data-model.md` vence.

### 4. Obter o diff
```bash
gh pr diff $ARGUMENTS
gh pr view $ARGUMENTS --json files --jq '.files[].path'
```
Leia arquivos alterados com Read quando necessário.

### 5. Analisar: o que deveria ter sido feito vs o que foi feito
Compare issue + specs + data-model + diff. Categorize incongruências:
- **CRÍTICO** — bloqueadores: DoD não cumprida, falha de import, testes não passando
- **MODERADO** — desvios de requisito, spec ou data-model (campo com nome errado, tipo incorreto, invariante violada)
- **MENOR** — qualidade e convenções

### 6. Determinar caminho do relatório
`docs/relatorios/[BRANCH]/Sprint_[SPRINT]/Relatorio_PR_[N]_[ITERAÇÃO].md`

```bash
ls docs/relatorios/[BRANCH]/Sprint_[SPRINT]/ 2>/dev/null || echo "(pasta ainda não existe)"
```
Conte os arquivos `Relatorio_PR_[N]_*.md` existentes + 1 = iteração.

### 7. Gerar e salvar o relatório
Siga o [template de relatório](./report-template.md). Use como referência visual qualquer relatório existente em `docs/relatorios/`.

```bash
mkdir -p docs/relatorios/[BRANCH]/Sprint_[SPRINT]
# Write tool: docs/relatorios/[BRANCH]/Sprint_[SPRINT]/Relatorio_PR_[N]_[ITERAÇÃO].md
```

### 8. Apresentar e perguntar a ação
Exiba o relatório e, se o PR estiver OPEN, pergunte:
1. **Aprovar** — `gh pr review --approve` + move issue para Done
2. **Reprovar** — `gh pr review --request-changes` + move issue para Backlog
3. **Apenas comentar** — posta resumo + move issue para In Progress
4. **Nada** — só salvar o relatório localmente

### 9. Executar a ação escolhida
```bash
# Aprovar
gh pr review $ARGUMENTS --approve --body "[resumo]"
bash .claude/hooks/move-issue.sh [ISSUE_NUMBER] "done"

# Reprovar
gh pr review $ARGUMENTS --request-changes --body "[bloqueadores]"
bash .claude/hooks/move-issue.sh [ISSUE_NUMBER] "backlog"

# Comentar
gh pr comment $ARGUMENTS --body "[comentário]"
bash .claude/hooks/move-issue.sh [ISSUE_NUMBER] "in progress"
```

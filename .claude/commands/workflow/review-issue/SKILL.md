---
name: review-issue
description: Analisa o estado de uma issue do GitHub — o que foi pedido vs. o que foi entregue — e gera relatório de conformidade com os specs. Use when reviewing or auditing an issue. $ARGUMENTS
---

# Review Issue

Analisa a issue `#$ARGUMENTS`.

## Workflow

### 1. Buscar dados da issue
```bash
gh issue view $ARGUMENTS --json number,title,body,labels,assignees,state,milestone,comments,createdAt,updatedAt,url
```
Extraia: número, título, sprint (`[Sprint N]` → dois dígitos), assignees, estado, Definition of Done (se houver).

### 2. Identificar specs relevantes
Use o [mapa de specs](./specs-map.md) e a tabela do `CLAUDE.md`. Leia cada spec identificado.

### 3. Buscar PRs relacionados
```bash
gh pr list --state all --search "#$ARGUMENTS" --json number,title,state,headRefName,mergedAt,author,url
gh pr list --state all --search "closes $ARGUMENTS OR fixes $ARGUMENTS" --json number,title,state,headRefName,mergedAt,author,url
```

### 4. Buscar commits relacionados
```bash
git log --all --oneline --grep="#$ARGUMENTS"
```
Se sem resultado, tente palavras-chave do título.

### 5. Ler arquivos implementados
Com base nos PRs e commits, leia os arquivos principais com Read.

### 6. Analisar: o que foi pedido vs o que foi feito
Compare: requisitos da issue + specs + código entregue. Classifique o status:
- ✅ **Completa** — tudo entregue e conforme spec
- 🔄 **Em progresso** — parcialmente entregue
- ❌ **Bloqueada** — há impedimento técnico ou de dependência
- ⏳ **Não iniciada** — nenhum commit ou PR encontrado

### 7. Gerar e salvar o relatório
Siga o [template de relatório](./report-template.md).

```bash
mkdir -p docs/Relatórios/Issues
# Write tool: docs/Relatórios/Issues/Relatório_Issue_[NUMBER].md
```

### 8. Apresentar resultado
Exiba o relatório no chat e informe o caminho. Pergunte se deseja enviar por e-mail via `/send-email`.

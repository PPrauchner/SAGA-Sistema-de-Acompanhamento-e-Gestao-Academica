---
name: commit
description: Analisa mudanças não-commitadas e realiza commits atômicos seguindo as convenções do projeto. Use when the user wants to commit changes, stage files, or create a structured commit message. $ARGUMENTS
---

# Commit

## Workflow

### 1. Diagnosticar
```bash
git status
git diff --stat HEAD
```
Se a working tree estiver limpa, informe o usuário e pare.

### 2. Ler convenções
- `guidelines/CommitConventions.md` — tipos, escopos, template
- `CLAUDE.md` seção "Commits atômicos durante o trabalho" — regras de atomicidade
- `.gitmessage` — template exato do git

### 3. Identificar issue ativa
```bash
cat .claude/current-issue 2>/dev/null || echo "(nenhuma)"
gh issue view $(cat .claude/current-issue) --json number,title,body,labels 2>/dev/null
```

### 4. Inspecionar mudanças
```bash
git diff          # não-staged
git diff --cached # staged
git ls-files --others --exclude-standard  # untracked
```
Leia arquivos novos relevantes com Read para entender o que fazem.

### 5. Agrupar em commits atômicos
Aplique as [regras de atomicidade](./atomicity-rules.md). Regra de ouro: se precisar de mais de uma frase para descrever **o que** foi feito (não o porquê), divida o commit.

### 6. Propor plano — aguardar confirmação
```
Plano de commits (N commits):

1. tipo(escopo): descrição curta
   Arquivos: path/arquivo1.py, path/arquivo2.py
   Corpo: [porquê da mudança, se necessário]
```
Se houver issue ativa, o último commit relevante deve referenciar no rodapé (`Closes #N` ou `Part of #N`). **Aguardar confirmação antes de executar.**

### 7. Executar após confirmação
```bash
git add caminho/arquivo1 caminho/arquivo2
git commit -m "tipo(escopo): descrição

Corpo opcional (wrap a 72 chars).

Closes #N"
git log --oneline -1  # confirmar cada commit
```

### 8. Resumo final
```bash
git log --oneline -N
```
Perguntar se deseja fazer push.

---
name: finish-issue
description: Finaliza uma issue/sub-issue — roda /code-review no diff e, se válido, gera as mensagens de commit atômicas por camada. Use when an issue or sub-issue implementation is done and ready to review + commit. $ARGUMENTS
---

# Finish Issue

Fecha o ciclo de implementação de uma issue ou sub-issue: **revisar → se válido, gerar as mensagens de commit**.

> Por padrão este comando **gera** as mensagens de commit, mas **não executa** os commits. Gerar a mensagem ≠ commitar: só commitar quando o usuário pedir (delega ao `/workflow:commit`).

## Workflow

### 1. Identificar a issue ativa
```bash
cat .claude/current-issue 2>/dev/null || echo "(nenhuma)"
gh issue view $(cat .claude/current-issue) --json number,title,body 2>/dev/null
```
Use o número da sub-issue ativa (`current-issue`). Para o rodapé do commit, lembre que `root-issue` é a issue pai.

### 2. Diagnosticar o diff
```bash
git status
git diff --stat HEAD
```
Se a working tree estiver limpa, informe o usuário e pare — não há o que revisar nem commitar.

### 3. Rodar o code-review
Invoque a skill `code-review` sobre o diff atual. Relate os achados.

**Critério de validade:** prosseguir para gerar as mensagens **somente** se não houver achados de correção (bugs) bloqueantes. Achados de simplificação/altitude/convenção de baixa severidade não bloqueiam, mas devem ser mencionados.

Se houver achado bloqueante:
- Apresente o achado e **pare** antes de gerar mensagens de commit.
- Corrija (ou proponha correção) e rode o code-review de novo antes de seguir.

### 4. Rodar os testes da camada tocada
Se o diff tocou `backend/`, rode os testes relevantes e confirme que passam antes de gerar mensagens (ex.: `pytest backend/app/services/tests/ -q`). Após mudanças em `backend/inference_engine/`, rode `pytest backend/inference_engine/tests/ -v`. Não gere mensagens com testes falhando.

### 5. Gerar as mensagens de commit
Leia `guidelines/CommitConventions.md` e agrupe o diff em commits atômicos seguindo as regras:
- Um commit por camada: `model → repository → service → router`.
- Testes **sempre** em commit separado (`feat`/`fix` primeiro, `test` depois).
- Cada commit compila e faz sentido isoladamente.
- Rodapé referencia a issue: `Refs #N` nos commits intermediários, `Closes #N` no último que completa a (sub-)issue.
- Toda mensagem termina com `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

Apresente as mensagens prontas (uma por bloco, com os arquivos de cada commit), na ordem de execução.

### 6. Aguardar o usuário
Não execute os commits. Ao final, ofereça executar via `/workflow:commit` quando o usuário confirmar.

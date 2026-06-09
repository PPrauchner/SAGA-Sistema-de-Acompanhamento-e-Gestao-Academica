#!/bin/bash
# Hook: create-subtasks.sh
# Cria sub-issues no GitHub a partir de .claude/subtasks-pending.json,
# herdando assignees e labels da issue pai. Adiciona cada sub-issue ao
# GitHub Projects V2 (#4) e atualiza o corpo da issue pai com um checklist.
#
# Uso: bash .claude/hooks/create-subtasks.sh <PARENT_ISSUE_NUMBER>

set -e

PARENT_ISSUE="$1"
OWNER="PPrauchner"
PROJECT_NUMBER=4
ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
SUBTASKS_FILE="$ROOT/.claude/subtasks-pending.json"

# ── Validações ────────────────────────────────────────────────────────────────

if [ -z "$PARENT_ISSUE" ]; then
    echo "[create-subtasks] Erro: número da issue pai não fornecido."
    exit 1
fi

if [ ! -f "$SUBTASKS_FILE" ]; then
    echo "[create-subtasks] Erro: $SUBTASKS_FILE não encontrado."
    echo "[create-subtasks] Crie o arquivo antes de chamar este script."
    exit 1
fi

SUBTASK_COUNT=$(python3 -c "import json; d=json.load(open('$SUBTASKS_FILE')); print(len(d))")
if [ "$SUBTASK_COUNT" -eq 0 ]; then
    echo "[create-subtasks] Nenhuma sub-tarefa encontrada em subtasks-pending.json."
    exit 0
fi

echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│  Criando $SUBTASK_COUNT sub-issues para issue #$PARENT_ISSUE"
echo "└─────────────────────────────────────────────────┘"

# ── Buscar metadata da issue pai ─────────────────────────────────────────────

echo "[create-subtasks] Buscando metadata da issue pai #$PARENT_ISSUE..."

PARENT_DATA=$(gh issue view "$PARENT_ISSUE" \
    --repo "$OWNER/$(git remote get-url origin | sed -E 's|.*[/:]([^/]+/[^/.]+)(\.git)?$|\1|' | cut -d'/' -f2)" \
    --json assignees,labels,body,title)

REPO_NAME=$(git remote get-url origin | sed -E 's|.*[/:]([^/]+/[^/.]+)(\.git)?$|\1|' | cut -d'/' -f2)

# Extrair assignees (lista separada por vírgula)
ASSIGNEES=$(echo "$PARENT_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
logins = [a['login'] for a in d.get('assignees', [])]
print(','.join(logins))
")

# Extrair labels (lista separada por vírgula)
LABELS=$(echo "$PARENT_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = [l['name'] for l in d.get('labels', [])]
print(','.join(names))
")

PARENT_BODY=$(echo "$PARENT_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('body', ''))
")

echo "[create-subtasks] Assignees: ${ASSIGNEES:-nenhum}"
echo "[create-subtasks] Labels: ${LABELS:-nenhum}"

# ── Criar cada sub-issue ──────────────────────────────────────────────────────

CREATED_ISSUES=""  # acumula "NUMERO|TITULO" separados por newline

TOTAL=$(python3 -c "import json; print(len(json.load(open('$SUBTASKS_FILE'))))")

for i in $(seq 0 $(($TOTAL - 1))); do
    TITLE=$(python3 -c "import json; d=json.load(open('$SUBTASKS_FILE')); print(d[$i]['title'])")
    BODY=$(python3 -c "import json; d=json.load(open('$SUBTASKS_FILE')); print(d[$i]['body'])")

    echo ""
    echo "[create-subtasks] ($((i+1))/$TOTAL) Criando: $TITLE"

    # Montar argumentos opcionais
    EXTRA_ARGS=()
    [ -n "$ASSIGNEES" ] && EXTRA_ARGS+=(--assignee "$ASSIGNEES")
    [ -n "$LABELS" ]    && EXTRA_ARGS+=(--label "$LABELS")

    # Criar a issue
    NEW_URL=$(gh issue create \
        --repo "$OWNER/$REPO_NAME" \
        --title "$TITLE" \
        --body "$BODY" \
        "${EXTRA_ARGS[@]}" 2>/dev/null)

    NEW_NUMBER=$(echo "$NEW_URL" | grep -oE '[0-9]+$')

    if [ -z "$NEW_NUMBER" ]; then
        echo "[create-subtasks] ✗ Falha ao criar sub-issue: $TITLE"
        continue
    fi

    echo "[create-subtasks] ✓ Issue #$NEW_NUMBER criada: $NEW_URL"

    # Adicionar ao projeto
    echo "[create-subtasks]   Adicionando ao projeto #$PROJECT_NUMBER..."
    gh project item-add "$PROJECT_NUMBER" \
        --owner "$OWNER" \
        --url "$NEW_URL" > /dev/null 2>&1 \
        && echo "[create-subtasks]   ✓ Adicionada ao projeto." \
        || echo "[create-subtasks]   ⚠ Não foi possível adicionar ao projeto (verifique permissões)."

    CREATED_ISSUES="$CREATED_ISSUES
$NEW_NUMBER|$TITLE"
done

# ── Atualizar corpo da issue pai com checklist ────────────────────────────────

echo ""
echo "[create-subtasks] Atualizando issue pai #$PARENT_ISSUE com checklist..."

CHECKLIST="## Sub-tarefas"$'\n'
while IFS='|' read -r NUM TITLE; do
    [ -z "$NUM" ] && continue
    CHECKLIST="$CHECKLIST- [ ] #$NUM — $TITLE"$'\n'
done <<< "$CREATED_ISSUES"

# Verificar se já existe um bloco de sub-tarefas no corpo
if echo "$PARENT_BODY" | grep -q "## Sub-tarefas"; then
    NEW_BODY=$(echo "$PARENT_BODY" | python3 -c "
import sys, re
body = sys.stdin.read()
checklist = '''$CHECKLIST'''
new_body = re.sub(r'## Sub-tarefas[\s\S]*?(?=\n##\s|\Z)', checklist.strip(), body)
print(new_body)
")
else
    NEW_BODY="$PARENT_BODY"$'\n\n'"$CHECKLIST"
fi

gh issue edit "$PARENT_ISSUE" \
    --repo "$OWNER/$REPO_NAME" \
    --body "$NEW_BODY" > /dev/null \
    && echo "[create-subtasks] ✓ Checklist adicionado à issue #$PARENT_ISSUE." \
    || echo "[create-subtasks] ⚠ Não foi possível atualizar o corpo da issue pai."

# ── Limpeza ───────────────────────────────────────────────────────────────────

rm -f "$SUBTASKS_FILE"
echo ""
echo "[create-subtasks] ✓ Concluído. subtasks-pending.json removido."

# Mostrar resumo
echo ""
echo "┌─────────────────────────────────────────────────┐"
echo "│  Sub-issues criadas:"
while IFS='|' read -r NUM TITLE; do
    [ -z "$NUM" ] && continue
    printf "│  #%-5s %s\n" "$NUM" "$TITLE"
done <<< "$CREATED_ISSUES"
echo "└─────────────────────────────────────────────────┘"
echo ""

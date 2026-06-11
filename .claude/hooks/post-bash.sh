#!/bin/bash
# Hook: PostToolUse (Bash)
# Detecta quando um PR foi criado e aciona a movimentação no GitHub Projects.

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null)

# Só age se o comando foi um gh pr create
if echo "$COMMAND" | grep -q "gh pr create"; then
    ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)"

    # Adiciona lorenzoficher como reviewer
    echo "[hook] Adicionando @lorenzoficher como reviewer..."
    gh pr edit --add-reviewer lorenzoficher 2>&1 \
        && echo "[hook] Reviewer adicionado." \
        || echo "[hook] Aviso: não foi possível adicionar o reviewer (PR pode ser de fork ou permissão insuficiente)."

    ISSUE_FILE="$ROOT/.claude/current-issue"

    if [ -f "$ISSUE_FILE" ]; then
        ISSUE_NUMBER=$(cat "$ISSUE_FILE" | tr -d '[:space:]')
        if [ -n "$ISSUE_NUMBER" ]; then
            echo "[hook] PR criado — movendo issue #$ISSUE_NUMBER para 'In Review'..."
            bash "$ROOT/.claude/hooks/move-to-in-review.sh" "$ISSUE_NUMBER" "$ROOT"
        fi
    else
        echo "[hook] Aviso: .claude/current-issue não encontrado. Issue não será movida automaticamente."
    fi
fi

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

    # Usa root-issue (issue pai) se existir; caso contrário, cai em current-issue.
    # root-issue é escrito ao iniciar uma issue pai e nunca sobrescrito por sub-issues.
    ROOT_FILE="$ROOT/.claude/root-issue"
    CURRENT_FILE="$ROOT/.claude/current-issue"

    if [ -f "$ROOT_FILE" ]; then
        ISSUE_NUMBER=$(cat "$ROOT_FILE" | tr -d '[:space:]')
        echo "[hook] PR criado — movendo issue pai #$ISSUE_NUMBER para 'In Review'..."
    elif [ -f "$CURRENT_FILE" ]; then
        ISSUE_NUMBER=$(cat "$CURRENT_FILE" | tr -d '[:space:]')
        echo "[hook] PR criado — movendo issue #$ISSUE_NUMBER para 'In Review'..."
    fi

    if [ -n "$ISSUE_NUMBER" ]; then
        bash "$ROOT/.claude/hooks/move-to-in-review.sh" "$ISSUE_NUMBER" "$ROOT"
    else
        echo "[hook] Aviso: .claude/root-issue e .claude/current-issue não encontrados. Issue não será movida automaticamente."
    fi
fi

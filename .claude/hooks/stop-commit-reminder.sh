#!/bin/bash
# Hook: Stop
# Verifica se há mudanças não commitadas ao encerrar a sessão.
# Se houver, avisa o usuário com um resumo do que está pendente.

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)

if [ -z "$ROOT" ]; then
    exit 0
fi

cd "$ROOT"

STAGED=$(git diff --cached --name-only 2>/dev/null)
UNSTAGED=$(git diff --name-only 2>/dev/null)
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)

HAS_CHANGES=false
[ -n "$STAGED" ]    && HAS_CHANGES=true
[ -n "$UNSTAGED" ]  && HAS_CHANGES=true
[ -n "$UNTRACKED" ] && HAS_CHANGES=true

if [ "$HAS_CHANGES" = true ]; then
    echo ""
    echo "┌─────────────────────────────────────────────┐"
    echo "│  ⚠️  Mudanças não commitadas nesta sessão   │"
    echo "└─────────────────────────────────────────────┘"

    if [ -n "$STAGED" ]; then
        echo ""
        echo "📦 Staged (prontos para commit):"
        echo "$STAGED" | sed 's/^/   /'
    fi

    if [ -n "$UNSTAGED" ]; then
        echo ""
        echo "✏️  Modificados (não staged):"
        echo "$UNSTAGED" | sed 's/^/   /'
    fi

    if [ -n "$UNTRACKED" ]; then
        echo ""
        echo "🆕 Novos arquivos (untracked):"
        echo "$UNTRACKED" | sed 's/^/   /'
    fi

    ISSUE_FILE="$ROOT/.claude/current-issue"
    ISSUE=""
    if [ -f "$ISSUE_FILE" ]; then
        ISSUE=$(cat "$ISSUE_FILE" | tr -d '[:space:]')
        echo ""
        echo "📌 Issue ativa: #$ISSUE"
    fi

    echo ""
    echo "💡 Considere commitar antes de encerrar:"
    if [ -n "$ISSUE" ]; then
        echo "   git add -A && git commit -m \"tipo: descrição (#$ISSUE)\""
    else
        echo "   git add -A && git commit -m \"tipo: descrição\""
    fi
    echo ""
fi

exit 0

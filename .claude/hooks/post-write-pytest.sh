#!/bin/bash
# Hook: PostToolUse (Write + Edit)
# Roda pytest do inference_engine automaticamente quando arquivos dentro
# de backend/inference_engine/ são criados ou modificados.

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Suporta Write (file_path) e Edit (file_path)
    inp = d.get('tool_input', {})
    print(inp.get('file_path', inp.get('path', '')))
except:
    print('')
" 2>/dev/null)

# Só age se o arquivo modificado está dentro do inference_engine
if echo "$FILE_PATH" | grep -q "inference_engine"; then
    ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[hook] Arquivo do inference_engine modificado."
    echo "[hook] Rodando pytest automaticamente..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    cd "$ROOT"

    # Ativa o venv se existir
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    fi

    pytest backend/inference_engine/tests/ -v --tb=short 2>&1
    EXIT_CODE=$?

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[hook] ✓ Todos os testes passando."
    else
        echo "[hook] ✗ Testes falhando — corrija antes de continuar."
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Não propaga falha — apenas avisa
    exit 0
fi

exit 0

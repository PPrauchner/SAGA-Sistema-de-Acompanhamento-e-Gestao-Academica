#!/bin/bash
# Hook: move-to-in-review.sh
# Move uma issue para "In Review" no GitHub Projects V2.
# Wrapper do move-issue.sh para manter compatibilidade com post-bash.sh.
#
# Uso: bash move-to-in-review.sh <ISSUE_NUMBER> [REPO_ROOT]

ISSUE_NUMBER="$1"
ROOT="${2:-.}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

bash "$SCRIPT_DIR/move-issue.sh" "$ISSUE_NUMBER" "in review" "$ROOT"

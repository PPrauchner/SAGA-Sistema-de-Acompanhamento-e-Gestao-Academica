#!/bin/bash
# Hook: move-issue.sh
# Move uma issue para qualquer coluna do GitHub Projects V2 via GraphQL.
# Faz match por substring case-insensitive no nome da opção de Status.
#
# Uso: bash move-issue.sh <ISSUE_NUMBER> <STATUS_SUBSTRING> [REPO_ROOT]
# Exemplos:
#   bash move-issue.sh 42 "done"
#   bash move-issue.sh 42 "backlog"
#   bash move-issue.sh 42 "in progress" /path/to/repo

set -e

ISSUE_NUMBER="$1"
STATUS_QUERY="$2"
ROOT="${3:-.}"
OWNER="PPrauchner"
PROJECT_NUMBER=4

if [ -z "$ISSUE_NUMBER" ] || [ -z "$STATUS_QUERY" ]; then
    echo "[move-issue] Uso: bash move-issue.sh <ISSUE_NUMBER> <STATUS_SUBSTRING> [ROOT]"
    exit 1
fi

REPO_URL=$(git -C "$ROOT" remote get-url origin 2>/dev/null)
REPO_NAME=$(echo "$REPO_URL" | sed -E 's|.*[/:]([^/]+/[^/.]+)(\.git)?$|\1|' | cut -d'/' -f2)

if [ -z "$REPO_NAME" ]; then
    echo "[move-issue] Erro: não foi possível detectar o nome do repositório."
    exit 1
fi

echo "[move-issue] Buscando dados do projeto #$PROJECT_NUMBER..."

PROJECT_DATA=$(gh api graphql -f query='
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      id
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
            }
          }
        }
      }
    }
  }
}' -f login="$OWNER" -F number="$PROJECT_NUMBER")

FIELD_INFO=$(echo "$PROJECT_DATA" | python3 -c "
import sys, json

query = '''$STATUS_QUERY'''.lower()
d = json.load(sys.stdin)
project = d['data']['user']['projectV2']
project_id = project['id']
fields = project['fields']['nodes']

field_id = None
option_id = None
matched_name = None

for field in fields:
    if field.get('name', '').lower() == 'status':
        for opt in field.get('options', []):
            if query in opt['name'].lower():
                field_id = field['id']
                option_id = opt['id']
                matched_name = opt['name']
                break
    if field_id:
        break

if field_id and option_id:
    print(f'{project_id}|{field_id}|{option_id}|{matched_name}')
else:
    for field in fields:
        if field.get('name', '').lower() == 'status':
            opts = [o['name'] for o in field.get('options', [])]
            print(f'OPCOES_DISPONIVEIS: {opts}', file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ]; then
    echo "[move-issue] Erro: nenhuma opção de Status contendo '$STATUS_QUERY' encontrada no projeto."
    echo "[move-issue] Verifique o nome da coluna no quadro Kanban."
    exit 1
fi

PROJECT_ID=$(echo "$FIELD_INFO" | cut -d'|' -f1)
FIELD_ID=$(echo "$FIELD_INFO"   | cut -d'|' -f2)
OPTION_ID=$(echo "$FIELD_INFO"  | cut -d'|' -f3)
MATCHED=$(echo "$FIELD_INFO"    | cut -d'|' -f4)

echo "[move-issue] Coluna encontrada: '$MATCHED'"
echo "[move-issue] Buscando item da issue #$ISSUE_NUMBER no projeto..."

ITEM_DATA=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $issue: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $issue) {
      title
      projectItems(first: 10) {
        nodes {
          id
          project {
            ... on ProjectV2 {
              number
            }
          }
        }
      }
    }
  }
}' -f owner="$OWNER" -f repo="$REPO_NAME" -F issue="$ISSUE_NUMBER")

ITEM_ID=$(echo "$ITEM_DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
issue = d['data']['repository']['issue']
if not issue:
    sys.exit(0)
for item in issue['projectItems']['nodes']:
    if item['project'].get('number') == $PROJECT_NUMBER:
        print(item['id'])
        break
")

if [ -z "$ITEM_ID" ]; then
    echo "[move-issue] Aviso: issue #$ISSUE_NUMBER não está vinculada ao projeto #$PROJECT_NUMBER."
    exit 0
fi

echo "[move-issue] Movendo issue #$ISSUE_NUMBER para '$MATCHED'..."

gh api graphql -f query='
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $project
    itemId:    $item
    fieldId:   $field
    value:     { singleSelectOptionId: $option }
  }) {
    projectV2Item { id }
  }
}' -f project="$PROJECT_ID" \
   -f item="$ITEM_ID" \
   -f field="$FIELD_ID" \
   -f option="$OPTION_ID" > /dev/null

echo "[move-issue] ✓ Issue #$ISSUE_NUMBER movida para '$MATCHED' no projeto #$PROJECT_NUMBER."

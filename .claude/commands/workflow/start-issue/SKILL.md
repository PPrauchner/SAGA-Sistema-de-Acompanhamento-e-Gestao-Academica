---
name: start-issue
description: Inicia o trabalho em uma issue do GitHub. Lê a issue, identifica specs relevantes, avalia complexidade e cria sub-tarefas se necessário. Use when starting work on an issue. $ARGUMENTS
---

# Start Issue

Inicia o trabalho na issue `#$ARGUMENTS`.

## Workflow

### 1. Registrar issue ativa
```bash
echo "$ARGUMENTS" > .claude/current-issue
echo "$ARGUMENTS" > .claude/root-issue
```

`root-issue` sempre armazena a issue pai (raiz da sessão de trabalho). Nunca sobrescreva `root-issue` ao trocar para uma sub-issue — apenas `current-issue` deve ser atualizado.

### 2. Ler a issue
```bash
gh issue view $ARGUMENTS --json number,title,body,labels,assignees
```

### 3. Ler o modelo de dados e identificar specs correspondentes

**Sempre** leia o modelo de dados canônico:
```
Read docs/data-model.md
```

Use-o para:
- Identificar quais coleções e sub-coleções serão tocadas pela issue
- Confirmar nomes exatos de campos, enums e tipos antes de implementar (ex: `situacao_registrada`, não `status`; `orientador_id` aponta para `advisors` auto-id, não para `uid`)
- Verificar quais entidades estão ✅ implementadas vs. 🔲 planejadas — issues em entidades planejadas exigem criação do modelo completo

Em seguida, identifique os specs relevantes em `docs/specs/` usando a tabela do `CLAUDE.md`. Leia cada spec relevante com Read antes de qualquer implementação. Onde `data-model.md` e `03_firebase_schema.json` divergirem, o `data-model.md` vence (é a fonte mais atualizada).

### 4. Ler arquivos de código relevantes
Leia os arquivos diretamente relacionados à issue para entender o que já existe.

### 5. Avaliar complexidade
Consulte o [guia de complexidade](./complexity-guide.md) para decidir se a issue deve ser quebrada.

**Se SIMPLES** — apresente: resumo do que será feito + arquivos a modificar. Aguardar confirmação.

**Se COMPLEXA** — apresente: avaliação de complexidade + lista de sub-tarefas propostas (título, escopo, spec de referência, dependências). Aguardar confirmação e ajustes.

Após confirmação de issue complexa, escreva `.claude/subtasks-pending.json`:
```json
[
  {
    "title": "Título curto",
    "body": "Escopo detalhado. Referência: docs/specs/XX_nome.json, seção Y.\n\nParte da issue #$ARGUMENTS."
  }
]
```
Depois execute:
```bash
bash .claude/hooks/create-subtasks.sh $ARGUMENTS
```

### 6. Iniciar implementação
Comece pela primeira sub-tarefa (ou pela issue diretamente, se simples).

Ao trocar para uma sub-issue, atualize **apenas** `current-issue` — `root-issue` permanece com o número da issue pai:
```bash
echo "NUMERO_DA_SUBISSUE" > .claude/current-issue
# NÃO altere .claude/root-issue
```

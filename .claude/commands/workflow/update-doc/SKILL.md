---
name: update-doc
description: Adiciona um relatório ao Google Doc acumulativo do projeto. Use when the user wants to publish or upload a report to the shared Google Doc. Format: <caminho-do-arquivo> [título da seção]. $ARGUMENTS
---

# Update Doc

Adiciona um relatório ao Google Doc do projeto. Formato: `<caminho-do-arquivo> [título da seção]`

**Integrantes reconhecidos:** GD (@bielGD23), Pietro (@PPrauchner), Lorenzo (@lorenzoficher), Rafael (@rjnlopes03), Inaurrara (@inaurrara)

## Workflow

### 1. Parsear argumentos
- **Arquivo** — primeiro token de `$ARGUMENTS`
- **Título** — tudo que vier depois (opcional; usa o nome do arquivo se omitido)

Se o arquivo não for informado, mostre o formato correto e pare.

### 2. Ler e exibir prévia
Leia o arquivo com Read. Detecte o número de iteração pelo nome (`Relatorio_PR_N_I.md` → `I`).

Exiba ao usuário:
```
Prévia
📂 Seção: [membro] > [sprint] OU Issues
📄 PR: #[N] | Iteração: [I] | Modo: [Nova entrada / Nova iteração]
📅 Data: [hoje]

[primeiras 10 linhas do conteúdo]
[...]
```
**Aguardar confirmação antes de continuar.**

### 3. Verificar se o template foi inicializado
```bash
cd $(git rev-parse --show-toplevel)
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from update_gdoc import authenticate, get_doc_id, parse_doc_structure
from googleapiclient.discovery import build
doc_id = get_doc_id()
creds = authenticate()
service = build('docs', 'v1', credentials=creds)
doc = service.documents().get(documentId=doc_id).execute()
content = doc.get('body', {}).get('content', [])
els = parse_doc_structure(content)
h1s = [e['text'] for e in els if e['style'] == 'HEADING_1']
print('H1s:', h1s)
" 2>/dev/null
```
Se não contiver os nomes dos integrantes, inicialize:
```bash
python3 scripts/init_gdoc_template.py
```

### 4. Verificar dependências Python
```bash
cd $(git rev-parse --show-toplevel)
python3 -c "import googleapiclient, google_auth_oauthlib" 2>/dev/null \
  || pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib --break-system-packages -q
```

### 5. Executar após confirmação
```bash
cd $(git rev-parse --show-toplevel)
python3 scripts/update_gdoc.py "[ARQUIVO]" --title "[TÍTULO]"
```
Se for a primeira execução, avise que o navegador vai abrir para autorizar acesso ao Google.

### 6. Confirmar resultado
```
✓ Adicionado ao Google Doc com sucesso.

📂 Seção: [membro > sprint / Issues]
📄 PR #[N] — Iteração [I] inserida
🔗 https://docs.google.com/document/d/1ccbII77jCOIl7ksEljhnI8PHJZLOQpASQhYnH1y8fJc/edit
```

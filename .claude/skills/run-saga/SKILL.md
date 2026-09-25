---
name: run-saga
description: Sobe, roda, loga e dirige o SAGA (FastAPI :8000 + Vite :5173) — screenshot de telas autenticadas, chamadas autenticadas à API, invocação direta do motor de inferência e testes. Use when asked to run, start, launch, stop, screenshot, drive or smoke-test SAGA, call its API as a given user, confirm a change works in the real app, or run its tests.
---

# Rodar e dirigir o SAGA

Backend FastAPI (`:8000`) + frontend React/Vite (`:5173`), ambos falando com o
**Firebase real** do `.env`. O caminho de agente é o driver
`.claude/skills/run-saga/driver.py`: sobe/derruba os servidores, emite ID token
para uma conta existente **sem senha**, chama a API autenticada e tira screenshot
de telas logadas via Playwright (Chromium headless).

Caminhos relativos à raiz do repo. Comandos verificados na tool **Bash** (Git Bash,
Windows 11) — no PowerShell, `$D`/`$TEMP` não existem: use o caminho inteiro e `$env:TEMP`.

## Pré-requisitos

- `uv`, `pnpm`, Node — e um `.env` preenchido (credenciais Admin SDK +
  `VITE_FIREBASE_API_KEY`). Sem `.env` nada disto funciona: login e dados vêm do
  Firebase real.
- Navegador do Playwright (uma vez por máquina; baixa ~115 MB):

```bash
uv run --no-project --with playwright playwright install chromium --only-shell
```

## Setup

```bash
uv sync
pnpm install
```

## Rodar (caminho do agente)

Sempre via `uv run --with playwright` — dá o venv do projeto (firebase_admin,
backend) + playwright, sem tocar no `pyproject.toml`.

```bash
D=.claude/skills/run-saga/driver.py
uv run --with playwright python $D up        # sobe back+front, espera o health
uv run --with playwright python $D status    # health + onde estão os logs
```

Logs e PIDs: `%TEMP%/saga-run/` (`backend.log`, `frontend.log`, `pids.json`).

### API autenticada

`--as EMAIL` = conta existente no Firebase Auth. O driver cria um custom token
(Admin SDK) e troca por ID token no Identity Toolkit — as custom claims
(`role`, `programa_id`) vêm junto. A conta não é alterada.

```bash
uv run --with playwright python $D api GET auth/me --as coord@demo.com
uv run --with playwright python $D api GET students --as coord@demo.com --max 300
uv run --with playwright python $D api GET inference/<student_id> --as coord@demo.com
uv run --with playwright python $D api GET health          # público
uv run --with playwright python $D token --as coord@demo.com   # só o ID token (p/ curl)
```

`api` aceita `--data '<json>'` para POST/PATCH (**escreve no Firestore real** —
peça autorização antes; caminho ainda não exercitado, só GET foi verificado). Caminho sem `/api` ganha o prefixo `/api/v1/`.

### Screenshot de tela logada

A navegação do app é por estado (`setCurrentPage`), **não há URL por tela** —
chega-se às páginas clicando no texto da sidebar/abas, em ordem:

```bash
uv run --with playwright python $D shot "$TEMP/saga-run/dash.png" --as coord@demo.com
uv run --with playwright python $D shot "$TEMP/saga-run/alunos.png" --as coord@demo.com --click Alunos --text
uv run --with playwright python $D shot "$TEMP/saga-run/inferencia.png" --as coord@demo.com --click "Inferência Acadêmica"
uv run --with playwright python $D shot "$TEMP/saga-run/login.png"     # sem --as: tela de login
```

- `--click TEXTO` (repetível) — texto **exato** do elemento.
- `--wait TEXTO` — espera o texto aparecer antes do screenshot.
- `--text` — imprime o texto visível da tela (bom para asserções sem abrir a imagem).
- Erros de console do browser são impressos como `[console.error]`.

**Abra o PNG com Read e olhe** — "screenshot gerado" não significa tela certa.

Conta de demonstração confirmada: `coord@demo.com` (papel `coordenacao`, vê
todas as páginas). Para outros papéis, peça o e-mail ao usuário — não liste
contas do Firebase Auth (dados pessoais).

### Parar

```bash
uv run --with playwright python $D down
```

Só derruba o que o próprio driver subiu (`pids.json`, `taskkill /T`).

## Invocação direta do motor de inferência

A maioria dos PRs de regra (RL01–RL05) não precisa do app: rode o motor puro.
**Tem que ser de dentro de `backend/`** e importando `inference_engine.*` (ver Gotchas):

```bash
cd backend && uv run python - <<'EOF'
from inference_engine.terms import Atom, Compound
from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine
from inference_engine.rules import register_all

fb, rb = FactBase(), RuleBase()
for name in ["creditos_validos", "proficiencia_comprovada", "qualificacao_aprovada",
             "producao_bibliografica_validada", "plano_concluido"]:
    fb.add_fact(Compound(name, [Atom("a1")]))
register_all(rb)
engine = InferenceEngine(fb, rb)
print(engine.query(Compound("apto_defesa", [Atom("a1")])))  # [{'A_1': Atom('a1')}] -> verdadeiro
print(engine.query(Compound("apto_defesa", [Atom("a2")])))  # [] -> falso
EOF
```

## Testes

```bash
uv run pytest -q          # 479 passed, ~6 s — testpaths no pyproject.toml, sem Firebase
```

## Rodar (caminho humano)

`uv run uvicorn backend.app.main:app --reload --port 8000` + `pnpm dev`, abrir
`http://localhost:5173` e logar com e-mail/senha. Inútil para agente: prende o
terminal e exige senha.

## Gotchas

- **`TypeError: Fato deve ser um Compound; recebido Compound`** — o motor importa a
  si mesmo como `inference_engine.terms`. Importar como `backend.inference_engine...`
  carrega o módulo duas vezes e as classes deixam de ser iguais. Rode de `backend/`
  e importe `inference_engine.*`.
- **Sem `Authorization` a API responde 422, não 401** — o header é parâmetro
  obrigatório do FastAPI. 401 só com token presente e inválido.
- **`networkidle` do Playwright não serve após clique** — numa SPA não há
  navegação, então `wait_for_load_state("networkidle")` volta na hora e o
  screenshot sai com "Consultando o motor…". O driver conta as requisições
  `/api/` em andamento e espera 800 ms de silêncio + sumirem os placeholders
  `Carregando…`/`Consultando…`.
- **Login no browser sem senha** — o driver faz `signInWithCustomToken` dentro
  da página importando a **mesma** URL pré-empacotada que o app usa
  (`/node_modules/.vite/deps/firebase_auth.js?v=<hash>`, lida do fonte servido de
  `/src/lib/firebase.ts`). Importar outra URL cria uma segunda instância do SDK e o
  app não enxerga o login. Só funciona com o **dev server** (não com `dist/`).
- **`--full` não captura a página inteira** — o layout rola dentro de um container
  interno, não no `body`; o screenshot fica do tamanho do viewport (1440×900).
- **Dados são reais** — o Firestore do `.env` é compartilhado; o dashboard mostra o
  estado atual do banco. Leitura à vontade; escrita só com autorização.
- **Playwright × navegador em cache** — `uv run --with playwright` pega a última
  versão do pacote; se ela pedir outro build do Chromium, rode de novo o
  `playwright install` dos pré-requisitos.

## Troubleshooting

| Sintoma | Correção |
|---|---|
| `BrowserType.launch: Executable doesn't exist at ...chromium_headless_shell-NNNN...` | `uv run --no-project --with playwright playwright install chromium --only-shell` |
| `up` diz "já está no ar (não foi iniciado por mim)" e `down` não derruba | Servidor subido fora do driver; mate pela porta (`netstat -ano \| grep :8000`, `taskkill //T //F //PID <pid>`) |
| `[aviso] tela não assentou em 30s` | Requisição travada ou placeholder novo; confira `%TEMP%/saga-run/backend.log` e use `--wait` com um texto do estado final |
| `signInWithCustomToken falhou` / `UserNotFoundError` | E-mail não existe no Firebase Auth do `.env` |

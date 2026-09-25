# Calibragem de Trabalho

> Como **este projeto** divide trabalho: quando uma issue é grande demais para uma
> tacada, e o que conta como uma camada na hora de fatiar os commits.
>
> Preencher na sessão de *grill with docs* (skill `grill-with-docs`, log em
> `docs/grills_logs/`). Seção vazia significa: valem os defaults genéricos, descritos
> nos guias que apontam para cá.
>
> Este arquivo é **do projeto**, não do template: a `adopt-repo` só o copia se faltar,
> e nada no ARK sobrescreve o que você escreveu aqui.

---

## Quebra de trabalho

> Consumido pelo `complexity-guide.md` do `/start-issue` (em
> `$ARK_HOME/commands/start-issue/`), que decide se a issue vira implementação direta
> ou plano de sub-tarefas.
>
> O que entra aqui: limiares diferentes ("neste repo, dois módulos já bastam para
> quebrar"), a unidade que o repositório usa no lugar de "módulo/diretório" (pacote,
> serviço, contexto), ou critérios próprios que a régua genérica não captura.

Vale a régua do próprio projeto:
[`.claude/commands/workflow/start-issue/complexity-guide.md`](../commands/workflow/start-issue/complexity-guide.md).
Em resumo, quebrar em sub-tarefas quando a issue:

- atravessa camadas do backend (model → repository → service → endpoint);
- afeta frontend **e** backend;
- cria 3+ arquivos em partes distintas do projeto;
- mexe em lógica do `inference_engine` (spec + regra + testes) ou cria aspecto AOP;
- passa de ~1,5 h estimada.

Correção pontual (bug em um módulo, ajuste de UI isolado) vai direto.

---

## Camadas deste projeto

> Consumido pelo `atomicity-rules.md` do `/commit` (em `$ARK_HOME/commands/commit/`),
> que agrupa as mudanças em commits atômicos.
>
> O que entra aqui: quais pastas são camadas neste repositório, ou a declaração de
> que ele não é organizado em camadas — nesse caso vale só "um domínio por commit".

Fonte da verdade: [`guidelines/CommitConventions.md`](../../guidelines/CommitConventions.md).

**Backend** (`backend/app/`), na ordem em que os commits progridem:
`models/` → `repositories/` → `services/` → `api/v1/`. Transversais, cada uma sua
própria camada: `aspects/`, `core/`.

**Motor de inferência:** `backend/inference_engine/` (núcleo) e
`backend/inference_engine/rules/` (RL01–RL05) são camadas separadas.

**Frontend** (`src/`): `api/` → `hooks/` → `app/components/`.

**Testes** sempre em commit próprio (`test`), depois do `feat`/`fix` correspondente.

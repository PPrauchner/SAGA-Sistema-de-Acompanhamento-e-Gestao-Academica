# Modelo de Dados — SAGA

Modelo de dados do Firestore para o SAGA (Sistema de Acompanhamento e Gestão Acadêmica).
Documenta o **modelo completo pretendido**, marcando o que já está implementado vs. planejado.

> **Fonte canônica:** `docs/specs/03_firebase_schema.json`, refinado pelas decisões em
> [`data-model-decisions.md`](./data-model-decisions.md) (sessão de *grill-me*).
>
> **Precedência código × docs.** Depende da natureza da divergência:
> - **Divergência acidental** numa entidade já implementada (✅) — a doc apenas se
>   desatualizou: o **código em execução vence**; corrija a doc. (Hoje só `users`/`invites`
>   têm código real.)
> - **Refinamento deliberado** registrado em [`data-model-decisions.md`](./data-model-decisions.md)
>   (série **R**) ainda **não aplicado ao código**: a **decisão/doc lidera**; o código diverge
>   de forma conhecida e **deve ser ajustado** (rastreado como bloqueador, ex.: C1, M1).
>
> Em suma: o código vence quando a doc só se atrasou; a doc/decisão vence quando o log
> deliberou uma mudança que o código ainda não acompanhou.
>
> **Escopo:** apenas backend / Firestore. O motor de inferência (`Atom`, `Variable`,
> `Compound`, `FactBase`) é representação lógica em memória, **não** dados persistidos, e
> fica fora deste documento. Tipos TypeScript do frontend também ficam fora.

---

## Legenda e convenções

**Estado de implementação:**

| Marca | Significado |
|-------|-------------|
| ✅ | Implementado (há código real) |
| 🔲 | Planejado (stub ou ausente) |

Hoje só `users` e `invites` têm código real (`backend/app/models/user.py`, `auth_service.py`).
Todas as demais coleções estão planejadas.

**Convenções aplicadas a todas as coleções:**

- **Chave do documento:** indicada por coleção. Três padrões — `uid` (Firebase Auth),
  `auto-id` (gerado pelo Firestore) e chave natural (`invites`=token UUID,
  `programs`=`prog_default`, `vehicle_levels`=`veiculo_id`).
- **Auditoria:** `criado_em` / `atualizado_em` (Timestamp) e, quando há autoria de
  escrita, `atualizado_por` / `criado_por` (uid). Presentes na maioria das coleções.
- **`programa_id`:** discriminador de tenant (FK lógica a `programs`). Mantém a
  generalização multi-programa, mas é **efetivamente single-tenant no MVP** (`prog_default`).
  Tratado como atributo com nota — **sem aresta** nos diagramas (evita poluição).
- **Campos calculados:** marcados como `calc`. Distinguem-se em *snapshot persistido*
  (ex.: `inferred_status`) e *computado em leitura* (ex.: `orientandos_ativos`).
- **Referências soft polimórficas** (ex.: `recurso`, `entidade_id`): string path, **não**
  FK real — sem aresta nos diagramas.

**Notação dos diagramas (Mermaid `erDiagram`):** as sub-coleções do Firestore são
representadas como entidades ligadas por **composição (1:N)**. Não são FKs relacionais —
são aninhamento de documentos NoSQL. As cardinalidades (`||--o{`, `||--o|`) descrevem a
relação lógica, não constraints impostas pelo banco (o Firestore não impõe integridade
referencial; as invariantes são garantidas nos *services*).

---

## Visão geral (ER macro)

Entidades-âncora e ligações principais, sem atributos.

```mermaid
erDiagram
    users ||--o| students : "é aluno"
    users ||--o| advisors : "é orientador"
    advisors ||--o{ students : orienta
    programs ||--o{ vehicle_levels : classifica
    vehicles ||--o| vehicle_levels : "tem nível"
    students ||--o{ work_plan : possui
    students ||--o{ activities : registra
    students ||--o{ extensions : solicita
    students ||--o{ transfer_requests : transfere
    students ||--o{ inferred_status : historiza
    programs ||--o{ coordination_transfers : transfere_coordenacao
    activity_types ||--o{ activities : tipifica
    productions ||--o{ activities : "creditada por"
    vehicles ||--o{ productions : publica
```

> A produção (`productions`) é **coleção raiz** (decisão Q8/opção C): um artigo existe
> uma única vez e é creditado a N alunos via `activities.producao_id`. Ver
> [Atividades & Produções](#3-atividades--produções).

---

## 1. Identidade & papéis

Quem são os usuários e como os papéis se materializam.

```mermaid
erDiagram
    users {
        string uid PK
        string email
        string nome
        string role
        string programa_id
        bool ativo
        bool primeiro_acesso_completo
    }
    invites {
        string token PK
        string email
        string role
        string nome
        bool usado
        timestamp expira_em
    }
    students {
        string id PK
        string uid FK
        string orientador_id FK
        string coorientador_id FK
        string nivel
        string situacao_registrada
        string situacao_inferida
    }
    advisors {
        string id PK
        string uid FK
        string departamento
        int limite_orientandos
    }
    programs {
        string id PK
        int creditos_total_min
        int max_prorrogacoes
        int meses_ate_qualificacao
    }

    users ||--o| students : "é aluno"
    users ||--o| advisors : "é orientador"
    advisors ||--o{ students : orienta
    advisors |o--o{ students : coorienta
```

### Papéis e identidade (modelo de decisão)

- Um `users` é **aluno** (tem `students`), **orientador** (tem `advisors`),
  **coordenador**, ou **coordenador + orientador** (mesmo `uid`, acumula). Aluno nunca acumula.
- `role` é **valor único** = papel de maior privilégio. A capacidade de **orientar** vem da
  **existência do doc `advisors`**, não de `role`. Coordenação engloba as permissões de orientador.
  O *toggle* "Orientador | Coordenador" é filtro de visão no **frontend**, não fronteira de
  segurança ([ADR-0002](./adr/0002-papel-unico-com-toggle-de-visao.md)).
- O papel `adm` ([ADR-0001](./adr/0001-papel-adm-global.md)) é um **superusuário global**, fora
  de qualquer programa: é o **único papel com `programa_id` nulo**. Cria/edita/desativa
  coordenadores (operação cross-programa); criado via script/backend, nunca por convite. Não
  orienta nem cursa, então não tem `students`/`advisors`.
- **Invariante** (garantida no service, não pelo banco): existe doc `advisors` ⟺ o usuário
  pode orientar. Criar/ativar orientador cria o `advisors`; revogar remove. Não há
  `role="orientador"` sem `advisors`.
- `student_id` / `advisor_id` **não** são campos de `users/` — só aparecem em `UserResponse`,
  resolvidos por lookup em leitura.

### `users` ✅ — chave: `uid`

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `uid` | string | PK | uid do Firebase Auth |
| `email` | string | | normalizado (trim + minúsculas) |
| `nome` | string | | |
| `role` | string | | enum `aluno`\|`orientador`\|`coordenacao`\|`adm` (papel de maior privilégio; `adm` é superusuário global — ADR-0001) |
| `programa_id` | string\|null | →`programs` (soft) | **null apenas para `adm`** (global, fora de programa); não-nulo para os demais |
| `ativo` | bool | | |
| `primeiro_acesso_completo` | bool | | persistido; **não exposto** em `UserResponse` |
| `criado_em` / `atualizado_em` | timestamp | | |

### `invites` ✅ — chave: `token` (UUID v4)

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `token` | string | PK | UUID do convite |
| `email` | string | | |
| `role` | string | | `aluno`\|`orientador` (coordenação e `adm` não são criados por convite) |
| `nome` | string | | **incluído** (código grava; origem do `users.nome`) — ausente na spec 03 |
| `programa_id` | string | →`programs` (soft) | |
| `usado` | bool | | |
| `expira_em` | timestamp | | TTL 48h |
| `criado_por` | string | →`users.uid` (soft) | coordenação que emitiu |
| `criado_em` | timestamp | | |

### `students` 🔲 — chave: `auto-id` (entidade central)

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `uid` | string | →`users.uid` | identidade |
| `matricula` | string | | |
| `nome` / `email` | string | | |
| `orientador_id` | string | →`advisors` (auto-id) | **não** é o uid |
| `coorientador_id` | string\|null | →`advisors` (0..1) | 2º orientador opcional |
| `programa_id` | string | →`programs` (soft) | |
| `nivel` | string | | `mestrado`\|`doutorado` — **MVP foca mestrado** |
| `data_ingresso` | timestamp | | |
| `prazo_final` | timestamp | | **vigente**; escrito no ingresso **e** por prorrogação aprovada |
| `situacao_registrada` | string | | enum 7 valores¹; escrito **manual** (coordenação) **e** por transições automáticas |
| `situacao_inferida` | string | `calc` | cache do último `inferred_status`; escrito **só pelo motor** |
| `proficiencia_comprovada` | bool | | default false; dispara transição de situação |
| `proficiencia_data` | timestamp\|null | | |
| `qualificacao_aprovada` | bool | | default false; dispara transição de situação |
| `qualificacao_data` | timestamp\|null | | |
| `criado_em` / `atualizado_em` / `atualizado_por` | timestamp / uid | | |

¹ `regular`\|`em_prorrogacao`\|`em_risco`\|`qualificado`\|`fase_defesa`\|`concluido`\|`desligado`.
`situacao_registrada` (humano + transição automática) e `situacao_inferida` (motor) usam o mesmo enum;
a **divergência entre as duas é sinal de atenção**.

### `advisors` 🔲 — chave: `auto-id`

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `uid` | string | →`users.uid` | |
| `nome` / `email` | string | | |
| `departamento` | string | | |
| `lattes` | string\|null | | |
| `programa_id` | string | →`programs` (soft) | |
| `limite_orientandos` | int | | default 5 |
| `criado_em` / `atualizado_em` | timestamp | | |
| `orientandos_ativos` | int | `calc` | computado em leitura (contagem de `students` por `orientador_id`) |

### `transfer_requests` - colecao raiz - chave: `auto-id`

Registra transferencias same-program de orientando entre orientadores. A mesma entidade cobre
o mover-direto da coordenacao e a solicitacao do orientador com aprovacao da coordenacao.

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `id` | string | | auto-id Firestore do documento em `transfer_requests/` |
| `student_id` | string | ->`students` | aluno transferido |
| `orientador_origem_id` | string | ->`advisors` | orientador atual no momento da solicitacao |
| `orientador_destino_id` | string | ->`advisors` | destino imutavel da solicitacao |
| `solicitante_id` | string | ->`users.uid` | quem iniciou a solicitacao/acao |
| `programa_id` | string | ->`programs` (soft) | origem e destino precisam pertencer ao mesmo programa |
| `status` | string | | `pendente`\|`aprovada`\|`rejeitada`\|`cancelada` |
| `tipo` | string | | `direta_coordenacao`\|`solicitada_orientador` |
| `motivo` / `observacao` | string\|null | | justificativa de rejeicao/cancelamento ou observacao livre |
| `created_at` / `updated_at` | timestamp | | |
| `approved_at` / `approved_by` | timestamp / uid | | preenchido quando aprovada ou mover-direto efetivado |
| `rejected_at` / `rejected_by` | timestamp / uid | | preenchido quando rejeitada |
| `cancelled_at` / `cancelled_by` | timestamp / uid | | preenchido quando cancelada |
| `cancel_reason` | string\|null | | motivo tecnico/usuario do cancelamento |
| `cancelled_request_id` | string\|null | ->`transfer_requests` | mover-direto pode cancelar pendente anterior |

Status aceitos:

| Status | Significado |
|--------|-------------|
| `pendente` | solicitacao criada por orientador e aguardando decisao da coordenacao |
| `aprovada` | transferencia efetivada; tambem usado no mover-direto da coordenacao |
| `rejeitada` | coordenacao recusou a solicitacao e registrou `motivo` |
| `cancelada` | orientador solicitante cancelou a solicitacao, ou a coordenacao cancelou uma pendente ao mover direto |

Relacionamentos:

- `transfer_requests.student_id` -> `students`
- `transfer_requests.orientador_origem_id` -> `advisors`
- `transfer_requests.orientador_destino_id` -> `advisors`
- `transfer_requests.programa_id` -> `programs`
- `transfer_requests.solicitante_id`, `approved_by`, `rejected_by`, `cancelled_by` -> `users.uid`
- `transfer_requests.cancelled_request_id` -> `transfer_requests`

Ciclo de vida:

- Coordenacao pode criar uma transferencia direta com `tipo="direta_coordenacao"`; o registro ja nasce `aprovada`.
- Orientador pode criar solicitacao com `tipo="solicitada_orientador"`; o registro nasce `pendente`.
- Coordenacao pode aprovar (`aprovada`) ou rejeitar (`rejeitada`) solicitacao pendente.
- Orientador solicitante pode cancelar (`cancelada`) solicitacao pendente.
- Transferencia direta pela coordenacao cancela eventual solicitacao pendente do mesmo aluno, preenchendo `cancelled_request_id` no novo registro e `cancel_reason` no registro cancelado.

> Invariante: so pode existir uma solicitacao `pendente` por aluno. A efetivacao atualiza
> `students.orientador_id`, limpa `coorientador_id` quando o destino era coorientador atual,
> registra A02/A03 e dispara A05 para origem, destino e aluno.

### `coordination_transfers` - colecao raiz - chave: `auto-id`

Registra a transferencia do papel de coordenacao para um orientador sucessor do mesmo programa,
com aceite obrigatorio do sucessor. Nao gera A03 porque nao altera historico de aluno.

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `programa_id` | string | ->`programs` (soft) | programa da coordenacao transferida |
| `initiator_uid` | string | ->`users.uid` | coordenacao atual que iniciou o convite |
| `successor_uid` | string | ->`users.uid` | orientador convidado para assumir coordenacao |
| `status` | string | | `pendente`\|`aceita`\|`rejeitada`\|`cancelada` |
| `created_at` / `updated_at` | timestamp | | |
| `decided_at` | timestamp\|null | | preenchido em aceite/rejeicao |
| `accepted_at` | timestamp\|null | | preenchido no aceite |
| `rejected_at` / `rejected_by` | timestamp / uid | | preenchido na rejeicao |
| `cancelled_at` / `cancelled_by` | timestamp / uid | | preenchido no cancelamento |

> Swap no aceite: valida pendencia e vinculo ao mesmo programa; troca `set_custom_user_claims`
> do sucessor e do iniciador; atualiza `users/{uid}.role` dos dois; cria `advisors/` para o
> ex-coordenador com `limite_orientandos=5` se ainda nao existir; revoga refresh tokens dos dois;
> marca a transferencia como `aceita`. Se houver falha parcial, repetir o aceite e seguro desde
> que a transferencia continue `pendente`: claims e roles sao regravados com os mesmos valores,
> o documento `advisors/` e reutilizado/criado com id estavel, e tokens podem ser revogados
> novamente sem alterar o resultado final.

### `programs` 🔲 — chave: `prog_default` (singleton de configuração)

Guarda os **fatos de configuração do motor**. `vehicle_levels` é sub-coleção (ver subdomínio 3).

| Campo | Tipo | Notas |
|-------|------|-------|
| `nome` / `instituicao` | string | |
| `duracao_meses` | int | default 24 |
| `creditos_grupo_basico_min` | int | default 12 |
| `creditos_grupo_especifico_min` | int | default 8 |
| `creditos_grupo_tecnologico_max` | int | default 4 |
| `creditos_total_min` | int | default 24 |
| `max_prorrogacoes` | int | default 1 |
| `duracao_prorrogacao_meses` | int | default 6 |
| `meses_ate_qualificacao` | int | default 12 |
| `criado_em` / `atualizado_em` | timestamp | |

---

## 2. Plano de trabalho

Aninhamento profundo sob o aluno: `work_plan → stages → tasks → updates`. Cada nível é
entidade própria (composição 1:N encadeada). `work_plan` é 1:N estrutural — "1 por aluno no MVP".

```mermaid
erDiagram
    students ||--o{ work_plan : possui
    work_plan ||--o{ stages : contém
    stages ||--o{ tasks : contém
    tasks ||--o{ updates : recebe

    work_plan {
        string id PK
        string titulo
        float progresso_percentual
        string status_geral
    }
    stages {
        string id PK
        string nome
        int ordem
        string status
    }
    tasks {
        string id PK
        string titulo
        string status
        string prioridade
        string responsavel_id
    }
    updates {
        string id PK
        string conteudo
        float percentual
        string autor_id
    }
```

### `work_plan` 🔲 — sub-coleção de `students` — chave: `auto-id`

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `titulo` | string | | |
| `data_inicio` / `data_fim_prevista` | timestamp | | |
| `progresso_percentual` | float | `calc` | 0–100, agregado das tasks |
| `status_geral` | string | | `em_andamento`\|`atrasado`\|`concluido` |
| `criado_por` | string | →`users.uid` (orientador) | |
| `criado_em` / `atualizado_em` | timestamp | | |

### `stages` 🔲 — sub-coleção de `work_plan`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nome` | string | `revisao_bibliografica`\|`definicao_problema`\|`desenvolvimento`\|`experimentos`\|`escrita`\|`qualificacao`\|`defesa` |
| `ordem` | int | |
| `data_inicio` / `data_fim` | timestamp | |
| `status` | string | `pendente`\|`em_andamento`\|`concluido`\|`atrasado` |
| `criado_por` | string (uid orientador) | |

### `tasks` 🔲 — sub-coleção de `stages`

| Campo | Tipo | Notas |
|-------|------|-------|
| `titulo` / `descricao` | string | |
| `prazo` | timestamp | |
| `status` | string | `pendente`\|`em_andamento`\|`concluido`\|`atrasado` |
| `prioridade` | string | `baixa`\|`media`\|`alta` |
| `responsavel_id` | string | →`users.uid` (aluno) |
| `criado_por` | string | →`users.uid` (orientador) |
| `criado_em` / `atualizado_em` | timestamp | |

> Convenção implementada: `work_plan`, `stages` e `tasks` usam os status canônicos
> masculinos `concluido` e `atrasado`. Entradas legadas `concluida`/`atrasada` são aceitas
> apenas como compatibilidade e normalizadas na borda.

### `updates` 🔲 — sub-coleção de `tasks`

| Campo | Tipo | Notas |
|-------|------|-------|
| `conteudo` | string | atualização de progresso |
| `percentual` | float | 0–100 |
| `autor_id` | string | →`users.uid` (aluno) |
| `criado_em` | timestamp | |

---

## 3. Atividades & produções

O módulo de maior densidade de regras. **Decisão estrutural (Q8/opção C):** `productions`
é **coleção raiz** — um artigo existe uma vez e é creditado a N alunos via `activities.producao_id`.

```mermaid
erDiagram
    students ||--o{ activities : registra
    activity_types ||--o{ activities : tipifica
    productions ||--o{ activities : "creditada por"
    vehicles ||--o{ productions : publica
    programs ||--o{ vehicle_levels : classifica
    vehicles ||--o| vehicle_levels : "tem nível"

    activities {
        string id PK
        string tipo_id FK
        string producao_id FK
        string status
        float creditos_gerados
        float creditos_concedidos
    }
    productions {
        string id PK
        string veiculo_id FK
        string tipo_producao
        array autores
        float pontuacao_calculada
    }
    activity_types {
        string id PK
        string categoria
        float pontuacao_base
        float limite_maximo_creditos
        bool ativo
    }
    vehicles {
        string id PK
        string nome
        string tipo
    }
    vehicle_levels {
        string veiculo_id PK
        string nivel
        float peso
    }
```

### Subtipo e atribuição de crédito (modelo de decisão)

- **Atividade creditável** = qualquer coisa que gera créditos (disciplina, estágio docência,
  banca, software, artigo). **Produção bibliográfica** = subtipo especial: uma publicação
  ligada a um veículo, com score ponderado (RL05) e que satisfaz a condição de defesa (RL01).
  **Toda produção é atividade; nem toda atividade é produção.**
- Um **artigo** é as duas coisas: tem doc(s) em `activities` (crédito/validação por aluno) **e**
  um doc em `productions` (identidade bibliográfica + score, uma vez).
- **FK invertida (opção C):** `activities.producao_id → productions`. Validação e crédito são
  **por aluno** (cada um tem orientador próprio). **Sem produção órfã**: registrar a produção e a(s)
  atividade(s) é a mesma operação.
- **Crédito: score cheio por autor** (não dividido). A produção guarda `pontuacao_calculada`
  (RL05, uma vez); cada atividade guarda `creditos_gerados` (= score), ajustável por aluno via
  `creditos_concedidos` (coordenação) e capado pelo limite da categoria (RL04) individualmente.
- `productions.autores` aceita **uid de aluno cadastrado E string livre** (autor externo).
  Distinção: `autores` = autoria bibliográfica (inclui externos); `activities.producao_id` =
  quem reivindica crédito (só alunos cadastrados que registraram a atividade).
- Relatórios de "produções do programa" contam `productions` raiz (sem duplicação).

> **Decisão Q8 (opção C):** `productions` é **coleção raiz** e a FK é invertida
> (`activities.producao_id → productions`), para suportar co-autoria entre alunos sem perda de
> crédito. Os specs 03/07 foram alinhados a este modelo (ver `data-model-decisions.md` → R3).
> Historicamente a spec 03 punha `productions` como sub-coleção de `students` referenciando
> `activity_id` — modelo superado.

### `activities` 🔲 — sub-coleção de `students` — chave: `auto-id`

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `tipo_id` | string | →`activity_types` | |
| `producao_id` | string\|null | →`productions` (raiz) | **só** em atividades bibliográficas |
| `aluno_id` | string | →`students` | |
| `descricao` | string | | |
| `data_realizacao` | timestamp | | |
| `comprovante_url` | string\|null | | URL de download (Firebase Storage) |
| `creditos_gerados` | float | `calc` | default = `pontuacao_base` do tipo |
| `creditos_concedidos` | float\|null | | override da coordenação no `/validate` (sobrescreve crédito) |
| `status` | string | | `rascunho`\|`enviado`\|`aprovado`\|`rejeitado` |
| `parecer_orientador` | string\|null | | **campo**, não estado (ação intermediária) |
| `observacao_coordenacao` | string\|null | | |
| `validado_por` | string\|null | →`users.uid` | |
| `validado_em` | timestamp\|null | | |
| `criado_em` / `atualizado_em` | timestamp | | |

### `productions` 🔲 — **coleção raiz** — chave: `auto-id`

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `titulo` | string | | |
| `doi` | string\|null | | chave natural de deduplicação quando presente |
| `veiculo_id` | string | →`vehicles` | |
| `tipo_producao` | string | | `artigo`\|`livro`\|`capitulo` (natureza bibliográfica; situação em `status_publicacao`) |
| `status_publicacao` | string | | `publicado`\|`submetido`\|`aceito` |
| `observacao` | string\|null | | impactos específicos |
| `autores` | array | →`users.uid` **ou** string livre | inclui autores externos |
| `pontuacao_calculada` | float | `calc` | RL05 = `pontuacao_base × peso_veículo`, uma vez |
| `programa_id` | string | →`programs` (soft) | |
| `criado_em` | timestamp | | |

> A produção **não tem status próprio** — a validação vive nas `activities` que a referenciam.

### `activity_types` 🔲 — **coleção raiz** (config coordenação) — chave: `auto-id`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nome` | string | |
| `categoria` | string | `basico`\|`especifico`\|`tecnologico` |
| `pontuacao_base` | float | base do crédito gerado |
| `limite_maximo_creditos` | float\|null | teto por categoria (RL04) |
| `exige_comprovante` | bool | |
| `permite_multiplas` | bool | |
| `ativo` | bool | default true |
| `programa_id` | string | →`programs` (soft) |
| `criado_por` | string (uid coordenação) | |
| `criado_em` / `atualizado_em` | timestamp | |

> Versionado pelo aspecto A03 (`history`) ao alterar pontuação/limite/ativo.

### `vehicles` 🔲 — **coleção raiz** — chave: `auto-id`

| Campo | Tipo | Notas |
|-------|------|-------|
| `nome` | string | |
| `tipo` | string | `evento`\|`revista` |
| `issn` | string\|null | |
| `sigla` | string\|null | |
| `programa_id` | string | →`programs` (soft) |
| `criado_em` | timestamp | |

### `vehicle_levels` ✅ — sub-coleção de `programs` — chave: `veiculo_id`

Classificação de relevância **1:1 opcional (0..1)** com `vehicles` (um veículo pode existir antes
de ser classificado). Guarda o **nível Qualis do veículo no programa**; o peso autoritativo da RL05
vem de [`qualis_weights`](#qualis_weights--sub-coleção-de-programs--chave-auto-id), resolvido por
data de publicação ([ADR-0003](./adr/0003-pesos-qualis-versionados-por-programa.md)).

| Campo | Tipo | Notas |
|-------|------|-------|
| `veiculo_id` | string (PK = id do veículo) | |
| `nivel` | string | `A1`–`A8` \| `SC` (Qualis Único A1–A8 + fallback `SC` = Sem Classificação) |
| `peso` | float | snapshot **denormalizado** do peso default (`PESO_POR_NIVEL`) na classificação — só para exibição na listagem de veículos; **não** é a fonte do score |
| `atualizado_em` / `atualizado_por` | timestamp / uid | |

> **Escala A1–A8 + fallback (ADR-0003, supera R1/R4):** pesos default em
> `backend/app/models/vehicle.py` → `PESO_POR_NIVEL`
> (A1=1.0, A2=0.85, A3=0.7, A4=0.55, A5=0.45, A6=0.35, A7=0.25, A8=0.15, SC=0.1),
> estritamente decrescente. Esses valores são apenas o **bootstrap**: o peso efetivo da RL05 é o
> **vigente por programa na data de publicação**, lido de `qualis_weights` (não desta coleção).
> **Sem nível configurado:** o veículo assume `SC` (fallback).

### `qualis_weights` ✅ — sub-coleção de `programs` — chave: `auto-id`

Pesos Qualis **versionados por programa** ([ADR-0003](./adr/0003-pesos-qualis-versionados-por-programa.md)).
Cada coordenador define, no seu programa, o peso de cada nível da escala `A1`–`A8` + `SC`. Cada
alteração cria uma **nova versão** (nunca sobrescreve): a própria coleção é o histórico de mudanças.
A RL05 usa o peso **vigente na data de publicação** da produção; produção ainda não publicada
(`submetido`/`aceito`) usa o vigente atual (provisório) até ser publicada.

| Campo | Tipo | Notas |
|-------|------|-------|
| `pesos` | map | nível → peso; deve cobrir **exatamente** `A1`–`A8` + `SC`; pesos não-negativos |
| `vigente_desde` | timestamp | momento a partir do qual a versão vale (base da resolução por data) |
| `alterado_por` | string | →`users.uid` (coordenação que criou a versão) |
| `alterado_em` | timestamp | |

> Resolução (`QualisWeightsService` / `inference_service`): seleciona a versão de maior
> `vigente_desde ≤ data_referência`; sem versão aplicável, cai no default `PESO_POR_NIVEL`. O
> `inference_engine` permanece isolado — recebe o peso já resolvido como fato
> `relevancia_peso(Nivel, Peso)`. O `seed_firestore` grava uma versão bootstrap a partir de
> `PESO_POR_NIVEL`.

---

## 4. Inferência & infraestrutura

Snapshots do motor, histórico (A03), auditoria (A02), notificações (A05) e prorrogações.
Coleções transversais geradas por aspectos — **escrita exclusiva via aspecto**.

```mermaid
erDiagram
    students ||--o{ inferred_status : historiza
    students ||--o{ extensions : solicita
    students ||--o{ history : versiona
    work_plan ||--o{ history : versiona
    activity_types ||--o{ history : versiona
    users ||--o{ audit_logs : "registra (soft)"
    users ||--o{ notifications : "recebe (soft)"

    inferred_status {
        string id PK
        timestamp timestamp
        string situacao_inferida
        bool apto_defesa
        bool creditos_validos
        bool em_risco
        map checklist_snapshot
    }
    extensions {
        string id PK
        string tipo
        string student_id
        string aluno_id
        string requester_id
        string programa_id
        string status
        timestamp nova_data
        timestamp prazo_novo
        timestamp data_atual
        timestamp prazo_atual
        timestamp created_at
        timestamp solicitacao
    }
    history {
        string id PK
        string entidade_tipo
        string entidade_id
        map valor_anterior
        map valor_novo
    }
    audit_logs {
        string id PK
        string usuario_id
        string operacao
        string recurso
        string resultado_status
    }
    notifications {
        string id PK
        string tipo
        string destinatario_id
        bool lida
    }
```

> **Checklist não é entidade** — é computado ao vivo em `GET /checklist` e fotografado em
> `inferred_status.checklist_snapshot`. As condições da RL01 são booleanos dentro desse map.

### `inferred_status` 🔲 — sub-coleção de `students` — histórico de inferências

| Campo | Tipo | Notas |
|-------|------|-------|
| `timestamp` | timestamp | |
| `situacao_inferida` | string | enum de situação |
| `apto_defesa` | bool | RL01 |
| `creditos_validos` | bool | RL02 |
| `em_risco` | bool | RL03 |
| `checklist_snapshot` | map | cópia do checklist calculado (condições RL01) |
| `fatos_usados` | array | fatos da FactBase usados na inferência |

> Fonte **historizada canônica** da inferência. `students.situacao_inferida` é só o cache do último.

### `extensions` 🔲 — coleção raiz — prorrogações

| Campo | Tipo | Ref | Notas |
|-------|------|-----|-------|
| `id` | string | | auto-id Firestore do documento em `extensions/` |
| `tipo` | string | | ex.: `prazo_defesa`, `prazo_qualificacao`, `trancamento`, `mudanca_nivel` |
| `student_id` | string | →`students` | aluno da solicitação |
| `aluno_id` | string | →`students` | alias de compatibilidade para `student_id` |
| `requester_id` | string | →`users.uid` | uid de quem abriu a solicitação |
| `programa_id` | string\|null | →`programs` | derivado do aluno |
| `motivo` | string | | |
| `justificativa` | string | | alias de compatibilidade para `motivo` |
| `plano_atualizado` | string\|null | | descrição ou link, quando aplicável |
| `parecer_orientador` | string\|null | | |
| `parecer` | string\|null | | alias de compatibilidade para `parecer_orientador` |
| `semestres_solicitados` | int\|null | | campo legado; o fluxo atual usa `nova_data` |
| `status` | string | | `pendente`\|`em_analise`\|`aprovada`\|`rejeitada` |
| `nova_data` | timestamp | | data solicitada pelo aluno/orientador |
| `prazo_novo` | timestamp | | alias de compatibilidade para `nova_data`; snapshot do novo prazo pretendido |
| `data_atual` | timestamp\|null | | prazo atual do aluno no momento da solicitação |
| `prazo_atual` | timestamp\|null | | alias de compatibilidade para `data_atual` |
| `aprovado_por` | string\|null | →`users.uid` | |
| `aprovado_em` | timestamp\|null | | |
| `created_at` | timestamp | | data de criação |
| `solicitacao` | timestamp | | alias de compatibilidade para `created_at` |
| `criado_em` | timestamp\|null | | campo legado |

> "Prorrogações usadas" = `calc` (contagem de `status="aprovada"`), comparado a
> `programs.max_prorrogacoes` pelo motor. Sem contador persistido.

### `history` 🔲 — sub-coleção **polimórfica** (A03)

Presente sob `students/`, `work_plan/` e `activity_types/`. Uma entidade genérica;
`entidade_tipo`/`entidade_id` discriminam o pai.

| Campo | Tipo | Notas |
|-------|------|-------|
| `entidade_tipo` | string | discriminador |
| `entidade_id` | string | discriminador |
| `valor_anterior` / `valor_novo` | map | snapshot antes/depois |
| `usuario_id` | string | →`users.uid` |
| `role` | string | |
| `timestamp` | timestamp | |

### `audit_logs` 🔲 — **coleção raiz** imutável (A02)

| Campo | Tipo | Notas |
|-------|------|-------|
| `usuario_id` | string | →`users.uid` (soft) |
| `role` | string | |
| `operacao` | string | nome da função Python |
| `modulo` | string | nome do módulo Python |
| `recurso` | string | path soft (ex.: `students/abc123`) — **sem aresta** |
| `valor_entrada` | map | |
| `resultado_status` | string | `sucesso`\|`erro` |
| `erro_mensagem` | string\|null | |
| `timestamp` | timestamp | |
| `duracao_ms` | int | |
| `programa_id` | string | →`programs` (soft) |

> Nunca deletado.

### `notifications` 🔲 — **coleção raiz** (A05)

Única coleção lida **diretamente** pelo frontend (`onSnapshot`).

| Campo | Tipo | Notas |
|-------|------|-------|
| `tipo` | string | `progresso_task`\|`atividade_validada`\|`prorrogacao_aprovada`\|`prazo_critico`\|`atividade_submetida`\|`transferencia_orientador`\|`transferencia_coordenacao` |
| `tipo="transferencia_orientador"` | uso | fluxo `transfer_requests`: criacao de solicitacao, aprovacao, rejeicao, cancelamento e transferencia direta pela coordenacao |
| `titulo` / `mensagem` | string | |
| `destinatario_id` | string | →`users.uid` (soft) |
| `entidade_tipo` / `entidade_id` | string | ref soft polimórfica — **sem aresta** |
| `lida` | bool | default false |
| `timestamp` | timestamp | |
| `programa_id` | string | →`programs` (soft) |

> Índice composto: `(destinatario_id ASC, lida ASC, timestamp DESC)`.
> Revisões de `registration_requests` não geram notificação in-app para o solicitante
> público, pois antes da aprovação/rejeição ele ainda não possui `users.uid`; comunicação
> ao e-mail informado deve ocorrer por mecanismo externo ao `notifications/`.

---

## Invariantes de integridade (garantidas no service)

O Firestore não impõe integridade referencial. Estas regras são responsabilidade dos *services*:

1. **Orientador ⟺ `advisors`**: usuário pode orientar se e somente se existe `advisors/{x}.uid == users.uid`.
   Criar orientador cria o doc; revogar remove. Sem `role="orientador"` órfão.
2. **Produção sem órfã**: toda `activities.producao_id` aponta para uma `productions` existente;
   registrar produção + atividade(s) é uma operação atômica.
3. **Papel único + acumulação**: aluno nunca acumula; orientador pode acumular coordenação no mesmo `uid`.
   Perder a última capacidade ⇒ desativar conta (`ativo=false`), nunca `role` vazio.
4. **`prazo_final` vigente**: atualizado no ingresso e a cada prorrogação aprovada; cada
   `extensions.prazo_novo` guarda o histórico.
5. **Transferencia same-program**: origem e destino pertencem ao mesmo `programa_id`, destino
   respeita `limite_orientandos`, aluno terminal (`concluido`/`desligado`) nao transfere e
   solicitacao duplicada pendente retorna conflito.
6. **Transferencia de coordenacao**: apenas uma `coordination_transfers` pendente por programa;
   sucessor deve ser orientador do mesmo programa; aceite mantem exatamente uma coordenacao ativa.

## Campos calculados (não-entrada do usuário)

| Campo | Coleção | Tipo de cálculo |
|-------|---------|-----------------|
| `situacao_inferida` | `students` | snapshot persistido (cache do último `inferred_status`) — motor |
| `progresso_percentual` | `work_plan` | computado em leitura (agregado das tasks) |
| `creditos_gerados` | `activities` | derivado de `activity_types.pontuacao_base` |
| `pontuacao_calculada` | `productions` | snapshot persistido — RL05 |
| `orientandos_ativos` | (resposta de `advisors`) | computado em leitura (contagem) |
| `apto_defesa` / `creditos_validos` / `em_risco` | `inferred_status` | snapshot persistido — RL01/RL02/RL03 |
| checklist | (não-entidade) | computado ao vivo + fotografado em `inferred_status.checklist_snapshot` |
| prorrogações usadas | (derivado) | computado em leitura (contagem de `extensions` aprovadas) |

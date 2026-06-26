# Data Model — Registro de Decisões

> Log das decisões de modelagem do `data-model.md` do SAGA, tomadas em sessão de
> *grill-me*. Cada entrada traz a **pergunta**, a **recomendação** e a **decisão final**.
> Atualizado a cada pergunta respondida.
>
> Fontes: `docs/specs/03_firebase_schema.json` (schema canônico), `05_discentes.json`,
> `07_atividades_producoes.json`, `CONTEXT.md`.
>
> **Precedência código × docs.** Divergência acidental numa entidade já implementada
> (hoje só `users`/`invites`; o resto são stubs) → o **código em execução vence**; corrija a
> doc. Refinamento deliberado da série **R** (abaixo) ainda não aplicado ao código → a
> **decisão lidera** e o código deve ser ajustado (bloqueador, ex.: C1, M1).

---

## Resoluções iniciais (pré-grill)

### Escopo
- **Modelo completo pretendido**, marcando `✅ implementado` (só `users`/`invites`) vs `🔲 planejado`.
- Coleções operacionais/derivadas (`audit_logs`, `notifications`, `history`, `inferred_status`): entidades de primeira classe, em seção separada **"Infraestrutura / Auditoria / Derivadas"**.
- Sub-coleções: cada nível é entidade própria, ligada por **composição (1:N)**.
- Motor de inferência (`Atom`, `Variable`, `Compound`, `FactBase`): **fora** do data-model (representação lógica, não persistida).
- Frontend / tipos TS: **fora** — só backend/Firestore.

### Conflitos spec × código
- `invites.nome`: **incluir** (código grava em `auth_service.py:88`; origem do `users.nome`).
- `users.primeiro_acesso_completo`: campo **persistido** em `users/`, não exposto na API.
- `users.student_id` / `advisor_id`: **não** são campos de `users/`; só de `UserResponse`, resolvidos por lookup em leitura.

### Campos ambíguos
- `status` de atividade/produção: enum canônico de 4 valores `rascunho|enviado|aprovado|rejeitado`. `parecer_orientador` é **campo**, não estado.
- Créditos: `activity_types.pontuacao_base` (base do tipo) → `activities.creditos_gerados` (default = base) → `creditos_concedidos` (override da coordenação no `/validate`, sobrescreve `creditos_gerados`).

### Relacionamentos
- `students.orientador_id` → auto-id de `advisors/` (não uid). `coorientador_id` = 2º advisor opcional (0..1).
- `programs/{id}/vehicle_levels/{veiculo_id}` = config 1:1 com `vehicles/`, por programa.

### Negócio
- Campos calculados (`situacao_inferida`, `progresso_percentual`, `pontuacao_calculada`, `creditos_gerados`, `orientandos_ativos`, `elegivel`, `apto_defesa`): marcados como `calculado`, distinguindo *snapshot persistido* de *computado em leitura*.
- `programa_id`: generalização multi-programa mantida, **efetivamente single-tenant no MVP** (`prog_default`).
- ER em Mermaid: sub-coleções como entidades em composição 1:N, com nota de que são aninhamento NoSQL, não FKs reais.

### Decisão de domínio (AskUserQuestion)
- `students.nivel`: manter enum `'mestrado'|'doutorado'` (como specs 03/05), com nota **MVP foca mestrado**.

---

## Decisões do grill-me

### Q1 — Cardinalidade `users` ↔ `students`/`advisors`
**Decisão:** 1:1 opcional. `users.uid` é a âncora de identidade; `students.uid` e `advisors.uid` são a FK lógica. `student_id`/`advisor_id` em `UserResponse` são o caminho inverso resolvido em leitura (não persistido). ER: `users ||--o| students` e `users ||--o| advisors`.

### Q2/Q3 — Papéis acumuláveis e o `role` do JWT
**Contexto:** um usuário pode ser *só aluno*, *só orientador*, *só coordenador*, ou *coordenador + orientador* (mesmo `uid`). Aluno nunca acumula. `role` é valor único (`Literal`), então não cabe "os dois".
**Decisão (opção a):** `role` continua **único** = papel de maior privilégio. A capacidade de **orientar** vem da **existência do doc `advisors`**, não do valor de `role`. Coordenação engloba as permissões de orientador. "É orientador?" ⟺ "tem doc em `advisors/{x}` com `uid == users.uid`".

### Q4 — Invariante role ⟺ advisors
**Decisão (opção a):** invariante **documentada e garantida no service** — criar/ativar orientador cria o doc `advisors` na mesma operação; revogar remove. Evita orientador "fantasma" (`role="orientador"` sem `advisors`). Firestore não impõe integridade referencial; é regra de negócio.

**Revogação independente das capacidades** (consequência travada):
| Capacidade | Onde mora | Conceder | Revogar |
|---|---|---|---|
| Coordenador | `users.role` | `role="coordenacao"` | rebaixar `role` → `"orientador"` |
| Orientador | doc `advisors/{x}` | criar/ativar doc | apagar/desativar doc |

Caso de borda: usuário **só coordenador** que perde a coordenação → desativar conta (`ativo=false`), não deixar `role` vazio.

### Q5 — `situacao_registrada` × `situacao_inferida` × `inferred_status`
**Decisão:**
- `situacao_inferida` = campo **calculado/cache**, espelha o último snapshot de `inferred_status`. Escrito **só pelo motor de inferência** (regra declarativa).
- `situacao_registrada` = campo **editável**, com **duas origens de escrita**: manual (coordenação) **e** transições automáticas (ex.: `qualificacao_aprovada=true` → `qualificado`). Transição automática é ação explícita de service/aspecto, **não** o motor.
- `inferred_status` = entidade de **histórico** (snapshots imutáveis), composição 1:N a partir de `students`.
- Divergência entre `registrada` e `inferida` = sinal de atenção (realidade ≠ registro).

### Q6 — `work_plan` e aninhamento
**Decisão:** `work_plan` é **1:N** estrutural com `students` (sub-coleção), com nota "1 por aluno no MVP". Os 4 níveis `work_plan → stages → tasks → updates` são **4 entidades distintas**, em composição 1:N encadeada.

### Q7 — Produção como subtipo de atividade
**Status:** parcialmente **substituída por Q8 (opção C)**. Mantido: produção é subtipo de atividade (toda produção é atividade; nem toda atividade é produção); um artigo é atividade **e** produção; atividades não-bibliográficas (disciplina, software) não são produções. A estrutura de persistência foi redefinida em Q8.

### Q8 — Co-autoria entre alunos
**Contexto:** um artigo pode ter vários alunos autores. No schema original (`productions` sob um aluno + `autores[]` como rótulo), só o "dono" ganharia créditos/RL01; co-autores ficariam de fora.
**Decisão (opção C):** **`productions` vira coleção raiz** (a identidade do artigo: `titulo`, `doi`, `veiculo_id`, `tipo_producao`, `status_publicacao`, `autores[]`, `pontuacao_calculada`, `observacao`). Cada aluno autor tem um doc em `activities` (no seu subtree) que **referencia** a produção (`producao_id`) — invertendo a FK (atividade → produção). Validação e crédito permanecem **por aluno** (cada um tem orientador próprio); RL05 calcula o score **uma vez** na produção raiz; RL01 por aluno = ter atividade aprovada ligada a uma produção validada.
- **Desvio consciente vs. spec 03** (que punha `productions` como sub-coleção referenciando `activity_id`). Documentar como desvio.
- `autores[]` aceita **uid de aluno cadastrado E string livre** (autor externo fora do sistema).
- Distinção a documentar: `autores[]` = autoria bibliográfica (inclui externos); `activities.producao_id` = quem reivindica crédito (só alunos cadastrados que registraram a atividade).
- Relatórios de "produções do programa": deduplicar por `productions` raiz (não há mais duplicação — a produção é única).

### Q9 — Atribuição de crédito entre co-autores
**Decisão:** **score cheio por autor** — cada co-autor conta a produção integralmente, **sem dividir** a pontuação. A **produção** guarda o score canônico (`pontuacao_calculada`, RL05, calculado uma vez); cada **atividade** do aluno guarda `creditos_gerados` = esse score, ajustável **por aluno** pela coordenação (`creditos_concedidos`) e capado pelo limite da categoria (RL04) **individualmente**. Produção = fonte da pontuação bibliográfica; atividade = crédito efetivamente concedido àquele aluno.

### Q10 — Integridade `vehicles` ↔ `vehicle_levels`
**Decisão:** `programs/{prog}/vehicle_levels/{veiculo_id}` é **1:1 opcional (0..1)** com `vehicles/` — um veículo pode ser cadastrado antes de a coordenação classificá-lo. Sem nível configurado, a RL05 usa **peso default `SC` = 0.2** (fallback documentado), e a coordenação pode reclassificar depois (recalcula o score). Garante RL05 total (sempre retorna pontuação), sem produção "travada".

### Q11 — Coleções transversais (`history`, `audit_logs`, `notifications`)
**Decisão:**
- `history` (A03): **uma entidade genérica única**, ligada por composição aos três pais (`students`, `work_plan`, `activity_types`). `entidade_tipo`/`entidade_id` são o discriminador.
- `audit_logs` (A02) e `notifications` (A05): entidades raiz autônomas, com relacionamento **fraco** a `users` via uid (`users ||--o{ audit_logs`, `users ||--o{ notifications`).
- Referências polimórficas soft (`recurso`, `entidade_id`): **sem aresta** no ER — só atributo com nota (string path), **não** FK real.
- As três numa seção **"Infraestrutura / Auditoria / Derivadas"**; escrita exclusiva via aspecto.

### Q12 — `extensions` (prorrogações) e `students.prazo_final`
**Decisão:**
- `students ||--o{ extensions` (1:N, composição) — aluno pode solicitar mais de uma ao longo do tempo, mesmo que o limite aprovável seja `programs.max_prorrogacoes` (default 1).
- `students.prazo_final` tem **duas origens de escrita**: inicial (`data_ingresso` + duração) **e** aprovação de prorrogação (vira `prazo_novo`).
- "Prorrogações usadas" = **derivado** (contagem de `extensions` com `status="aprovada"`), comparado a `programs.max_prorrogacoes` pelo motor (`prorrogacoes_dentro_limite`). Sem contador persistido.
- `extensions.prazo_novo` = snapshot histórico de cada aprovação; `students.prazo_final` = valor **vigente** (cache do último aprovado). Distintos, ambos existem.

### Q13 — Checklist × `inferred_status`
**Decisão:**
- Checklist **não é entidade própria**: é (a) computado ao vivo pelo motor em `GET /checklist` e (b) fotografado em `inferred_status.checklist_snapshot` a cada inferência.
- `inferred_status` é a **única fonte historizada** da inferência (snapshot completo: situação, aptidão, créditos, em risco, checklist, fatos usados); `students.situacao_inferida` é só o cache do último.
- As condições da RL01 aparecem como **booleanos dentro de `checklist_snapshot`**, não como campos soltos.
- No ER só `inferred_status` aparece; "checklist" entra na seção de campos calculados.

### Q14 — `programs` (config/fatos) e threading de `programa_id`
**Decisão:**
- `programs` é **entidade de configuração singleton** (`prog_default` no MVP); os limiares (`creditos_*`, `max_prorrogacoes`, `meses_ate_qualificacao`, etc.) são atributos marcados como "fatos de configuração do motor". `vehicle_levels` é sub-coleção (composição).
- `programa_id` é **discriminador de tenant soft**: atributo com nota ("FK lógica ao programa, single-tenant no MVP"), **sem aresta** no ER. Única aresta estrutural de `programs` é → `vehicle_levels`.
- `activity_types` é coleção raiz de config da coordenação (com `programa_id`); `activities.tipo_id → activity_types/{id}` **é aresta real** (`activity_types ||--o{ activities`).

### Q15 — Estrutura dos diagramas ER
**Decisão (opção b):** **ER por subdomínio** (não um único diagrama):
1. Identidade & papéis — `users` / `students` / `advisors` / `programs`
2. Plano de trabalho — `work_plan → stages → tasks → updates`
3. Atividades & produções — `activities` / `productions` (raiz) / `activity_types` / `vehicles` / `vehicle_levels`
4. Inferência & infra — `inferred_status` / `history` / `audit_logs` / `notifications` / `extensions`

Mais um **ER macro** só com entidades-âncora e ligações principais (sem atributos). Tabelas de atributos detalhadas acompanham cada subdomínio.

---

## Refinamentos (pós-implementação)

> Decisões tomadas após a primeira implementação (revisão do PR #111, 2026-06-18).

### R1 — Escala de níveis de relevância: 4 níveis → 7 níveis (Qualis Único)

> **⚠️ Superada por [ADR-0003](./adr/0003-pesos-qualis-versionados-por-programa.md).** A escala global única e estática (`A1, A2, A3, A4, B1, B2, SC` com `PESO_POR_NIVEL` hardcoded) foi substituída por pesos **A1–A8 + fallback**, configuráveis e versionados **por programa**. R1 e R4 abaixo ficam como registro histórico.

**Contexto:** a escala original (Q10) tinha 4 níveis (`A1/A2/B/C`). O PR #111 introduziu uma escala
de 7 níveis no código (fixtures/frontend/seed), gerando incoerência com a documentação.
**Decisão:** adotar a escala de **7 níveis** alinhada ao Qualis Único da CAPES:
`A1 | A2 | A3 | A4 | B1 | B2 | SC` (`SC` = Sem Classificação), com pesos
`A1=1.0, A2=0.85, A3=0.7, A4=0.7, B1=0.5, B2=0.5, SC=0.2`. O fallback para veículo sem nível
configurado passa de `C=0.5` para **`SC=0.2`** (refina Q10).
**Resolução:** a escala definitiva (monotônica) e a propagação ao runtime foram decididas e
aplicadas na **R4** (issue #133); o bloqueador C1 (runtime na escala antiga de 4 níveis) fica
resolvido.

### R2 — `tipo_producao` = natureza; situação em `status_publicacao`

**Contexto:** o enum `tipo_producao` (`artigo_publicado | artigo_submetido | livro | capitulo`)
duplicava a informação de `status_publicacao` (`publicado | submetido | aceito`).
**Decisão:** `tipo_producao` passa a descrever apenas a **natureza** da produção
(`artigo | livro | capitulo`); a situação de publicação vive exclusivamente em `status_publicacao`.
Aplicado em `data-model.md`, specs 03 e 07.

### R3 — `productions` permanece coleção raiz (mantém Q8)

**Contexto:** os specs 03/07 e o código do PR #111 descreviam `productions` como subcoleção de
`students`, divergindo da decisão Q8 (coleção raiz + `activities.producao_id → productions`).
**Decisão:** **manter Q8** — `productions` é coleção raiz. Os specs 03/07 foram atualizados para
refletir a estrutura raiz e a FK invertida; o código do PR #111 (subcoleção) precisa ser
ajustado (bloqueador M1 da revisão).

### R4 — Pesos Qualis monotônicos (resolve a pendência de R1)

**Contexto:** R1 deixou em aberto se os pesos `A3=A4=0.7` e `B1=B2=0.5` (herdados do PR #111)
deveriam ser monotônicos. Empates entre níveis tornam a distinção de nível irrelevante para o
score da RL05, e o runtime ainda operava na escala antiga de 4 níveis (`A1=2.0…C=0.5`).
**Decisão (issue #133):** adotar a escala **monotônica** (estritamente decrescente)
`A1=1.0, A2=0.85, A3=0.7, A4=0.55, B1=0.4, B2=0.3, SC=0.2` — um nível superior sempre pondera
mais que um inferior. Canonizada em **um único lugar de verdade** no código
(`backend/app/models/vehicle.py` → `RelevanceLevel` + `PESO_POR_NIVEL`), consumida por
`inference_repository`, `fixtures` e `seed_firestore`. Aplicada também em `data-model.md`,
specs 01 e 03, e nos casos RL05 dos testes. R1 deixa de ter pendência.

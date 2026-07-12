# Sessão de Grilling — Features e Bugs (2026-07-07)

> Log iterativo de perguntas e respostas. Atualizado a cada rodada.
> Contexto: lista de features novas e bugs levantada para o SAGA.

---

## Triagem inicial

A lista tem 17 itens. Nem todos são decisões de domínio — a maioria é bug de
implementação (conserta e pronto, sem grilling). Separação:

### Bugs de implementação (sem grilling — só correção)
| # | Item | Natureza |
|---|------|----------|
| 2 | Fechar modais no ESC | UX |
| 3 | Progresso e status na aba de alunos | Exibição/cálculo |
| 5 | Verificar por que está tão lento | Performance |
| 6 | Relatórios não está carregando | Bug |
| 9 | Cadastros pendentes não carrega | Bug |
| 10 | Definição do "tamanho do sistema" nas configurações | Config (termo a esclarecer) |
| 11 | Atividades creditáveis — erro `[object Object]` ao adicionar | Bug |
| 14 | Não recarregar a página ao aprovar produção/atividade | UX/estado |

### Itens de domínio (valem grilling — mexem no modelo/linguagem)
| # | Item | Por quê |
|---|------|---------|
| 12 | Coautoria em produções e atividades | Novo relacionamento no modelo; afeta RL05? |
| 13 | Definir veículo → nível numa tabela | Toca Veículo / Qualis / RL05 (+ conflito 7 vs 8 níveis) |
| 15 | Coordenador que também é orientador | Interage com ADR-0002; lacuna de representação |
| 16 | Excluir atividades aprovadas ou pendentes | Regra de negócio de exclusão |
| 17 | Proficiência e qualificação no checklist | Como avaliar; quem, quais estados |
| 8 | Solicitações | Escopo vago — precisa recortar |
| 1 | Exportação | Escopo vago — o quê, em que formato |
| 4 | Implementar detalhes do aluno | Escopo — o que entra na tela |
| 7 | Motor de inferência | Vago demais — precisa recorte |

---

## Perguntas e Respostas

### Item 15 — Coordenador que também é orientador

**Q1 — Como um coordenador-que-orienta passa a ser selecionável como orientador?**
Contexto: ADR-0002 já fixa papel único (`coordenacao` superset de `orientador`);
o problema não é papel novo, é onde ele aparece no dropdown (lê de `advisors`).

> **R:** Na prática todo coordenador orienta, mas **não é obrigatório**. A feature
> **não pode bugar a transferência de coordenação**.

Achados no código:
- `coordination_transfer_service._ensure_initiator_advisor` **já** cria um `advisors`
  doc (idempotente, keyed no `uid`) quando um coordenador cai para orientador →
  "ter doc em `advisors`" já é ortogonal ao `role`.
- A transferência valida sucessor como `orientador` puro e exige coordenação única;
  adicionar `advisors` doc a um coordenador não toca essas guardas.

**Q1b — Advisors-doc garantido vs união no dropdown; ele se ver na tela de gestão?**

> **R:** **Advisors-doc garantido** para todo coordenador. É aceitável ele se ver na
> tela de orientadores, **desde que não consiga se autogerenciar** (editar/excluir o
> próprio registro com os privilégios de coordenação, como faz com os outros).

**Decisões:**
- Todo usuário `coordenacao` do programa ganha um registro em `advisors` (reusar/
  extrair o helper de `_ensure_initiator_advisor`); `list_advisors` já o inclui, sem
  alterar o dropdown.
- Transferência de coordenação permanece intocada (só reusa o doc, idempotente).
- **Regra nova:** bloquear auto-gestão — a coordenação não pode `update`/`delete` o
  próprio `advisors` doc pela tela de gestão de orientadores.
- CONTEXT.md atualizado (entidade Orientador: orientar é ortogonal ao papel).

---

### Item 12 — Coautoria em produções e atividades

**Q2 — "Coautoria em atividades" significa (a) o lado-atividade da produção ou (b)
atividade creditável standalone?**
Achado: `ProductionCreate.autores` já aceita uids + strings livres; cada uid ganha uma
`activity` dedicada → coautoria em **produção já existe** no backend, falta UI.

> **R:** **(b)** — quer coautoria em atividade creditável standalone também.

**Q3 — Alocação de créditos entre co-autores: crédito cheio (A) ou rateado (B)?**

> **R:** **(A) crédito cheio para cada co-autor + validação individual por cópia.**

**Q4 — Cópias, consentimento e RL04.**

> **R:** **Sem consentimento** — orientador valida cada cópia; co-autor não precisa
> aceitar.

**Decisões:**
- Coautoria vale para **produção e atividade creditável**.
- Cada co-autor cadastrado recebe uma **cópia independente** em sua subcoleção
  `activities`, validada pelo próprio orientador; **crédito/pontuação cheios**, sem rateio.
- Autores não cadastrados = texto livre (informativo, sem crédito).
- **Sem passo de aceite** do co-autor.
- RL04 **intocada**: `nao_duplicata` é intra-aluno; cópias entre alunos **não** são
  duplicata e não devem ser deduplicadas.
- UI nova: seletor de co-autores (alunos cadastrados) + campo de autores externos, em
  produção **e** atividade.
- CONTEXT.md: novo termo **Coautoria**; ADR-0006 criado.

---

### Item 13 — Definir veículo → nível numa tabela

**Q5 — Fonte de verdade do nível: base do veículo ou por programa?**
Achados: escala real é **A1–A8 + SC** (não 7; memória corrigida). `vehicles/` guarda o
veículo; nível por programa em `programs/{id}/vehicle_levels/{veiculo_id}` (fonte da RL05).
Produção já tem `veiculo_id`; `ProductionResponse` já devolve nível/peso.

> **R:** **Nível por programa** é a fonte de verdade. **É só expor na UI** — sem gap de modelo.

**Decisões:**
- Modelo completo; item 13 = tarefa de **UI** (escolher veículo ao criar produção;
  mostrar nível/peso resolvidos por programa).
- `vehicles.nivel` = default de bootstrap; `vehicle_levels` por-programa manda.
- Índice do MEMORY.md corrigido ("7 níveis" → A1–A8 + SC).

---

### Item 17 — Proficiência e qualificação no checklist

**Q6 — Toggle da coordenação (A) ou fluxo de submissão com comprovante (B)?**
Achado: backend completo — checklist já modela ambos os requisitos (read-only); PATCH
`/students/{id}/qualificacao` e `/proficiencia` existem, `coordenacao`-only. Falta UI.

> **R:** **(A) toggle da coordenação, com comprovante opcional.**

**Decisões:**
- Expor no checklist/detalhe do aluno as ações de marcar qualificação e proficiência
  (`coordenacao`-only), usando os PATCH que já existem.
- Adicionar campo **`comprovante_url` opcional** em `QualificacaoRequest`/
  `ProficienciaRequest` (e refletir nos requisitos do checklist). **Sem** fluxo de
  submissão do aluno.
- bool + data continuam sendo o que alimenta RL01/RL03.

---

### Item 16 — Excluir atividades aprovadas ou pendentes

**Q7 — Quem exclui, em quais estados, efeito em créditos/motor, soft vs hard.**
Achado: `ActivityService` **não tem delete** hoje — feature nova. Excluir aprovada =
reverter aprovação + re-rodar motor.

> **R:** Concorda com a matriz; **hard delete + auditoria A02**.

**Decisões:**
| Estado | Quem exclui | Efeito |
|--------|-------------|--------|
| `rascunho`/`enviado` | dono (aluno) ou coordenação | hard delete simples |
| `aprovado` | **só coordenação** | reverte créditos + **re-roda motor** + A02 |
| `rejeitado` | coordenação | hard delete simples |

- Atividade com `producao_id` → **bloqueia** exclusão pela tela de atividade (remove-se
  excluindo a produção).
- Coautoria: delete é **por-cópia**; não afeta cópias de outros co-autores.
- **Hard delete** do doc + rastro só em `audit_logs` (A02). Sem soft delete/tombstone.
- **ADR-0007** criado — hard delete de aprovada não é imutável (decisão do usuário: "quero").

---

### Itens vagos — recorte de escopo (Q8 múltipla)

**Item 1 — Exportação.** Escopo: relatórios/dashboard em **PDF**, listas em **CSV/Excel**,
checklist do aluno em **PDF**, E **cada gráfico** dos dashboards dos 3 tipos de conta
(aluno, orientador, coordenação) com opção de exportar. → Verificar todas as informações
dos 3 dashboards. Implementação; sem decisão de domínio.

**Q9 — Formato de export por gráfico.**
> **R:** Hoje há **PDF, Excel, CSV**; **adicionar PNG** e implementar **as quatro** em
> cada gráfico.

**Item 4 — Detalhes do aluno.** A página **já existe** (acesso: perfil do orientador →
trocar exibição para **cards** → clicar no nome do aluno), mas **nada funciona nela**.
= bug de wiring (provavelmente ainda em dados mockados) + caminho de acesso ruim.
Escopo: ligar a página aos endpoints reais e melhorar o acesso. Implementação.

**Item 7 — Motor de inferência (frontend).** Expor o resultado na UI + **correções
visuais** + **remover dados mockados** da página. Implementação/bug; o motor backend
está ok. Não confundir com editar regras (RL01–RL05).

**Item 8 — Solicitações.** Implementar a **lista unificada** (modelo já existe no CONTEXT).
Ver Q8 abaixo para a decisão de "decidir na lista vs redirecionar".

**Q8 — Decidir na lista unificada ou redirecionar por subtipo?**

> **R:** **Inbox unificado; decisão em-linha só para os subtipos de formulário.**

**Decisões (item 8):**
- Lista unificada = **inbox de triagem** (visibilidade + filtro + status de todos os
  subtipos num lugar).
- **Decisão em-linha** só para prorrogação, trancamento e transferência de orientando.
- **Deep-link** para a tela existente nos subtipos de efeito pesado: validação de
  atividade/produção (crédito + motor) e transferência de coordenação (aceite do sucessor).
- Não reimplementar as regras de validação/transferência num segundo lugar.

---

### Item 10 — "Tamanho do sistema" nas configurações

**Q9 — O que é esse termo?** (a) aparência/fonte, (b) nome do sistema, (c) limite acadêmico?

> **R:** **(a)** — tamanho de fonte / escala da UI. Bug de config de UI, sem domínio.

---

## Síntese e tema transversal

**Tema recorrente (raiz comum):** vários itens não são bugs independentes — são a mesma
causa: **páginas do frontend ainda em dados mockados / não ligadas ao backend** (ver
`docs/specs/10_integracao_frontend.json`). Provável cluster de mesma raiz:
- #4 detalhes do aluno ("nada funciona"), #7 motor (remover mock), #6 relatórios não
  carregam, #9 cadastros pendentes não carregam, possivelmente #3 (progresso/status) e
  #5 (lentidão, se for N+1 de chamadas mal ligadas).
- **Recomendação:** atacar o wiring frontend↔backend como uma frente única antes de
  tratar cada "não carrega" isolado.

**Classificação final dos 17 itens:**

| # | Item | Resolução |
|---|------|-----------|
| 1 | Exportação | Escopo definido (PDF relatórios/checklist, CSV listas, export por gráfico nos 3 dashboards). Implementação. Q9-formato por gráfico em aberto. |
| 2 | Fechar modais no ESC | Bug UX puro. |
| 3 | Progresso/status na aba de alunos | Bug (provável cluster de wiring). |
| 4 | Detalhes do aluno | Página existe, não ligada — bug de wiring + acesso. |
| 5 | Lentidão | Perf; investigar N+1 de listagens (`list_all` repetidos nos services). |
| 6 | Relatórios não carrega | Bug (cluster de wiring). |
| 7 | Motor de inferência (UI) | Expor resultado + visual + remover mock. Backend ok. |
| 8 | Solicitações | **Decidido:** inbox unificado; decisão em-linha só p/ formulário. |
| 9 | Cadastros pendentes não carrega | Bug (cluster de wiring). |
| 10 | "Tamanho do sistema" | (a) fonte/escala UI. Bug de config. |
| 11 | Atividade `[object Object]` | Bug (erro serializado errado; atividade grava mas resposta/erro mal tratado). |
| 12 | Coautoria | **Decidido:** cópias independentes, crédito cheio, sem aceite. CONTEXT + ADR-0006. |
| 13 | Veículo → nível | **Decidido:** nível por programa; só expor na UI. Memória corrigida (A1–A8+SC). |
| 14 | Não recarregar ao aprovar | Bug de estado (atualizar em memória em vez de reload). |
| 15 | Coordenador que orienta | **Decidido:** advisors-doc garantido; sem auto-gestão. CONTEXT atualizado. |
| 16 | Excluir atividades | **Decidido:** matriz por estado; hard delete + A02. |
| 17 | Proficiência/qualificação no checklist | **Decidido:** toggle coordenação + comprovante opcional. |

**Artefatos atualizados nesta sessão:**
- `CONTEXT.md` — entidade Orientador (ortogonal ao papel); novo termo **Coautoria**;
  refs em Atividade Creditável e Produção Bibliográfica.
- `docs/adr/0006-coautoria-copias-independentes-credito-cheio.md` — criado.
- `MEMORY.md` (índice) — Qualis "7 níveis" → A1–A8 + SC.

**Pontas soltas — RESOLVIDAS:**
- **Q9** — export por gráfico: **PDF + Excel + CSV + PNG** (as quatro).
- **Item 16** — hard-delete-de-aprovada promovido a **ADR-0007**.

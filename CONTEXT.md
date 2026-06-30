# CONTEXT.md — Modelo de Domínio

> Linguagem ubíqua e modelo de domínio do SAGA.
> Lido pelas agent skills (`tdd`, `diagnose`, `improve-codebase-architecture`) para entender vocabulário e regras de negócio.
> Para instruções de desenvolvimento (comandos, convenções, workflow), ver [`CLAUDE.md`](./CLAUDE.md).

---

## Visão Geral

Sistema de acompanhamento acadêmico para programas de **mestrado**. Gerencia o ciclo completo do discente — cadastro, plano de trabalho, validação de créditos, checklist de integralização, prorrogações e relatórios gerenciais.

Dois paradigmas centrais determinam como o sistema raciocina e como ele se comporta:

- **Motor lógico** — decide o que é verdade no sistema: aptidão à defesa, situação acadêmica, elegibilidade de créditos. Expressado como regras declarativas; mudar uma política = editar a regra, não reescrever código.
- **Aspectos transversais** — definem como cada operação é enriquecida: autorização, auditoria, histórico, alertas. A lógica de negócio não os conhece.

---


### Regras Gerais

- Nunca abra PR sem ter o `.claude/current-issue` preenchido — o hook não saberá qual issue mover.
- O arquivo `.claude/current-issue` é ignorado pelo git (listado no `.gitignore`).
- Se a issue não estiver vinculada ao projeto #4, o hook avisará mas não falhará.

## Entidades do Domínio

### Discente
Aluno de mestrado vinculado a um programa e a um orientador. Possui matrícula, prazo de conclusão, comprovação de proficiência em língua estrangeira e aprovação na qualificação.

A situação acadêmica é dupla:
- **Situação registrada** — atualizada manualmente pela coordenação
- **Situação inferida** — calculada em tempo real pelo motor lógico a partir dos fatos do discente

Quando as duas divergem, o sistema sinaliza conflito.

### Orientador
Docente responsável por orientar discentes. Cria e mantém o plano de trabalho, emite pareceres em atividades e produções, e aprova etapas de progresso.

### Coordenação
Papel administrativo do programa. Realiza CRUD completo, valida atividades e produções em segunda instância, configura tipos de atividade e veículos, e emite relatórios gerenciais.

### Programa
Programa de pós-graduação. Agrupa discentes e orientadores e define as regras de crédito vigentes (mínimos e máximos por grupo de atividade).

### Plano de Trabalho
Estrutura do percurso acadêmico do discente, dividida em **etapas** (`stages`) e **tasks**. Cada task tem prazo, status e prioridade. O discente registra atualizações de progresso; o orientador cria e mantém a estrutura. Plano concluído é condição necessária para aptidão à defesa (RL01).

### Atividade Creditável
Atividade que gera créditos para o discente (disciplinas cursadas, participações em eventos, publicações técnicas). Organizada por **categoria**:

| Categoria | Limite |
|-----------|--------|
| Básico | Mínimo de 12 créditos |
| Específico | Mínimo de 8 créditos |
| Tecnológico | Máximo de 4 créditos |
| Total | Mínimo de 24 créditos |

Fluxo de validação: discente submete → orientador emite parecer → coordenação valida. Elegibilidade verificada pela RL04.

### Produção Bibliográfica
Publicação científica associada ao discente. Associada a um **veículo** (fator de pontuação configurado pela coordenação). A pontuação ponderada é calculada pela RL05. Pelo menos uma produção validada é condição para aptidão à defesa.

### Solicitação
Pedido formal que requer decisão da coordenação, consolidado numa lista única para revisão. Distingue-se pela **origem**:

- **Criada pelo formulário "Nova Solicitação"** (aluno ou orientador preenche, status inicia `pendente`): _prorrogação_ (de defesa ou de qualificação), _trancamento de matrícula_ e _transferência de orientando_.
- **Iniciada em outro fluxo e apenas agregada** na lista: _validação_ de atividade creditável ou produção bibliográfica (nasce da submissão do discente) e _transferência de coordenação_ (iniciada na lista de orientadores, ver US-SO02).

_Avoid_: transferência (é apenas um subtipo de solicitação).

### Prorrogação
Extensão de prazo concedida ao discente. Muda o estado para "Em Prorrogação" e recalcula o prazo final. Registrada pela coordenação ou orientador. É o subtipo mais comum de [Solicitação](#solicitação).

### Veículo
Publicação ou evento científico classificado em um **nível Qualis** (`A1`–`A8`, ou _fallback_ quando não classificado). Usado pela RL05 para ponderar o score de produções bibliográficas.

### Peso Qualis
Fator de ponderação de cada nível Qualis, definido **por programa** por cada coordenador. Mantido em coleção **versionada**: cada conjunto de pesos carrega `vigente_desde`, `alterado_por` e `alterado_em` — a coleção é o próprio histórico de mudanças. A RL05 aplica o peso **vigente na data de publicação** da produção; produção não publicada usa o peso vigente atual (provisório) até publicar. Ver [ADR-0003](./docs/adr/0003-pesos-qualis-versionados-por-programa.md).

### Índice de Produção
Soma ponderada dos `score` (RL05) de todas as produções bibliográficas **validadas**, sem filtro de estrato. Por aluno é a soma direta. Por orientador existe em duas formas selecionáveis: **soma total** (volume absoluto dos orientandos) e **média por orientando** (produtividade normalizada para comparação). Calculado no service layer, não no motor. _Avoid_: índice restrito.

---

## Ciclo de Vida do Discente

| Status | Descrição |
|--------|-----------|
| 🟢 Regular | Dentro do prazo, plano em dia |
| 🔄 Em Prorrogação | Semestre adicional concedido e em curso |
| 🔴 Em Risco | Pendências ou prazos estourados |
| ✅ Qualificado | Aprovado na qualificação |
| 📝 Em Fase de Defesa | Apto à defesa e com a defesa encaminhada |
| 🎓 Concluído | Integralizou o curso e defendeu |
| ❌ Desligado | Removido do programa |

---

## Papéis e Permissões

| Papel | Permissões principais |
|-------|----------------------|
| `adm` | Superusuário técnico/institucional global; cria/edita/desativa coordenadores em qualquer programa. Fora de todo programa acadêmico |
| `coordenacao` | CRUD completo, validação final, relatórios, configurações |
| `orientador` | Leitura de orientandos, criar plano/tasks, emitir pareceres |
| `aluno` | Próprios dados, registrar atividades/produções/progresso |

Papéis são armazenados como custom claims `{ role, programa_id }` no JWT do Firebase Auth. O papel `adm` é global: seu `programa_id` é `null` (não pertence a nenhum programa), e a gestão de coordenadores é cross-programa. Pode haver mais de um `adm`. Coordenadores **não** criam coordenadores — apenas transferem a própria coordenação (hand-off: o coordenador anterior passa a `orientador`).

Os valores canônicos de `role` são exatamente `adm`, `coordenacao`, `orientador` e `aluno` — usados em claims, `@requires_role` e seeds.
- `coordenacao` — _Avoid_: coordenador
- `aluno` — _Avoid_: discente

A prosa das histórias de usuário pode dizer "coordenador" ou "discente"; identificadores (claims, decoradores, enums) usam sempre o termo canônico.

---

## Regras Acadêmicas (Motor de Inferência)

Regras declarativas — alterar uma política acadêmica significa editar o arquivo da regra, nunca o fluxo de código. Ver detalhes de implementação em [`docs/specs/01_motor_inferencia.json`](./docs/specs/01_motor_inferencia.json).

| ID | Arquivo | Regra | Condição em linguagem de domínio |
|----|---------|-------|----------------------------------|
| RL01 | `defense_eligibility.py` | Aptidão à defesa | **Todas** as 5 condições: créditos mínimos atingidos + proficiência comprovada + qualificação aprovada + produção validada + plano concluído |
| RL02 | `credit_validation.py` | Créditos por grupo | Respeitar mínimos/máximo por categoria (básico ≥12, específico ≥8, tecnológico ≤4, total ≥24) |
| RL03 | `academic_status.py` | Em risco | **Qualquer** das 4 condições: prazo estourado OU créditos insuficientes OU qualificação pendente OU plano atrasado |
| RL04 | `activity_eligibility.py` | Elegibilidade de atividade | Tipo de atividade ativo + dentro do período de validade + sem duplicata no mesmo período |
| RL05 | `production_scoring.py` | Pontuação de produção | `score = pontuação_base × peso_qualis`, com o peso vigente na data de publicação (ver [Peso Qualis](#peso-qualis)) |

---

## Comportamentos Transversais (Aspectos)

Preocupações que cruzam todos os módulos sem aparecer na lógica de negócio. Ver mecanismos de implementação em [`docs/specs/02_aspectos_aop.json`](./docs/specs/02_aspectos_aop.json).

| ID | Arquivo | Comportamento | Quando atua |
|----|---------|--------------|-------------|
| A01 | `authorization.py` | Autorização por papel | Antes de qualquer endpoint — bloqueia roles não autorizados |
| A02 | `audit.py` | Auditoria de operações | Em torno de mutações — registra autor, ação e timestamp em `audit_logs` |
| A03 | `history.py` | Histórico de mudanças | Antes e após updates — persiste snapshot anterior em `history` |
| A04 | `deadline_validation.py` | Validação de prazos | Antes e após operações — recalcula situação de prazo antes de qualquer inferência |
| A05 | `alerts.py` | Emissão de alertas | Após mudanças de estado — dispara notificações em `notifications` |

---

## Modelo de Dados (Coleções Firestore)

| Coleção | Entidade de domínio | Notas |
|---------|---------------------|-------|
| `users` | Usuários autenticados | Custom claims definem papel e programa |
| `students` | Discentes | Sub-coleções: `work_plan`, `activities`, `productions`, `extensions`, `inferred_status`, `history` |
| `advisors` | Orientadores | Vinculados a `students` por `orientador_id` |
| `programs` | Programas | Definem regras de crédito vigentes |
| `activity_types` | Tipos de atividade | Categorias, limites e pontuação por programa |
| `vehicles` | Veículos bibliográficos | Fator de pontuação por veículo |
| `audit_logs` | Log de auditoria | Escrito pelo aspecto A02 |
| `notifications` | Alertas | Lidos em tempo real pelo frontend via `onSnapshot` |
| `invites` | Convites de acesso | Fluxo de cadastro por convite |

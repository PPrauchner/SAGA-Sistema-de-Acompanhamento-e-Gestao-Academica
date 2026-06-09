# PRD — SAGA: Sistema de Acompanhamento e Gestão Acadêmica

> Documento de Requisitos de Produto. É o **norte** acima das especificações técnicas em [`docs/specs/`](./specs/) — descreve o *o quê* e o *porquê*; os specs descrevem o *como*.
> Para o modelo de domínio, ver [`CONTEXT.md`](../CONTEXT.md). Para instruções de desenvolvimento, ver [`CLAUDE.md`](../CLAUDE.md).

| Campo | Valor |
|-------|-------|
| Produto | SAGA — produto real para um Programa de Pós-Graduação (PPG) |
| Escopo do MVP | Single-tenant (`prog_default`), **somente mestrado** |
| Usuário primário | Coordenação (≈70% do valor) |
| Usuário secundário | Aluno (≈30% do valor) · Orientador (apoio) |
| Release | 1 release (MVP) — alvo **13/07/2026** + marcos semanais internos |
| Equipe | 6 integrantes |
| Status | Em construção (motor lógico de pé; aspectos, services, routers e integração frontend pendentes) |

---

## Problem Statement

A coordenação de um programa de mestrado acompanha dezenas de discentes ao longo de ~24 meses, e hoje faz isso **manualmente** — planilhas, e-mails e documentos avulsos. As regras que determinam se um aluno está regular, em risco, apto à defesa ou se já integralizou os créditos são **numerosas, mudam com o tempo e se cruzam entre vários módulos** (créditos por grupo, proficiência, qualificação, produção bibliográfica, plano de trabalho, prazos, prorrogações).

Disso decorrem duas dores concretas:

1. **A coordenação não tem visibilidade em tempo real.** A situação acadêmica de cada aluno precisa ser apurada à mão, requisito por requisito. Alunos derivam para o risco e prazos estouram sem que ninguém seja avisado a tempo. Não há uma fonte única e confiável que diga "estes são os alunos em risco, e por quê".

2. **O aluno não tem clareza do que falta para integralizar.** Ele depende de perguntar à coordenação ou ao orientador para saber quais requisitos já cumpriu, quais estão pendentes e quais estão em risco — e essa resposta é trabalhosa de produzir e frequentemente desatualizada.

Como agravante, quando a situação **registrada** manualmente diverge da situação **real** (inferível a partir dos fatos cadastrados), ninguém percebe o conflito — a decisão administrativa fica baseada em dado defasado.

## Solution

O SAGA centraliza o acompanhamento acadêmico e transforma os fatos cadastrados (créditos, atividades validadas, qualificação, proficiência, progresso do plano, prazos) em **conclusões acadêmicas calculadas em tempo real** por um motor de inferência lógico.

Do ponto de vista do usuário, o produto entrega:

- **Para a coordenação:** uma visão única e sempre atualizada do programa — quem está em risco e por quê, quem está apto à defesa, distribuição por situação e por orientador, tempo médio de integralização, produção por aluno/orientador — além de **alertas automáticos** quando prazos ficam críticos e da **detecção de conflito** entre a situação registrada e a inferida.
- **Para o aluno:** um **checklist de integralização vivo** que, a qualquer momento e sem precisar perguntar a ninguém, mostra cada requisito como *cumprido*, *pendente* ou *em risco*, com os valores reais (créditos obtidos vs. mínimo, datas, etc.) e a sua situação acadêmica inferida.
- **Para o orientador:** acompanhamento dos próprios orientandos, criação e manutenção do plano de trabalho, e emissão de pareceres no fluxo de validação de atividades.

O diferencial-manchete é a **situação acadêmica inferida em tempo real** + **detecção de conflito (registrada ≠ inferida)** + **checklist vivo**. As políticas acadêmicas são expressas como **regras declarativas configuráveis**: mudar uma política significa editar a regra, não reescrever o sistema. As preocupações transversais (autorização, auditoria, histórico, validação de prazos, alertas) são aplicadas como **aspectos**, mantendo a lógica de negócio limpa e cada uma podendo ser ligada/desligada sem tocar no código de negócio.

## User Stories

### Autenticação e acesso

1. Como **coordenação**, quero convidar um novo usuário por e-mail/token, para que ele crie a própria senha e ative a conta sem eu manipular credenciais.
2. Como **usuário convidado**, quero definir minha senha no primeiro acesso a partir de um token, para que minha conta seja ativada com o papel correto.
3. Como **usuário**, quero fazer login com e-mail e senha e ser levado à área correspondente ao meu papel, para que eu veja apenas o que me diz respeito.
4. Como **usuário**, quero recuperar minha senha, para que eu reentre no sistema se a esquecer.
5. Como **usuário autenticado**, quero que meu papel (`aluno`/`orientador`/`coordenacao`) seja reconhecido automaticamente, para que minhas permissões sejam aplicadas sem eu escolher papel manualmente.

### Gestão de discentes e orientadores (coordenação)

6. Como **coordenação**, quero cadastrar, editar e remover alunos, para manter o registro dos discentes do programa.
7. Como **coordenação**, quero cadastrar orientadores e ver quantos orientandos ativos cada um tem, para equilibrar a distribuição de orientações.
8. Como **coordenação**, quero associar cada aluno a um orientador, para organizar a responsabilidade de acompanhamento.
9. Como **coordenação**, quero registrar manualmente a aprovação na qualificação de um aluno, para que esse fato alimente as inferências do motor.
10. Como **coordenação**, quero registrar a comprovação de proficiência em língua estrangeira, para que conte como requisito de integralização.
11. Como **coordenação**, quero ajustar manualmente a situação registrada de um aluno (ex.: concluído, desligado), para refletir decisões administrativas que o motor não infere.
12. Como **orientador**, quero ver apenas os meus orientandos, para focar em quem é da minha responsabilidade.

### Plano de trabalho (orientador + aluno)

13. Como **orientador**, quero criar o plano de trabalho de um orientando dividido em etapas, para estruturar o percurso acadêmico dele.
14. Como **orientador**, quero adicionar tasks com prazo e prioridade a cada etapa, para detalhar o que precisa ser feito.
15. Como **orientador**, quero atualizar o status de uma task, para refletir o andamento real.
16. Como **aluno**, quero registrar atualizações de progresso vinculadas às minhas tasks, para mostrar o andamento do meu trabalho.
17. Como **aluno**, quero ver meu plano completo com etapas, tasks e progresso, para entender o que falta.
18. Como **orientador**, quero ser notificado quando meu orientando registra progresso, para acompanhar sem precisar checar manualmente.

### Atividades creditáveis e produções

19. Como **coordenação**, quero cadastrar tipos de atividade creditável com categoria, pontuação e limites, para definir como cada atividade gera créditos.
20. Como **coordenação**, quero ativar/desativar e editar tipos de atividade, para refletir mudanças de política — preservando o histórico das versões anteriores.
21. Como **aluno**, quero registrar uma atividade creditável com **upload do comprovante**, para que ela seja validada e contabilizada nos meus créditos.
22. Como **aluno**, quero registrar uma produção bibliográfica indicando o veículo e uma observação, para que a relevância do veículo seja considerada na pontuação.
23. Como **aluno**, quero ver a pontuação calculada da minha produção (ponderada pelo nível do veículo), para entender seu peso.
24. Como **orientador**, quero emitir parecer sobre uma atividade submetida pelo meu orientando, para orientar a decisão da coordenação.
25. Como **coordenação**, quero aprovar ou rejeitar atividades em segunda instância, para controlar a contabilização de créditos.
26. Como **aluno**, quero ser notificado quando minha atividade é aprovada ou rejeitada, para agir conforme o resultado.
27. Como **coordenação**, quero cadastrar veículos e configurar seu nível de relevância por programa, para que a pontuação reflita as regras do meu PPG.
28. Como **orientador**, quero ser notificado quando um orientando submete uma atividade para validação, para emitir parecer a tempo.

### Checklist de integralização e situação acadêmica (motor lógico)

29. Como **aluno**, quero consultar meu checklist de integralização com cada requisito marcado como cumprido/pendente/em risco, para saber exatamente o que falta sem perguntar a ninguém.
30. Como **aluno**, quero ver minha situação acadêmica inferida (regular, em risco, qualificado, em fase de defesa), para entender meu estado atual.
31. Como **coordenação/orientador**, quero ver se um aluno está apto à defesa segundo as 5 condições (créditos, proficiência, qualificação, produção validada, plano concluído), para encaminhar a defesa com segurança.
32. Como **coordenação**, quero que o sistema sinalize um **conflito** quando a situação registrada diverge da inferida, para corrigir o dado defasado.
33. Como **coordenação/orientador**, quero ver os fatos e conclusões usados pelo motor para um aluno, para auditar *por que* aquela situação foi inferida.
34. Como **coordenação**, quero que a validação de créditos respeite mínimos e máximos por grupo (básico ≥12, específico ≥8, tecnológico ≤4, total ≥24), para aplicar a regra do programa de forma consistente.

### Prorrogações

35. Como **aluno**, quero solicitar uma prorrogação de prazo com justificativa e plano atualizado, para estender meu prazo quando necessário.
36. Como **orientador**, quero emitir parecer sobre a solicitação de prorrogação do meu orientando, para subsidiar a decisão.
37. Como **coordenação**, quero aprovar ou rejeitar prorrogações, recalculando o prazo final do aluno quando aprovada, para manter os prazos corretos.
38. Como **aluno**, quero ser notificado do resultado da minha prorrogação e do novo prazo, para me planejar.

### Dashboards e relatórios

39. Como **aluno**, quero um dashboard com minha situação, progresso do plano, créditos e tasks próximas, para ter uma visão rápida do meu estado.
40. Como **orientador**, quero um dashboard com a visão agregada dos meus orientandos e alertas ativos, para priorizar atenção.
41. Como **coordenação**, quero um dashboard macro do programa (alunos por situação, atividades aguardando validação, prorrogações pendentes, tempo médio de integralização), para gerir o programa.
42. Como **coordenação**, quero um relatório de alunos em risco com as razões do risco, para agir preventivamente.
43. Como **coordenação**, quero relatórios de alunos por situação e por orientador, para enxergar a distribuição do programa.
44. Como **coordenação**, quero o relatório de tempo médio de integralização, para avaliar a eficiência do programa.
45. Como **coordenação**, quero o relatório de produção por aluno e por orientador, para acompanhar a produção científica.

### Auditoria, histórico e alertas (transversais)

46. Como **coordenação**, quero um log de auditoria de quem fez qual operação, quando e em qual entidade, para rastrear alterações sensíveis.
47. Como **coordenação**, quero filtrar e paginar os logs de auditoria por operação, usuário e data, para investigar eventos específicos.
48. Como **coordenação**, quero que alterações em entidades versionáveis (plano, tipo de atividade, situação registrada) preservem o estado anterior, para evidenciar a evolução das regras institucionais.
49. Como **usuário**, quero receber alertas em tempo real (in-app) de pendências, prazos e resultados de validação, para agir a tempo.
50. Como **usuário**, quero marcar notificações como lidas, para gerenciar o que já tratei.
51. Como **administrador do sistema**, quero ligar/desligar individualmente cada preocupação transversal (autorização, auditoria, histórico, prazos, alertas), para testar e configurar o comportamento sem alterar a lógica de negócio.

### Configuração

52. Como **coordenação**, quero configurar os parâmetros do programa (créditos mínimos/máximos, nº de prorrogações, meses até qualificação), para que as regras do motor reflitam a política vigente.

## Implementation Decisions

### Posicionamento e escopo

- **Produto real single-tenant, somente mestrado.** Um único programa (`prog_default`). O enum `doutorado` presente no schema de `students` é **dívida técnica** a ignorar/remover no MVP — nenhuma regra de doutorado é implementada.
- **Guardrails fixos (restrições do enunciado, não-negociáveis):** o motor de inferência é construído **do zero em Python puro** (sem bibliotecas de programação lógica); os aspectos usam **exclusivamente mecanismos nativos do Python** (decoradores, metaclasses, descritores, `__init_subclass__`, `inspect`); stack **React + FastAPI + Firebase**.
- **Desvio consciente vs. specs:** o **upload real de comprovantes via Firebase Storage entra no MVP** (os specs tratavam `comprovante` como URL string e Storage como opcional). Os specs de atividades/produções e de schema deverão ser atualizados para refletir o bucket, as regras de acesso e o campo de URL gerado pelo upload.

### Arquitetura em camadas (backend)

- **API (`api/v1/`)** apenas recebe request → chama service → retorna response. Nenhuma lógica de negócio nos routers.
- **Services (`services/`)** concentram a lógica de negócio e são os **únicos consumidores do motor de inferência** (via `InferenceService`).
- **Repositories (`repositories/`)** acessam o Firestore; sem lógica de negócio.
- **Models (`models/`)** são schemas Pydantic de entrada/saída.
- **Escrita no Firestore exclusivamente pelo backend (Admin SDK).** O frontend só lê diretamente a coleção `notifications` via `onSnapshot`.

### Motor de inferência (paradigma lógico)

- **Completamente isolado:** sem imports de FastAPI, Firebase, Pydantic ou qualquer ORM. Apenas stdlib.
- **Ponto de entrada externo único:** `InferenceEngine.query(goal: Term) -> list[dict]`. O resto do sistema nunca acessa internos do motor.
- **Resolução direta por conjunção de condições, sem backtracking.** `em_risco` é modelado por múltiplas cláusulas afirmativas alternativas (OR implícito), **sem Negação como Falha**.
- **`InferenceService` é o único responsável por popular a `FactBase`** com dados do Firestore antes de cada consulta, incluindo os fatos derivados temporais (`prazo_estourado`, `prazo_qualificacao_proximo`, `plano_atrasado`).
- **Regras como módulos declarativos** (`rules/RL01–RL05`). Mudar uma política = editar o módulo da regra, nunca o fluxo de controle:
  - **RL01 — Aptidão à defesa:** conjunção das 5 condições (créditos válidos + proficiência + qualificação + produção bibliográfica validada + plano concluído).
  - **RL02 — Validação de créditos:** mínimos/máximo por grupo via comparações aritméticas tratadas como built-ins no resolver.
  - **RL03 — Situação acadêmica (em risco):** 4 cláusulas alternativas (prazo estourado · créditos insuficientes · qualificação pendente + prazo próximo · plano atrasado).
  - **RL04 — Elegibilidade de atividade:** dentro do período + comprovante + tipo ativo + não excede limite da categoria.
  - **RL05 — Pontuação de produção:** `score = pontuação_base × peso_do_nível_do_veículo`, com pesos configuráveis por programa.
- **Checklist e situação inferida são calculados sob demanda** — não são documentos estáticos. Cada execução persiste um snapshot imutável em `students/{id}/inferred_status/` e atualiza `students/{id}.situacao_inferida`. O **conflito** é `situacao_registrada != situacao_inferida`.

### Aspectos (paradigma orientado a aspectos)

- **5 aspectos**, cada um documentando no docstring: *Join Point*, *Advice* (Before/After/Around) e *Weaving*:
  - **A01 Autorização** — decorador `@requires_role(*roles)`, advice *Before*; valida o claim `role` do JWT (e propriedade, ex.: aluno só o próprio, orientador só orientandos).
  - **A02 Auditoria** — decorador `@audit_operation` + `inspect`, advice *Around*; persiste `audit_logs` com autor, operação, módulo, entrada, resultado e duração.
  - **A03 Histórico** — metaclasse `HistoryMeta`/`__init_subclass__` (com decorador `@track_history` como alternativa explícita válida no MVP), advice *Before+After*; persiste snapshot do estado anterior na sub-coleção `history/` da entidade.
  - **A04 Validação de prazos** — decorador `@check_deadlines`, advice *Before+After*; recalcula fatos de prazo e marca situação para atualização; delega alertas ao A05.
  - **A05 Alertas** — decorador `@trigger_alerts`, advice *After*; grava `notifications` consumidas em tempo real pelo frontend via `onSnapshot`.
- **Configurabilidade:** flags em `aspect_config.py` (`AUTHORIZATION_ENABLED`, `AUDIT_ENABLED`, `HISTORY_ENABLED`, `DEADLINE_VALIDATION_ENABLED`, `ALERTS_ENABLED`) ligam/desligam cada aspecto **sem alterar a lógica de negócio**.
- **Ordem canônica de decoradores** nos endpoints: `@requires_role` → `@audit_operation` → `@check_deadlines` → `@trigger_alerts`.
- **A lógica de negócio (services e routers) não contém** código de autorização, auditoria, histórico, validação de prazo ou alertas — tudo aplicado por aspectos.

### Autenticação

- **Firebase Auth** com custom claims `{ role, programa_id }` no JWT. Backend verifica o token com `verify_id_token` em cada request via dependency `get_current_user`.
- **Fluxo por convite:** coordenação cria convite (token UUID, TTL 48h) → usuário define senha no primeiro acesso → backend cria o usuário no Firebase Auth, seta claims e cria `users/{uid}`.
- O backend **nunca recebe senha** — autenticação de senha é responsabilidade do Firebase Auth (client-side).

### Modelo de dados (Firestore)

- Coleções principais: `programs` (config + `vehicle_levels`), `users`, `students` (sub-coleções `work_plan`/`stages`/`tasks`/`updates`, `activities`, `productions`, `extensions`, `inferred_status`, `history`), `advisors`, `activity_types`, `vehicles`, `audit_logs`, `notifications`, `invites`.
- Os **fatos de configuração do motor** (mínimos/máximo de créditos, pesos de relevância) vivem em `programs/prog_default` e são populados por `scripts/seed_firestore.py`.

### Integração frontend

- Substituir os dados hardcoded das 17 páginas por chamadas reais à API, **sem refatorar componentes visuais além do necessário**.
- Criar `src/api/` (um service por domínio), `lib/firebase.ts`, hook `useAuth()` (login/logout, `getIdToken`, busca `auth/me`) e hook `useNotifications()` (`onSnapshot`).
- **Correções de consistência obrigatórias:** alinhar a nomenclatura de status ao backend (ex.: `atencao`/`critico` → `em_risco`); substituir a **escala Qualis fixa** por `nivel_relevancia` carregado de `GET /vehicles`; exibir o **badge de conflito** quando registrada ≠ inferida.
- Guardas de rota por papel (`PrivateRoute`).

### Prioridade de entrega (MoSCoW)

- **Must-have (núcleo da demo, fim-a-fim):** Autenticação + Discentes (base); **Motor + Checklist + Inferência (RL01–RL05)** alimentando `ChecklistPage`/`InferencePage`; **Aspectos A01–A05 ativáveis**; **Atividades/Produções + fluxo de validação** (com upload via Storage). O **plano de trabalho mínimo** é Must na medida em que gera o fato `plano_concluido` consumido pela RL01.
- **Should-have:** kanban completo do plano de trabalho; prorrogações; dashboards por papel; relatórios gerenciais; página de auditoria com filtros/paginação; configurações.
- **Could-have:** polimentos de UI e visualizações adicionais.

### Release e marcos

- **1 release (MVP)** com alvo em **13/07/2026**, com marcos semanais internos no fluxo kanban (Backlog → Sprint Backlog → Em Progresso → Feito):
  - **M1 — Backend + motor conectado:** services/repositories reais, `InferenceService` populando a `FactBase`, endpoints de auth/discentes/checklist/inferência funcionais.
  - **M2 — Aspectos + CRUD:** A01–A05 implementados e ativáveis; fluxos de atividades/produções/validação; upload via Storage.
  - **M3 — Integração frontend + demo:** páginas ligadas à API, conflito e checklist vivos, dashboards/relatórios, ensaio da demonstração.

## Testing Decisions

**O que faz um bom teste aqui:** testar **comportamento externo**, não detalhes de implementação. Para o motor, a entrada são fatos e a saída é a conclusão (apto/risco/inapto/score) — nunca o estado interno do resolver. Para os aspectos, o que importa é o **efeito observável** (log gravado, role rejeitado, snapshot criado, notificação emitida), não como o decorador o produz. Cada uma das 5 regras deve cobrir os cenários **apto / em risco / inapto**, e o resultado deve mudar conforme os fatos.

**Seams de teste (do mais alto/existente para o mais novo):**

1. **Motor de inferência — seam existente e preferencial:** `InferenceEngine.query(goal)` exercitado por **pytest** em `backend/inference_engine/tests/`. É o ponto de entrada público único; testa-se cada regra (RL01–RL05) montando uma `FactBase` mínima e asserindo a conclusão, seguindo os casos de teste já descritos no spec `01_motor_inferencia.json`. *Prior art:* `test_resolver.py`, `test_unification.py`, `test_substitution.py`, `test_terms.py`, `test_rules.py` já presentes.
2. **Aspectos — seam na fronteira do decorador:** aplicar cada aspecto sobre uma **função-dummy** com um **repositório fake** e asserir o efeito (auditoria persiste um registro; `@requires_role` levanta 403 para papel incorreto; `@track_history` grava o estado anterior; `@trigger_alerts` cria uma notificação). Alternar as flags de `aspect_config.py` para validar o **liga/desliga** sem alterar a função de negócio.
3. **Services e API — seam de contrato:** **FastAPI `TestClient`** com **repositories mockados** (ou emulador do Firestore), asserindo o contrato de resposta e os códigos HTTP dos endpoints, com `get_current_user` substituído por uma dependência de teste por papel.

**Módulos testados:** `inference_engine/` (todas as regras + unificação/substituição/resolver), `app/aspects/` (os 5 aspectos + configurabilidade), e os fluxos críticos de `app/services/` + `app/api/v1/` (auth, discentes, atividades/validação, checklist/inferência, prorrogações).

## Out of Scope

Itens explicitamente **fora** do MVP (candidatos a versões futuras):

- **Fluxo funcional de coorientador.** O campo `coorientador_id` existe, mas sem permissões, pareceres ou ações próprias.
- **Envio real de e-mail.** Convites retornam o token na resposta (para testes) e alertas vivem apenas in-app via `onSnapshot`; não há disparo de e-mail/SMTP nem notificação por push.
- **Integrações externas.** Sem Lattes, SIGAA, ORCID ou importação de dados institucionais.
- **Doutorado.** Apenas mestrado; o enum `doutorado` é dívida técnica a ignorar/remover.
- **Multi-programa / multi-institução.** Sistema single-tenant (`prog_default`); isolamento por tenant fica fora.
- **Piloto com usuários reais e métricas de adoção medidas.** Não há piloto previsto na janela do MVP; os KPIs de negócio são alvos de visão (ver *Further Notes*), não metas verificadas na entrega.

## Further Notes

### Métricas de sucesso (duas camadas)

**Camada 1 — KPIs-alvo de visão (aspiracionais; orientam o produto, não verificados no MVP):**

- Apuração da situação acadêmica de um aluno deixa de levar **horas/dias** (manual) e passa a ser **instantânea**.
- **100% dos alunos em situação de risco** são sinalizados pelo sistema **antes** do prazo estourar.
- O aluno descobre o que falta para integralizar **sem precisar perguntar** à coordenação/orientador (checklist self-service).
- A coordenação enxerga e resolve **conflitos** entre situação registrada e inferida assim que surgem.

**Camada 2 — Critérios de aceite verificáveis no MVP (demonstráveis na entrega):**

- O motor responde corretamente **apto/em risco/inapto** para cada regra (RL01–RL05) nos cenários de teste.
- O **checklist exibido coincide** com os fatos cadastrados do aluno (créditos, proficiência, qualificação, produção, plano).
- Os **5 aspectos** interceptam as operações previstas e podem ser **ligados/desligados** via `aspect_config.py` sem alterar a lógica de negócio.
- A **situação inferida** é recalculada a cada consulta e o **conflito** com a registrada é sinalizado na UI.
- O fluxo de **atividade fim-a-fim** (aluno submete com comprovante → orientador parecer → coordenação valida → fato alimenta o motor) funciona na demo.

### Contexto do projeto

- Projeto acadêmico da disciplina **Resolução de Problemas III** (UNIPAMPA, 2026), cujo propósito pedagógico é exercitar **Programação Lógica** e **Programação Orientada a Aspectos** de forma integrada — o domínio acadêmico é o veículo. Por isso os guardrails de paradigma são inegociáveis e tratados como requisitos de produto.
- **Equipe de 6 integrantes** (o `README.md` ainda lista 5 — atualizar a contagem).
- **Estado atual do build (referência para os marcos):** núcleo do motor de inferência implementado e com testes; **aspectos, services, routers e integração frontend ainda são o grosso do trabalho**; as 17 páginas React existem com dados hardcoded.
- **Relação com os specs:** este PRD fica **acima** dos 10 specs em `docs/specs/`. Onde houver divergência, vale o PRD; os specs afetados (notadamente upload via Storage e a contagem da equipe) devem ser atualizados.

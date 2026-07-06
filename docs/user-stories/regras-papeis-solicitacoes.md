# Histórias de Usuário — Papéis, Permissões e Solicitações

> Geradas a partir de feedback textual (2026-06-23).
> Cobre: validação de créditos, filtro de papel, autenticação, hierarquia de usuários, página de solicitações e transferência de coordenação.

---

## Créditos e Validação

### US-CR01 — Créditos só são computados após aprovação da coordenação

**Como** sistema,
**quero** computar créditos de uma atividade ou produção bibliográfica somente após aprovação explícita da coordenação,
**para que** o total de créditos do discente reflita apenas itens validados institucionalmente.

**Critérios de Aceitação:**
- Atividades e produções submetidas pelo discente e com parecer do orientador ficam no status `pendente_coordenacao` — créditos **não** são somados ao total do discente nesse estado.
- Somente após a coordenação marcar o item como `aprovado` os créditos são incluídos no cômputo (RL02 e RL05).
- Se a coordenação rejeitar o item, o discente é notificado e os créditos permanecem inalterados.
- O motor de inferência (RL02/RL04/RL05) nunca lê itens com status diferente de `aprovado` para fins de crédito.

---

## Papéis e Autenticação

### US-PA01 — Filtrar visão por papel em contas com múltiplos papéis

**Como** usuário com os papéis de orientador e coordenador simultaneamente,
**quero** aplicar um filtro de papel em todas as telas principais do sistema,
**para que** eu possa alternar entre a visão de coordenador e a visão de orientador sem precisar de contas separadas.

**Critérios de Aceitação:**
- Usuários com múltiplos papéis veem um seletor de contexto (ex.: "Visualizando como: Orientador | Coordenador") disponível em todas as telas relevantes.
- Ao selecionar "Orientador", o sistema filtra dados e ações para o escopo de orientador (apenas seus discentes, sem acesso a funções administrativas).
- Ao selecionar "Coordenador", o escopo completo do programa fica disponível.
- A preferência de contexto é mantida durante a sessão; ao relogar, volta ao papel padrão definido no token JWT.
- O filtro é aplicado no **frontend** com base nos `custom claims` do token — o backend valida o papel ativo em cada requisição.

---

### US-PA02 — Remover seleção de papel da página de login

**Como** sistema,
**quero** eliminar a escolha explícita de papel na tela de login,
**para que** o papel do usuário seja sempre determinado pelos `custom claims` do token JWT gerado pelo backend, sem possibilidade de adulteração pelo cliente.

**Critérios de Aceitação:**
- A página de login solicita apenas e-mail e senha (ou SSO).
- Após autenticação, o frontend lê os `custom claims` do token (`role`, `programa_id`) para definir a experiência do usuário — sem dropdown de papel.
- Qualquer requisição ao backend que declare um papel não presente nos `custom claims` retorna 403.
- Usuários com único papel são redirecionados diretamente para o dashboard correspondente.

---

### US-PA03 — Verificar e garantir implementação real dos papéis de coordenador e orientador

**Como** equipe de desenvolvimento,
**quero** auditar todas as rotas e componentes do sistema para confirmar que os papéis `coordenador` e `orientador` estão aplicados corretamente via aspecto A01 (`@requires_role`),
**para que** não existam endpoints ou telas acessíveis por papéis incorretos.

**Critérios de Aceitação:**
- Todos os endpoints de `api/v1/` possuem `@requires_role` declarado com os papéis corretos.
- Nenhuma rota de escrita (POST/PUT/DELETE) está acessível por `discente`.
- Testes de integração cobrem tentativas de acesso com papel incorreto (espera-se 403).
- Componentes de frontend ocultam ações não permitidas com base nos `custom claims` (não apenas por CSS, mas por condicional de renderização).

---

## Hierarquia de Usuários

### US-PA04 — Criar papel ADM (superusuário)

**Como** administrador do sistema (ADM),
**quero** ter um papel de superusuário separado dos papéis acadêmicos,
**para que** a gestão de coordenadores seja feita por um perfil técnico/institucional sem interferir nas operações do programa.

**Critérios de Aceitação:**
- Existe o papel `adm` nos `custom claims` do Firebase Auth.
- O ADM pode criar, editar e desativar contas de coordenadores.
- O ADM não aparece como participante de nenhum programa acadêmico e não tem acesso às operações de orientador ou discente.
- Pode haver mais de uma instância de ADM por implantação; a criação de novos ADMs é feita diretamente via script/backend, fora da interface.

---

### US-PA05 — Remover permissão de criação de coordenadores do papel coordenador

**Como** sistema,
**quero** que somente o ADM possa criar novos coordenadores,
**para que** a escalada de privilégios por coordenadores seja impossível.

**Critérios de Aceitação:**
- O endpoint de criação de coordenadores (`POST /users/coordenadores`) exige `@requires_role("adm")`.
- Coordenadores que tentarem acessar esse endpoint recebem 403.
- A opção de "Criar coordenador" é removida da interface para usuários com papel `coordenador`.
- Testes cobrem a tentativa de um coordenador criar outro coordenador (espera-se 403).

---

## Solicitações

### US-SO01 — Centralizar todas as solicitações em uma única página

**Como** coordenador ou orientador,
**quero** ter uma página unificada de "Solicitações" que consolide todos os tipos de pedidos existentes no sistema,
**para que** eu não precise navegar por múltiplas telas para gerenciar itens pendentes de revisão.

**Critérios de Aceitação:**
- A página "Solicitações" substitui a página "Transferências" e agrega, sem redundância, todos os tipos de solicitação do sistema, incluindo (mas não limitado a):
  - Validação de atividades creditáveis
  - Validação de produções bibliográficas
  - Prorrogações de prazo
  - Transferência de coordenação
  - Outros tipos identificados durante o levantamento de redundâncias
- Cada solicitação exibe: tipo, solicitante, data, status e ações disponíveis.
- É possível filtrar por tipo de solicitação, status e período.
- O número de solicitações pendentes é exibido como badge no menu de navegação.

---

### US-SO02 — Transferir coordenação para outro orientador

**Como** ADM ou coordenador atual,
**quero** selecionar um orientador na lista de orientadores do programa e transferir a ele o papel de coordenador,
**para que** a sucessão de coordenação seja feita de forma controlada e rastreada.

**Critérios de Aceitação:**
- Na lista de orientadores, existe a ação "Transferir coordenação" disponível para ADM (e para o coordenador atual, se a regra de negócio permitir).
- Ao confirmar a transferência:
  1. O orientador selecionado recebe o `custom claim` `role: coordenador` no Firebase Auth.
  2. O coordenador anterior mantém o papel de `orientador` (não é removido do programa).
  3. Um registro de auditoria é gerado (aspecto A02).
- A operação gera uma entrada na página de "Solicitações" com status `concluído` para rastreabilidade.
- A transferência é irreversível pela interface; para desfazê-la, é necessária ação do ADM.

---

## Notas de Implementação

- O novo papel `adm` deve ser adicionado ao enum de papéis em `core/` e ao aspecto A01 (`authorization.py`).
- A remoção da seleção de papel no login impacta o componente de login no frontend e o fluxo de redirecionamento pós-autenticação em `AppContext`.
- A página de "Solicitações" deve ser levantada como uma rota nova (`/solicitacoes`); a rota antiga de transferências deve redirecionar para ela.
- Antes de implementar US-SO01, mapear todos os fluxos existentes que geram itens pendentes para evitar duplicação de lógica.
- **US-CR01 — status `pendente_coordenacao`:** decisão atual é **implícita** — o enum `ActivityStatus` permanece `{rascunho, enviado, aprovado, rejeitado}`; "aguardando coordenação" é representado por `enviado` + `parecer_orientador` preenchido. A invariante de crédito (motor lê apenas `aprovado` via `get_approved_activities`/`get_approved_productions`) já está garantida. _Issue futura:_ avaliar introduzir o status explícito `pendente_coordenacao` no enum **se** a página de Solicitações (US-SO01) precisar do filtro de primeira classe "fila do orientador" vs "fila da coordenação"; envolve migração do enum, ajuste do fluxo de validação em duas etapas e dos testes.

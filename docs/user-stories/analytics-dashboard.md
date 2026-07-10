# Histórias de Usuário — Módulo de Analytics e Dashboard Comparativo

> Geradas a partir da sessão de feedback (áudio 2026-06-22).  
> Contexto: visualização de métricas de desempenho de docentes/orientadores e alunos, com filtros interativos e comparação entre pares.

---

## US-AN01 — Visualizar índice restrito de orientadores ao longo do tempo

**Como** coordenador,  
**quero** ver um gráfico de evolução temporal do índice restrito de cada orientador,  
**para que** eu possa acompanhar tendências de desempenho ao longo dos semestres.

**Critérios de Aceitação:**
- O gráfico exibe o índice restrito (pontuação ponderada das produções) por período para um ou mais orientadores selecionados.
- O eixo X representa o tempo (semestres/anos); o eixo Y representa o valor do índice.
- É possível alternar entre visualizar um único orientador ou múltiplos simultaneamente.

---

## US-AN02 — Comparar orientadores lado a lado

**Como** coordenador,  
**quero** selecionar múltiplos orientadores e ver uma comparação direta entre eles,  
**para que** eu possa identificar discrepâncias de produtividade e embasar decisões de gestão.

**Critérios de Aceitação:**
- Existe um seletor multi-valor que permite escolher 2 ou mais orientadores (ex.: Sílvio, Paulo, Bernardino).
- O gráfico comparativo exibe barras ou linhas side-by-side para os orientadores selecionados.
- Ao alterar a seleção, o gráfico atualiza sem recarregar a página.
- O seletor exibe o nome completo do orientador e suporta busca por texto.

---

## US-AN03 — Visualizar meu próprio desempenho como orientador

**Como** orientador,  
**quero** ver meu índice restrito e minha posição relativa em relação aos demais orientadores do programa,  
**para que** eu saiba se estou acima ou abaixo da média e possa tomar ações proativas.

**Critérios de Aceitação:**
- O orientador visualiza apenas seus próprios dados de índice (sem acesso a dados individuais de outros orientadores).
- É exibida uma referência de contexto (ex.: média do programa, faixa percentil) para situar o orientador.
- A tela não expõe nomes de colegas; apenas a posição relativa anônima.

---

## US-AN04 — Visualizar meu desempenho como aluno

**Como** discente,  
**quero** ver minha própria situação acadêmica e evolução de créditos no dashboard,  
**para que** eu possa acompanhar meu progresso sem depender da coordenação para obter informações.

**Critérios de Aceitação:**
- O discente acessa apenas seus próprios dados (créditos, produções, situação inferida).
- Não são exibidos dados de outros discentes nem dados internos do corpo docente.
- A visualização inclui: total de créditos validados por categoria, status do plano de trabalho e pontuação de produções bibliográficas.

---

## US-AN05 — Personalizar os dados exibidos no dashboard

**Como** usuário do sistema (coordenador, orientador ou discente),  
**quero** configurar quais métricas e filtros são exibidos no meu dashboard,  
**para que** eu veja apenas as informações relevantes ao meu contexto no momento.

**Critérios de Aceitação:**
- Existem menus/filtros selecionáveis para customizar a visualização (ex.: período, tipo de métrica, orientadores incluídos).
- As preferências de filtragem são mantidas durante a sessão.
- A interface exibe claramente quais filtros estão ativos.

---

## US-AN06 — Acesso diferenciado ao módulo de analytics por papel

**Como** sistema,  
**quero** controlar o escopo de dados visíveis conforme o papel do usuário autenticado,  
**para que** cada perfil acesse apenas as informações pertinentes à sua função.

**Critérios de Aceitação:**

| Papel | Acesso permitido |
|-------|-----------------|
| Coordenador | Todos os orientadores e discentes do programa; comparativos completos |
| Orientador | Próprio índice + posição relativa anônima no programa |
| Discente | Apenas os próprios dados acadêmicos |

- O controle de acesso é aplicado via aspecto A01 (`@requires_role`) — sem lógica de filtragem nos componentes de UI.
- Tentativa de acesso a dados fora do escopo retorna 403.

---

## Notas de Implementação

- As métricas de produção bibliográfica são calculadas pela **RL05** (`production_scoring.py`).
- O índice restrito referenciado no feedback corresponde à pontuação ponderada de produções validadas (campo calculado pelo motor de inferência).
- Os dados de comparação devem ser agregados no backend (service layer) — o frontend recebe apenas os valores prontos para renderização.
- Componentes de gráfico: usar biblioteca já adotada no projeto; garantir responsividade.

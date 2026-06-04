# 📚 Sistema de Acompanhamento Acadêmico da Pós-Graduação

## 🎯 Visão Geral

Programas de pós-graduação acompanham o progresso de discentes de mestrado ao longo de um plano de trabalho de aproximadamente **24 meses**, considerando tarefas, prazos, créditos, atividades creditáveis, prorrogações e requisitos de integralização. As regras que regem esse acompanhamento são numerosas, mudam com o tempo e atravessam vários módulos do sistema, o que torna o domínio adequado para exercitar dois paradigmas de forma combinada.

---

## 💡 Objetivo Principal

Desenvolver um **Sistema de Acompanhamento Acadêmico da Pós-Graduação** que combine:

### 1️⃣ Programação Lógica
- Motor de inferência construído do zero
- Responsável por decidir situações acadêmicas a partir de fatos cadastrados
- Exemplos: se um aluno está apto à defesa, em risco ou se seus créditos satisfazem os grupos obrigatórios

### 2️⃣ Programação Orientada a Aspectos
- Usando apenas recursos nativos do Python
- Trata preocupações transversais que se repetem em quase todas as operações
- Inclui: autorização, auditoria, histórico de alterações, validação de prazos e geração de alertas

### 🔗 Integração dos Paradigmas
A integração é o **ponto central do projeto**:
- O motor lógico decide o que é verdade no sistema
- Os aspectos definem como cada operação é interceptada e enriquecida
- Mantém a lógica de negócio livre de código repetido

---

## 📋 Domínio do Sistema

### 01. 👥 Gestão de Discentes
Cadastro de alunos e associação entre aluno, orientador e coorientador opcional.

**Estados Possíveis:**
- 🟢 **Regular**: dentro do prazo e com o plano em dia
- 🔄 **Em Prorrogação**: com semestre adicional concedido e em curso
- 🔴 **Em Risco**: com pendências ou prazos estourados que ameaçam a integralização
- ✅ **Qualificado**: aprovado na qualificação
- 📝 **Em Fase de Defesa**: apto à defesa e com a defesa encaminhada
- 🎓 **Concluído**: integralizou o curso e defendeu
- ❌ **Desligado**: removido do programa

### 02. 📊 Plano de Trabalho
Cada aluno possui um plano dividido em **etapas**:
- Revisão bibliográfica
- Definição do problema
- Desenvolvimento
- Experimentos
- Escrita
- Qualificação
- Defesa

Cada etapa possui tasks cadastradas pelo orientador, e o aluno registra atualizações de progresso vinculadas a uma task.

### 03. 🏆 Atividades Creditáveis
Termo guarda-chuva para tudo que gera crédito.

**Características:**
- A coordenação cadastra tipos de atividade creditável com pontuação, limites e requisitos
- Tipos: artigo publicado, artigo submetido, software registrado, patente, participação em banca, estágio docência, disciplina cursada, entre outros
- **Produção**: subtipo bibliográfico (artigo publicado ou submetido)
- Toda produção é vinculada a um veículo (evento ou revista)
- Cada veículo possui nível de relevância configurável a nível de programa
- Campo de observação livre para registrar impactos diferentes de produções no mesmo veículo

### 04. ✓ Checklist de Integralização
O aluno visualiza os requisitos para concluir o curso:
- Créditos mínimos
- Créditos por grupo
- Proficiência
- Qualificação
- Atividade creditável validada
- Defesa
- Versão final

O sistema indica: **cumpridos**, **pendentes** e **em risco**.

### 05. ⏱️ Prorrogação de Prazo
- Solicitação de semestre adicional com justificativa, plano atualizado e parecer do orientador
- Sujeita a regras configuráveis sobre quantidade de prorrogações

### 06. 📊 Dashboard
Visões agregadas para:
- Aluno
- Orientador
- Coordenação

### 07. 📈 Relatórios
Visões gerenciais agregadas:
- Alunos em atraso
- Alunos por status e por orientador
- Tempo médio de integralização
- Produção por aluno e por professor
- Exibíveis na interface

---

## 👤 Histórias de Usuário

| # | Papel | Objetivo | Benefício |
|---|-------|----------|-----------|
| 01 | Coordenação | Cadastrar alunos, orientadores e relação de orientação | Manter registro dos discentes do programa |
| 02 | Orientador | Cadastrar etapas e tasks do plano de trabalho | Organizar o acompanhamento do progresso |
| 03 | Aluno | Registrar atualizações de progresso vinculadas a uma task | Refletir o andamento do plano |
| 04 | Coordenação | Cadastrar tipos de atividade creditável | Definir como cada atividade gera créditos |
| 05 | Aluno | Registrar atividades creditáveis com comprovante | Serem validadas e contabilizadas nos créditos |
| 06 | Aluno | Registrar produção indicando veículo e observação | Relevância do veículo considerada na contabilização |
| 07 | Coordenação | Validar ou rejeitar atividades registradas | Controlar a contabilização de créditos |
| 08 | Aluno | Consultar checklist de integralização | Saber requisitos cumpridos, pendentes e em risco |
| 09 | Orientador | Inferência de situação acadêmica dos orientandos | Priorizar atenção |
| 10 | Usuário | Autorização por papel em operações sensíveis | Apenas quem tem permissão altera dados |
| 11 | Coordenação | Manter auditoria e histórico de alterações | Rastrear quem alterou o quê e quando |
| 12 | Usuário | Receber alertas de pendências e prazos | Agir a tempo |
| 13 | Coordenação | Gerar relatórios gerenciais | Acompanhar o andamento do programa |

---

## 📐 Regras Gerais de Implementação

1. ✅ O back-end e a lógica dos paradigmas devem ser implementados em **Python**, combinando os Paradigmas Lógico e Orientado a Aspectos no mesmo sistema.

2. ✅ O Paradigma Lógico deve ser realizado por um **motor de inferência implementado do zero**, sem bibliotecas externas de programação lógica.

3. ✅ O Paradigma Orientado a Aspectos deve ser realizado apenas com **recursos nativos do Python**, sem bibliotecas externas de orientação a aspectos.

4. ✅ A **lógica de negócio** das operações deve permanecer livre das preocupações transversais. Autorização, auditoria, histórico, validação de prazos e alertas devem ser aplicados por aspectos.

5. ✅ As **decisões sobre situações acadêmicas** devem ser expressas como regras declarativas resolvidas pelo motor de inferência, não como cadeias de if/else espalhadas pelo código.

6. ✅ O sistema deve contar com uma **interface gráfica** que permita executar operações do núcleo e visualizar o checklist de integralização e situação acadêmica inferida de um aluno.

7. ✅ O código deve seguir **princípios de Clean Code**: nomes descritivos, funções curtas, responsabilidades bem separadas e comentários significativos.

---

## 🔬 Regras Específicas de Programação Lógica

### Implementação do Motor

1. Implemente um **motor de inferência próprio** capaz de:
   - Representar fatos e regras
   - Realizar unificação entre termos
   - Aplicar substituições
   - Resolver consultas

2. Modele o conhecimento acadêmico como **fatos e regras (cláusulas)** processadas pelo motor:
   - Fatos vêm dos dados cadastrados (alunos, tasks, créditos, atividades creditáveis validadas)
   - Regras expressam as políticas do programa

### Inferências Obrigatórias

Cubra, no mínimo, as seguintes inferências por meio de **regras declarativas**:

#### a) 🎯 Aptidão à Defesa
Um aluno está apto se:
- ✓ Possui créditos mínimos
- ✓ Possui proficiência
- ✓ Qualificação aprovada
- ✓ Ao menos uma produção (atividade creditável do tipo bibliográfico) validada
- ✓ Plano concluído

#### b) 💳 Validação de Créditos
Os créditos do aluno satisfazem:
- ✓ Mínimo por grupo básico
- ✓ Mínimo por grupo específico
- ✓ Máximo por atividade creditável do tipo tecnológico

#### c) 📊 Situação Acadêmica
Inferir a situação do aluno dentre os estados definidos no Domínio:
- Distinguir regular de em risco
- Identificar qualificado e em fase de defesa

#### d) 📝 Elegibilidade de Atividade Creditável
Uma atividade creditável gera crédito se:
- ✓ Estiver dentro do período do curso
- ✓ Possuir comprovante
- ✓ Ter o tipo ativo
- ✓ Não exceder o limite por categoria

#### e) ⭐ Pontuação de Produção
A pontuação de uma produção pondera:
- ✓ Nível de relevância do veículo
- ✓ Configurável a nível de programa

### Boas Práticas

- 📌 Regras devem ser **declarativas e configuráveis**
- 📌 Mudar uma política significa alterar regras ou fatos, não reescrever fluxo
- 📌 **Separar claramente**: base de fatos, base de regras e mecanismo de resolução
- 📌 Sistema consulta o motor por uma **interface de consulta**

---

## ⚙️ Regras Específicas de Programação Orientada a Aspectos

### Aspectos Obrigatórios

Trate como aspectos as preocupações que atravessam várias operações. **Mínimo de cinco aspectos**:

1. 🔐 **Autorização por Papel**
2. 📋 **Auditoria das Operações**
3. 📜 **Histórico de Alterações das Entidades**
4. ⏰ **Validação de Prazos**
5. 🔔 **Geração de Alertas de Pendências**

### Implementação

- ✅ Usar **exclusivamente mecanismos nativos do Python**:
  - Decoradores
  - Metaclasses
  - Descritores
  - `__init_subclass__`
  - Módulo `inspect`

### Documentação Obrigatória

Deixar explícito na documentação e comentários:
- 🎯 **Join Points**: pontos de interceptação
- 🎬 **Advices**: comportamento aplicado antes, depois ou em torno da operação
- 🔗 **Weaving**: aplicação dos aspectos sobre o código de negócio

### Reutilização e Configurabilidade

- ✅ Um mesmo aspecto reutilizado em múltiplas operações **sem duplicação**
- ✅ Adicionar nova operação **não exige reescrever** autorização, auditoria ou histórico
- ✅ **Ativação dos aspectos configurável**: ligar ou desligar preocupações transversais sem alterar lógica de negócio

---

## 📦 Regras de Organização

### Repositório GitHub

- **Repositório privado** no GitHub
- Adicionar professores como colaboradores:
  - `paulosevero`
  - `sequincozes`

### Metodologia Kanban

- ✅ Issues como tarefas do projeto
- ✅ Quadro do projeto populado com todas as tarefas
- ✅ Tarefas organizadas na coluna **Backlog** inicialmente
- ✅ Fluxo semanal: **Backlog → Sprint Backlog → Em Progresso → Feito**
- ✅ Responsáveis atribuídos a cada tarefa

### ⚠️ Prazos Críticos

| Fase | Data | Hora | Consequência |
|------|------|------|--------------|
| Setup do Repositório | 07/06/2026 | 23h59min | **NOk** para todo grupo se negligenciado |
| Entrega Final | 13/07/2026 | - | Conceito final |

> **IMPORTANTE**: A criação do repositório, compartilhamento com professores e organização do projeto devem ser realizados até **07/06/2026 às 23h59min**. Negligência resultará em conceito NOk para o grupo inteiro na verificação semanal.

---

## 🛠️ Stack de Tecnologia

| Componente | Tecnologia |
|------------|-----------|
| 🎨 Front-end | **React** |
| 🔧 Back-end | **FastAPI** |
| 🗄️ Banco de dados | **Firebase** |

---

## 💡 Dicas de Implementação

### Programação Lógica (Motor de Inferência)

1. 🚀 **Comece isolado**: motor com pequeno conjunto de fatos e regras de teste antes de conectar ao domínio acadêmico
   - Garanta que unificação, substituição e aplicação de regras funcionam em consultas simples

2. 📦 **Estruturas simples**: represente termos lógicos com tuplas e uma classe para variáveis
   - Mantenha substituição como dicionário de variável para valor

3. 📝 **Regras nomeadas**: cada regra de forma independente
   - Teste isoladamente
   - Ligue ou desligue políticas sem tocar no restante do código

4. 🧪 **Testes abrangentes**: cada inferência com casos de:
   - ✓ Aluno apto
   - ✓ Aluno em risco
   - ✓ Aluno inapto
   - Resultado deve mudar conforme os fatos

5. 🎚️ **Relevância configurável**: trate como fato, não como valor fixo
   - Pontuação de mesma produção pode mudar conforme relevância cadastrada e observação registrada

6. 🔌 **Interface única**: exponha motor por uma única função de consulta
   - Mantenha fatos, regras e resolução em módulos separados

### Programação Orientada a Aspectos

1. 🔨 **Incremental**: implemente aspecto simples primeiro (auditoria via decorador)
   - Só depois generalize para os demais
   - Cada aspecto reutilizável em várias operações

2. 🎯 **Mecanismos apropriados**:
   - **Decoradores**: para interceptar funções ou métodos individuais
   - **Metaclasses/`__init_subclass__`**: para aplicar aspecto a todos os métodos de uma classe
   - **Descritores**: quando ponto de interceptação é acesso a atributo

3. 🔍 **Módulo inspect**: use para descobrir em tempo de execução:
   - Nome, argumentos, assinatura das operações interceptadas
   - Útil para auditoria, histórico e rastreabilidade

4. 📋 **Sugestões de Aspectos**:

#### a) 📊 **Auditoria**
Registra em operações como:
- Cadastro de plano
- Criação de task
- Envio de progresso
- Validação de atividade creditável
- Mudança de status

O que registrar:
- Usuário, perfil, operação, data/hora
- Entidade afetada e valor anterior e novo

#### b) 🔐 **Autorização por Perfil**
Antes da operação, verifica o papel:
- Aluno registra apenas progresso próprio
- Orientador altera apenas planos dos próprios orientandos
- Coordenação valida atividades creditáveis e mantém checklist e tipos

#### c) 🔔 **Notificações e Alertas**
Após a operação, dispara avisos:
- Progresso registrado → notifica orientador
- Task próxima do vencimento → alerta aluno
- Atividade creditável validada/rejeitada → notifica aluno

#### d) ⏰ **Validação de Prazos**
Antes ou depois da operação, verifica:
- Tasks vencidas
- Plano atrasado
- Qualificação ou defesa próximas
- Checklist incompleto perto do prazo
- Alimenta marcação de em risco

#### e) 📜 **Histórico e Versionamento**
Ao alterar:
- Plano
- Checklist
- Tipo de atividade creditável

Guarda versão anterior, evidenciando que regras institucionais mudam com o tempo.

5. 📚 **Documentação Explícita**:
   - Onde estão os **join points** (pontos interceptados)
   - Quais são os **advices** (comportamento antes, depois ou em torno)
   - Como ocorre o **weaving** (aplicação dos aspectos)

---

## 📖 Glossário

### Programação Lógica

| Termo | Definição |
|-------|-----------|
| **Motor de Inferência** | Programa que responde consultas combinando fatos e regras para deduzir novas conclusões, em vez de seguir um passo a passo fixo escrito pelo programador |
| **Fato** | Afirmação que o sistema considera verdadeira, derivada dos dados cadastrados (ex: "o aluno A concluiu a qualificação") |
| **Regra (Cláusula)** | Afirmação condicional que deduz algo novo a partir de outras condições (ex: "A está apto à defesa se A tem créditos mínimos e qualificação aprovada e produção validada") |
| **Termo** | Unidade de informação manipulada pelo motor, podendo ser um valor concreto (constante) ou uma incógnita (variável) |
| **Variável Lógica** | Incógnita dentro de um termo cujo valor o motor tenta descobrir ao responder uma consulta |
| **Unificação** | Processo de comparar dois termos e descobrir quais valores tornam ambos iguais (ex: casar "apto(X)" com "apto(aluno_A)" descobrindo que X é aluno_A) |
| **Substituição** | Conjunto de pares variável-valor encontrado pela unificação, mantido tipicamente como dicionário de variável para valor |
| **Consulta** | Pergunta feita ao motor (ex: "o aluno A está apto à defesa?"), que o motor responde aplicando fatos e regras |
| **Aplicação Direta de Regras** | Estratégia de resolução em que o motor verifica as condições de uma regra de forma direta (conjunção de condições), sem testar caminhos alternativos nem voltar atrás (sem backtracking) |
| **Base de Fatos e Base de Regras** | Duas coleções que o motor consulta, separadas do mecanismo que resolve as consultas |

### Programação Orientada a Aspectos

| Termo | Definição |
|-------|-----------|
| **Programação Orientada a Aspectos** | Abordagem que isola, em módulos próprios chamados aspectos, comportamentos que se repetem em muitas partes do sistema, mantendo a lógica de negócio limpa |
| **Preocupação Transversal (Cross-Cutting Concern)** | Comportamento necessário em várias operações diferentes (autorização, auditoria, histórico, alertas) que cortaria o código todo se fosse escrito manualmente em cada lugar |
| **Aspecto** | Módulo que encapsula uma preocupação transversal e a aplica sobre as operações de negócio sem que elas precisem conhecê-la |
| **Separação de Interesses** | Princípio de manter cada responsabilidade em seu próprio lugar, de modo que a lógica de negócio não se misture com as preocupações transversais |
| **Join Point (Ponto de Junção)** | Ponto do programa onde um aspecto pode ser aplicado (ex: a chamada de um método ou acesso a um atributo) |
| **Advice** | Comportamento que o aspecto executa no join point, podendo rodar antes, depois ou em torno da operação original |
| **Weaving (Tecelagem)** | Ato de combinar os aspectos com a lógica de negócio, fazendo os advices serem de fato executados nos join points selecionados. Em Python, feito por decoradores, metaclasses e mecanismos afins |

### Mecanismos Nativos do Python Usados como Aspectos

| Mecanismo | Uso |
|-----------|-----|
| **Decorador** | Função que envolve outra função ou método para acrescentar comportamento antes ou depois, sem alterar o código original |
| **Metaclasse** | Classe que define como outras classes são criadas, permitindo aplicar um aspecto a todos os métodos de uma classe de uma só vez |
| **Descritor** | Objeto que controla a leitura e a escrita de um atributo, servindo como ponto de interceptação no acesso a dados |
| **`__init_subclass__`** | Gancho chamado automaticamente quando uma classe é definida a partir de outra, útil para aplicar aspectos a toda uma hierarquia de classes |
| **`inspect`** | Módulo padrão que revela, em tempo de execução, informações sobre funções e classes (nome, argumentos, assinatura), úteis para auditoria e rastreabilidade |

---

## 🎯 Resumo Executivo

Este projeto combina **dois paradigmas de programação** em um único sistema para gerenciar a pós-graduação:

- 🧠 **Lógica** define o que é verdade
- ⚙️ **Aspectos** definem como as operações são enriquecidas

O resultado é um sistema **robusto, manutenível e extensível** que mantém a lógica de negócio limpa e separada das preocupações transversais.

---

**Documento de Especificação do Projeto**  
*Última atualização: 2026*
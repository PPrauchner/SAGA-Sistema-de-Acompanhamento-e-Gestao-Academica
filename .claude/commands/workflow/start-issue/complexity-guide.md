# Guia de Complexidade

## NÃO quebrar (issue simples)

- Bug fix em arquivo único ou poucos arquivos do mesmo módulo
- Ajuste de UI isolado (só frontend, sem impacto em API)
- Mudança em um único serviço sem impacto cross-layer
- Adição de campo simples sem lógica nova
- Estimativa menor que 1 hora de trabalho

## QUEBRAR em sub-tarefas (issue complexa)

- Nova feature que atravessa camadas: model → repository → service → endpoint
- Mudança que afeta frontend E backend
- Criação de 3 ou mais arquivos em partes distintas do projeto
- Envolve lógica nova no `inference_engine` (requer spec + regra + testes)
- Envolve um novo aspecto AOP
- Estimativa maior que 1,5 horas

## Formato das sub-tarefas

Cada sub-tarefa precisa de:
- **Título** — curto, imperativo (ex: "Criar modelo ActivityLog")
- **Escopo** — o que exatamente será feito
- **Spec de referência** — seção relevante em `docs/specs/`, se aplicável
- **Dependências** — quais sub-tarefas devem ser concluídas antes

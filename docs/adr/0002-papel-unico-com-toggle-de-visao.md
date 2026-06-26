# Papel único por usuário, com toggle de visão no frontend

O claim mantém `role` **singular**. Um coordenador que também orienta alunos não recebe múltiplos papéis: `coordenacao` é tratado como superset de `orientador`, e o seletor "Visualizando como: Orientador | Coordenador" é um **filtro de visão no frontend** que restringe a tela aos alunos que ele orienta pessoalmente.

Escolhemos isso em vez de um claim `roles: list` (multi-papel de primeira classe) porque a única combinação real é coordenador+orientador, e coordenação já é superset — modelar lista exigiria reescrever auth, A01 e todos os checks para um ganho marginal.

**Consequência deliberada (não "consertar"):** o toggle é conveniência de UI, **não** uma fronteira de segurança. Quando um coordenador seleciona "visão de orientador", o backend continua autorizando pelo papel real (`coordenacao`) — os endpoints administrativos permanecem acessíveis; o toggle apenas oculta os botões. Isso é aceitável porque o coordenador já é confiável e está escondendo os próprios privilégios, não escalando. Não adicione enforcement server-side do toggle achando que é um bug.

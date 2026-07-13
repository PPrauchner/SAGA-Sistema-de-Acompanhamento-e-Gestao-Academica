# Exclusão de atividade aprovada: hard delete, reverte créditos e re-roda o motor

Uma [Atividade Creditável](../../CONTEXT.md#atividade-creditável) `aprovado` pode ser
**excluída pela coordenação**. A exclusão é **hard delete** do documento em
`students/{id}/activities` — não há tombstone nem status "excluída". Ao excluir uma
atividade aprovada, os créditos contabilizados são revertidos e o motor de inferência é
**re-executado** para o aluno (situação inferida pode voltar a "em risco"/inapto). O
rastro fica exclusivamente em `audit_logs` via aspecto A02.

Escolhemos hard delete + auditoria em vez de soft delete porque o A02 já preserva o
histórico da operação (autor, ação, timestamp), tornando o tombstone redundante e
mantendo as coleções limpas para as queries de crédito (que varrem `activities` por
status). O custo é que a atividade deixa de ser recuperável na coleção — aceitável dado
o registro de auditoria.

**Consequência deliberada (não "consertar"):** um registro acadêmico `aprovado` **não é
imutável** — a coordenação pode removê-lo. Quem esperar imutabilidade de aprovados vai
estranhar; é intencional. Atividades lastreadas em produção (`producao_id` != None) são a
exceção: **não** podem ser excluídas por aqui (remove-se a produção). Em coautoria, o
delete é por-cópia e não afeta as cópias dos demais co-autores (ver [ADR-0006](./0006-coautoria-copias-independentes-credito-cheio.md)).

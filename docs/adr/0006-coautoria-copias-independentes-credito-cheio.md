# Coautoria: cópias independentes, crédito cheio, sem consentimento

Uma [Atividade Creditável](../../CONTEXT.md#atividade-creditável) ou [Produção
Bibliográfica](../../CONTEXT.md#produção-bibliográfica) pode ter co-autores discentes
cadastrados. Cada co-autor recebe uma **cópia independente** da atividade na própria
subcoleção `students/{id}/activities`, validada separadamente pelo seu orientador, e
recebe o **crédito/pontuação cheios** (sem rateio). Não há passo de consentimento do
co-autor — a validação do orientador é o único gate. Autores não cadastrados entram
como texto livre (informativo, não geram crédito).

Escolhemos crédito cheio + cópias independentes para espelhar o modelo já vigente da
produção bibliográfica (cada autor uid já recebe uma activity dedicada e pontua cheio),
em vez de ratear créditos ou exigir aceite — que exigiriam lógica nova em RL02/RL04 e
um fluxo de aceite, para ganho marginal.

**Consequência deliberada (não "consertar"):** existirão documentos de atividade
"duplicados" entre alunos descrevendo o mesmo evento/produção. Isso **não** é duplicata
para a RL04 — cuja checagem `nao_duplicata` opera **dentro de um mesmo aluno** — e não
deve ser deduplicado. O risco de inflação de créditos por coautoria fictícia é contido
pela validação individual de cada cópia pelo orientador, não por trava automática.

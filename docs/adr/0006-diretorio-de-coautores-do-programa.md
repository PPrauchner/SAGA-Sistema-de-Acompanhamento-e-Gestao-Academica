# Diretório de co-autores é program-wide (`{uid, nome}` a qualquer papel)

O formulário de produção bibliográfica permite escolher **co-autores entre os alunos
cadastrados** (issue #310). Para alimentar esse seletor, `GET /api/v1/students/coauthors`
devolve `{uid, nome}` de **todos os alunos do programa do chamador**, acessível a
**qualquer papel autenticado — inclusive `aluno`**.

Isso diverge deliberadamente de `GET /api/v1/students`, que é restrito a
`orientador`/`coordenacao` e escopa a lista por orientador. A divergência é necessária,
não acidental.

## Por quê program-wide (e não escopado por orientador)

A co-autoria entre alunos (decisão Q8/Q9 do modelo de dados) é **ortogonal ao
orientador**: um artigo pode ter autores com orientadores diferentes dentro do mesmo
programa, e cada co-autor reivindica crédito pela sua própria `activity` ligada à
`production` raiz. Escopar o diretório ao orientador do chamador quebraria exatamente o
caso que a co-autoria existe para suportar — alunos de orientadores distintos co-autorando.
Logo, o candidato elegível a co-autor é **qualquer aluno do programa**, e o seletor
precisa enxergá-los todos.

## Por quê a exposição é aceitável

- **Campos mínimos:** devolve só `{uid, nome}` — nunca o `StudentResponse` completo
  (matrícula, orientador, situação, prazos). Um par que só precisa escolher um nome não
  recebe dado sensível de outro aluno.
- **Escopo de tenant preservado:** a lista é filtrada por `programa_id` do chamador
  (`list_by_program`); não há vazamento cross-programa.
- **Só contas ativadas:** apenas alunos com `uid` vinculado entram na lista (quem pode,
  de fato, ser referenciado em `autores[]`).

## Consequências

- A fronteira de autorização de `/students/coauthors` é intencionalmente mais ampla que a
  de `/students`. Qualquer mudança que restrinja esse endpoint precisa revisitar Q8/Q9,
  pois pode inviabilizar a co-autoria cross-orientador.
- Se no futuro o programa exigir sigilo de roster (alunos não devem enumerar colegas), a
  alternativa é resolver co-autores por outra chave (ex.: e-mail/matrícula digitada) em vez
  de listar — o que troca conveniência de UX por privacidade. Não é o caso no MVP
  (single-tenant, `prog_default`).

## Atividades standalone (issue #311)

O mesmo diretorio alimenta o seletor de coautores de atividades creditaveis nao
bibliograficas. Nesse fluxo nao ha entidade raiz compartilhada: o registro cria uma copia
independente em `students/{id}/activities` para o autor principal e para cada coautor
cadastrado selecionado.

As copias compartilham apenas `activity_group_id` para rastreabilidade. Cada copia tem ID
proprio, `student_id` proprio, status/parecer/validacao independentes e credito cheio quando
aprovada. Nas copias de coautores, `origin_activity_id` aponta para a copia original.

Autores externos informados em texto livre ficam em `external_authors`: nao geram copia,
validacao ou credito. Nao ha consentimento do coautor; o gate de credito continua sendo a
validacao do orientador do aluno dono da copia.

A RL04 `nao_duplicata` permanece escopada ao aluno/subcolecao. Copias equivalentes em alunos
diferentes nao devem ser consideradas duplicatas entre si.

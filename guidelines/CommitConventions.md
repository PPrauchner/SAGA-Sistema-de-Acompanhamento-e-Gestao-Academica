# Convenções de Commit — SAGA

## Regra fundamental: commits DEVEM ser atômicos

Cada commit representa a **menor mudança funcional possível** — o mínimo de arquivos que, juntos, produzem uma mudança observável no comportamento do sistema. Um commit atômico:
- Pode ser revertido sem afetar outras funcionalidades
- Tem uma única razão para existir
- Compila e passa nos testes de forma independente
- É compreensível sem contexto adicional

**Nunca** agrupe mudanças não relacionadas em um único commit.

### Critério de atomicidade: mudança funcional mínima

A pergunta a fazer antes de cada commit é: **"consigo dividir isso em partes menores que ainda façam sentido sozinhas?"**. Se sim, divida.

Um commit pode incluir mais de um arquivo **somente** quando esses arquivos são inseparáveis para que a mudança funcione — por exemplo, um novo modelo Pydantic e o schema Firestore correspondente. Se os arquivos podem ser introduzidos em etapas distintas, devem ser commits distintos.

**Nunca** faça (vários arquivos de camadas diferentes agrupados):
```
feat(backend/api): implementa endpoint de validação de atividades
# inclui: router, service, repository, schema — tudo junto
```

**Sempre** progrida em etapas:
```
feat(backend/models): adiciona schema ActivityValidation
feat(backend/repositories): adiciona ActivityRepository.update_status
feat(backend/services): implementa ActivityService.validate
feat(backend/api): adiciona endpoint PATCH /activities/{id}/validate
```

Cada etapa deve compilar e fazer sentido isoladamente.

### Testes sempre em commit separado

Commits de implementação (`feat`, `fix`, `refactor`) **nunca** devem incluir arquivos de teste. A sequência correta é:

1. `feat(escopo): implementa a funcionalidade X`
2. `test(escopo): adiciona testes para X`

**Nunca** faça:
```
feat(inference-engine/rules): implementa rl03 e adiciona testes
```

**Sempre** separe:
```
feat(inference-engine/rules): implementa regra rl03 de status acadêmico
test(inference-engine/rules): adiciona cenários apto/risco/inapto para rl03
```

---

## Template

```
<tipo>(<escopo>): <descrição curta em letras minúsculas e no imperativo>

[Opcional: Corpo do commit detalhando a motivação e o "porquê" da mudança.
Mantenha as linhas com no máximo 72 caracteres.]

[Opcional: Rodapé para listar Breaking Changes ou referenciar Issues/Tarefas]
```

O arquivo `.gitmessage` na raiz do projeto pode ser configurado como
template padrão do git:

```bash
git config commit.template .gitmessage
```

---

## Tipos permitidos

| Tipo       | Uso                                                          |
|------------|--------------------------------------------------------------|
| `feat`     | Nova funcionalidade                                          |
| `fix`      | Correção de bug                                              |
| `docs`     | Alterações em documentação                                   |
| `test`     | Adição ou correção de testes                                 |
| `refactor` | Refatoração sem alterar comportamento externo                |
| `chore`    | Tarefas de configuração, build, ferramentas                  |
| `style`    | Formatação, espaços, vírgulas (sem mudança de lógica)        |
| `perf`     | Melhoria de performance                                      |
| `ci`       | Mudanças em pipelines de CI/CD                               |

## Escopos sugeridos

`backend/core` · `backend/api` · `backend/models` · `backend/services`
`backend/repositories` · `backend/aspects` · `inference-engine`
`inference-engine/rules` · `frontend/api` · `frontend/hooks`
`frontend/components` · `docs` · `config` · `scripts`

---

## Exemplos

```
feat(backend/api): adiciona endpoint de validação de atividades

Implementa PATCH /api/v1/activities/{id}/validate com fluxo de
três etapas: parecer do orientador, aprovação da coordenação e
execução do motor RL04 para verificar elegibilidade.

Closes #42
```

```
fix(inference-engine): corrige occur check na unificação de variáveis
```

```
test(inference-engine/rules): adiciona cenários de risco para rl03

Cobre os quatro gatilhos alternativos de em_risco: prazo estourado,
créditos insuficientes, qualificação pendente e plano atrasado.
```

```
chore(config): adiciona .gitmessage como template padrão de commit
```

---

## Breaking Changes

Mudanças que quebram compatibilidade devem ser indicadas no rodapé:

```
feat(backend/api): altera contrato de resposta do checklist

BREAKING CHANGE: campo `requisitos.creditos` renomeado para
`requisitos.creditos_minimos` para consistência com o motor.
```

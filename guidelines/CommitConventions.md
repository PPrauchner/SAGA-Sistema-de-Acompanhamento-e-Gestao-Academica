# Convenções de Commit — SAGA

## Regra fundamental: commits DEVEM ser atômicos

Cada commit deve representar **uma única mudança lógica e coerente**. Um commit atômico:
- Pode ser revertido sem afetar outras funcionalidades
- Tem uma única razão para existir
- Compila e passa nos testes de forma independente
- É compreensível sem contexto adicional

**Nunca** agrupe mudanças não relacionadas em um único commit.

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

# Convenções de Código — SAGA

> Lido pelo agente ao escrever ou revisar código. Para o modelo de domínio, ver `CONTEXT.md`.

---

## Python — Docstrings

Padrão **Google Style** em todos os arquivos Python. Quatro níveis obrigatórios:

**1. Módulo** — todo `.py` começa com um bloco descritivo:
```python
"""
<Título de uma linha descrevendo o módulo.>

Responsabilidades:
- <responsabilidade 1>
- <responsabilidade 2>

Restrições: (somente quando aplicável, ex: inference_engine/)
- Sem imports de FastAPI, Firebase ou qualquer ORM.
"""
```

**2. Função / método** — obrigatório quando há ≥ 2 parâmetros ou o retorno não é óbvio:
```python
def unify(t1: Term, t2: Term, subst: dict) -> dict | None:
    """Unifica dois termos sob a substituição parcial `subst`.

    Args:
        t1: Primeiro termo a unificar.
        t2: Segundo termo a unificar.
        subst: Substituição parcial acumulada (variável → Term).

    Returns:
        Substituição estendida se bem-sucedida, None caso contrário.

    Raises:
        OccurCheckError: Se detectar ciclo via occur check.
    """
```

**3. Aspecto** — cada decorator/metaclasse que implementa um aspecto deve declarar Join Point, Advice e Weaving:
```python
def requires_role(*roles: str):
    """Aspecto A01 — Autorização por Papel.

    Join Point: qualquer endpoint FastAPI decorado com @requires_role.
    Advice: Before — verifica papel antes de executar a função original.
    Weaving: decorador Python aplicado manualmente sobre funções de negócio.
    """
```

**4. Classe** — docstring na classe e nos métodos públicos não-triviais:
```python
class FirebaseRepository:
    """Repositório base genérico para operações no Firestore.

    Attributes:
        db: Cliente Firestore assíncrono obtido de core/firebase.py.
    """
```

---

## Python — Type Hints

- **Todo parâmetro e retorno** de função/método devem ser tipados — sem exceção.
- Sintaxe nativa Python 3.10+: `X | None` em vez de `Optional[X]`; `list[str]` em vez de `List[str]`.
- Para forward references, adicionar `from __future__ import annotations` no topo.
- Funções assíncronas: anotar o tipo do valor retornado pelo `await` (ex: `async def get(...) -> Student`).
- `inference_engine/` usa **exclusivamente** tipos da stdlib — proibido `pydantic`, `typing_extensions` ou tipos do FastAPI.

```python
# ✅ correto
def apply(subst: dict, term: Term) -> Term: ...
async def create_student(data: StudentCreate, user: CurrentUser) -> Student: ...

# ❌ errado
def apply(subst, term):           # sem anotações
async def get_all() -> list[Any]: # Any encobre erros
```

---

## Restrições Obrigatórias do Enunciado

### Motor de Inferência (`inference_engine/`)
- **Isolamento total**: proibido importar FastAPI, Firebase, pydantic, SQLAlchemy ou qualquer pacote fora da stdlib Python.
- Único ponto de entrada externo: `InferenceEngine.query(goal: Term) -> list[dict]`.
- Decisões acadêmicas **nunca** como cadeias de `if/else` nos services — sempre como regras declarativas em `rules/RL01`–`RL05`.
- Para alterar uma política acadêmica: editar apenas o arquivo correspondente em `rules/`, não a lógica de controle.

### Aspectos AOP
- **Proibido** usar bibliotecas externas de AOP (`aspectlib`, `python-aspectlib`, `wrapt` para AOP, etc.).
- Mecanismos permitidos: decoradores, metaclasses, descritores, `__init_subclass__`, `inspect`.
- Todo aspecto **deve documentar** no docstring: Join Point, Advice (Before / After / Around), Weaving.
- Lógica de negócio em `services/` e `api/v1/` **não deve conter** código de autorização, auditoria, histórico, validação de prazo ou alertas.
- Aspectos ativáveis/desativáveis via `aspect_config.py` sem alterar código de negócio.

### Routers (`api/v1/`)
- Nenhuma lógica de negócio nos arquivos de rota — apenas: receber request → chamar service → retornar response.
- Ordem canônica de decoradores:
  ```python
  @requires_role(...)
  @audit_operation
  @check_deadlines
  @trigger_alerts
  async def endpoint_func(...):
  ```

### Clean Code (geral)
- Funções com responsabilidade única — se o nome precisar de "e" ou "ou", dividir em duas.
- Nomes descritivos: sem abreviações opacas (`stud` → `student`, `act` → `activity`).
- Constantes em `UPPER_SNAKE_CASE`; variáveis e funções em `snake_case`; classes em `PascalCase`.
- Comentários explicam *por quê*, não *o quê*.

---

## TypeScript

- Um arquivo de API por domínio em `src/api/`; hooks em `src/hooks/`.
- Alias `@` aponta para `src/`.
- Tipar todos os retornos de funções e props de componentes.

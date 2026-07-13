---
paths:
  - "backend/**"
---

# Regras — Backend

Carregado automaticamente ao trabalhar em qualquer arquivo dentro de `backend/`.

## Isolamento do inference_engine

O `inference_engine/` é completamente isolado — sem imports externos:
- Proibido importar FastAPI, Firebase, Pydantic ou qualquer ORM dentro de `inference_engine/`
- Único ponto de entrada externo: `InferenceEngine.query(goal: Term) -> list[dict]`
- `InferenceService` (em `services/`) é o único responsável por popular a `FactBase`
- Para adicionar/alterar regra de negócio: edite apenas o arquivo em `rules/` (RL01–RL05)

Após qualquer alteração em `backend/inference_engine/`, rode e confirme:
```bash
pytest backend/inference_engine/tests/ -v
```
Não prossiga com testes falhando.

## Ordem canônica de decoradores AOP

```python
@requires_role(...)
@audit_operation
@check_deadlines
@trigger_alerts
async def endpoint_func(...):
```

## Convenções Python

- Docstrings em todos os módulos públicos
- Tipagem explícita em funções e métodos
- Sem lógica nos arquivos de rota — delegate para services
- Uma camada por commit (models, services, api/v1 em commits separados)

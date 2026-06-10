# Regras de Atomicidade

## Princípios

- **Uma camada por commit** — `models/`, `services/`, `api/v1/` em commits separados, mesmo que do mesmo domínio
- **Config/deps separados de features** — `pyproject.toml`, `.env.example`, arquivos de configuração = commit independente
- **Scaffolding separado de implementação** — criar estrutura de arquivo ≠ implementar lógica
- **Um domínio por commit** — mudanças em `students/` e `activities/` = dois commits
- **Teste junto com o código que testa** — o teste vai no mesmo commit da função que ele testa
- **Docs junto com o que documentam** — docstrings e README do módulo vão no commit do módulo

## Tipos

`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `style`, `perf`, `ci`

## Escopos sugeridos

| Escopo | Quando usar |
|--------|-------------|
| `backend/core` | Módulos base, configuração central |
| `backend/api` | Endpoints FastAPI |
| `backend/models` | Modelos Pydantic / ORM |
| `backend/services` | Lógica de negócio |
| `backend/repositories` | Camada de persistência |
| `backend/aspects` | Aspectos AOP |
| `inference-engine` | Motor de inferência |
| `inference-engine/rules` | Regras específicas do motor |
| `frontend/api` | Camada de API do frontend |
| `frontend/hooks` | React hooks |
| `frontend/components` | Componentes React |
| `docs` | Documentação |
| `config` | Configuração de ambiente/build |
| `scripts` | Scripts utilitários |

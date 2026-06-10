---
paths:
  - "src/**"
---

# Regras — Frontend

Carregado automaticamente ao trabalhar em qualquer arquivo dentro de `src/`.

## Estrutura

- Um arquivo de API por domínio em `src/api/`
- Hooks em `src/hooks/`; alias `@` aponta para `src/`
- Componentes UI usam shadcn/ui — não criar componentes do zero para o que já existe
- Estado global via `AppContext` em `src/app/context/`

## Firebase no frontend

- **Leitura direta no frontend**: APENAS `notifications/` (via `onSnapshot`)
- Toda escrita passa pelo backend (Admin SDK)
- Nunca exponha chaves do Firebase Admin no frontend

## Convenções TypeScript

- Tipagem explícita — sem `any` salvo em casos justificados com comentário
- Imports absolutos com alias `@` (ex: `@/hooks/useAuth`)
- Componentes funcionais com hooks; sem class components

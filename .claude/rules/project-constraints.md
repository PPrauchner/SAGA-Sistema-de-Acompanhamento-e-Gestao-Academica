# Restrições deste projeto

> **Semente.** O ARK entrega este arquivo uma vez, vazio, para o projeto preencher —
> e nunca mais o toca. Quem preenche é a skill `adopt-repo`, na sessão de *grill with
> docs* (log em `docs/grills_logs/`).
>
> O genérico do ARK (idioma, clean code) não mora aqui: vem do clone, importado pela
> Instalação global. Este arquivo é só o que vale **neste** repositório.
>
> Modelo de domínio em [`CONTEXT.md`](../../CONTEXT.md); decisões e porquês em
> [`docs/adr/`](../../docs/adr/).

---

O que entra aqui é o que **não pode mudar** e não se descobre lendo o código:
linguagem e versão, dependências centrais vs. opcionais, tipo de interface
(CLI/web/API), formato de persistência, exigência de reprodutibilidade, limites de
ambiente, estrutura de pastas — o que for específico e não-óbvio deste projeto.

Dependência que é decisão, e não acaso, entra. Acaso, não.

As restrições impostas pelo **enunciado** (motor de inferência isolado, AOP só com
recursos nativos, routers sem lógica de negócio) estão em
[`code-conventions.md`](./code-conventions.md) — não repetidas aqui.

## Fase do projeto

- **O projeto já foi entregue** (disciplina concluída). O trabalho corrente é
  majoritariamente de **correção**, mas **features novas continuam possíveis** —
  há intenção de integrar o SAGA a outro sistema existente no futuro. Por isso o
  workflow e os guias de fatiamento da fase de features seguem valendo.

## Persistência

- **Firestore** é o banco, e a **escrita é exclusiva do backend** (Admin SDK). O
  frontend só lê diretamente `notifications/` via `onSnapshot`; qualquer outra
  leitura/escrita passa pela API. Não abrir escrita no cliente nem trocar de banco.
- **Pendente:** a integração futura com outro sistema ainda não está definida (qual
  sistema, direção do fluxo de dados). Quando for, rever esta seção — ela pode
  mudar o que vale aqui.

## Ambiente e ferramentas

- **Python ≥ 3.12**, dependências gerenciadas com **uv** (`uv.lock` é a fonte da
  verdade). Não introduzir `requirements.txt` nem outro gerenciador.
- **pnpm** no frontend (`pnpm-lock.yaml`). Não usar npm/yarn — um segundo lockfile
  é erro, não alternativa.

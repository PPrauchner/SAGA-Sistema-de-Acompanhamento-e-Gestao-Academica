---
status: accepted — supersede os refinamentos R1/R4 de docs/data-model-decisions.md
---

# Pesos Qualis versionados por programa, pontuação fixada na data de publicação

Cada coordenador define, **por programa**, o peso de cada nível Qualis da escala **A1–A8 + fallback** (veículo sem nível classificado). Os pesos vivem em uma coleção **versionada**: cada conjunto carrega `vigente_desde`, `alterado_por` e `alterado_em` — a própria coleção é o histórico de mudanças (quem mudou e quando).

A RL05 calcula `score = pontuacao_base × peso`, onde o peso é o **vigente na data de publicação** da produção. O `inference_service` resolve a versão correta e injeta o peso como fato — o `inference_engine` permanece isolado e sem noção de datas. Produção ainda não publicada (`submetido`/`aceito`) usa o peso **vigente atual** (provisório); ao ser publicada, o peso fica travado na versão vigente naquela data.

## Por que, e o que isto supera

Substitui a decisão anterior (R1/R4, issue #133) de uma **escala global única e estática** (`A1, A2, A3, A4, B1, B2, SC` com `PESO_POR_NIVEL` hardcoded em `backend/app/models/vehicle.py`). Aquela escala assumia que os pesos eram política do sistema; o domínio real é que cada programa define e revisa seus próprios pesos ao longo do tempo, e revisões **não** podem reescrever a pontuação de produções já publicadas.

Escolhemos versionar por data de vigência em vez de **congelar o score na produção** (snapshot na aprovação) porque o requisito é "publicações publicadas antes da mudança não são alteradas" — a fronteira é a **data de publicação**, não o evento de aprovação. Versionar unifica imutabilidade + histórico em uma estrutura só e mantém a pontuação replayável a partir de `(base, nível, data_publicação)`.

## Consequências (impacto a tratar fora deste grill)

- `RelevanceLevel` e `PESO_POR_NIVEL` em `vehicle.py` deixam de ser fonte única global: a escala vira `A1–A8 + fallback` e os pesos migram para config versionada por programa.
- `seed_firestore`, fixtures, testes RL05 e `inference_service` (que hoje lê `program["relevancia_pesos"]` estático) precisam passar a resolver a versão por data de publicação.
- `docs/data-model-decisions.md` (R1/R4) e a user-story `docs/user-stories/veiculos-qualis.md` ficam desatualizados e devem ser reconciliados.

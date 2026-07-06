# Histórias de Usuário — Veículos, Níveis Qualis e Pesos por Programa

> Geradas a partir da sessão de feedback (áudio 2026-06-22) e refinadas no grill de 2026-06-23.
> Contexto: classificação de Veículos por nível Qualis e definição, por programa, do peso de cada
> nível usado na pontuação ponderada de produções bibliográficas (RL05).
>
> **Decisões de referência:** [ADR-0003](../adr/0003-pesos-qualis-versionados-por-programa.md) —
> pesos Qualis versionados por programa, pontuação fixada na data de publicação.

---

## US-VQ01 — Classificar um veículo em um nível Qualis

**Como** coordenador,
**quero** classificar um veículo em um nível Qualis,
**para que** o sistema possa usar esse nível na pontuação ponderada das produções bibliográficas (RL05).

**Critérios de Aceitação:**
- O nível aceita os valores **A1, A2, A3, A4, A5, A6, A7, A8** e um **fallback** ("Sem Classificação") para veículo ainda não classificado.
- A classificação é por programa (vive em `programs/{id}/vehicle_levels/`); o mesmo veículo pode ter níveis distintos em programas distintos.
- Ao salvar, o nível é persistido e passa a alimentar os fatos da RL05.

---

## US-VQ02 — Definir o peso de cada nível Qualis no meu programa

**Como** coordenador,
**quero** definir o peso de cada nível Qualis (A1–A8 e fallback) no meu programa,
**para que** a pontuação das produções reflita a política de avaliação vigente do programa.

**Critérios de Aceitação:**
- Cada coordenador define os pesos **apenas do seu próprio programa** (escopo por `programa_id`).
- Os pesos são a base do cálculo da RL05 (`score = pontuacao_base × peso`).
- A alteração de pesos cria uma **nova versão vigente**, sem sobrescrever a anterior (ver US-VQ03).

---

## US-VQ03 — Versionar e auditar mudanças de peso

**Como** coordenador,
**quero** que cada mudança de pesos seja registrada como uma nova versão com autor e data,
**para que** exista histórico de quem mudou o quê e quando, e produções antigas não sejam afetadas.

**Critérios de Aceitação:**
- Cada conjunto de pesos é armazenado de forma **versionada**, carregando `vigente_desde`, `alterado_por` e `alterado_em`.
- Produções **publicadas antes** de uma mudança mantêm a pontuação calculada com o peso vigente **na data de publicação** — uma nova versão de pesos nunca reescreve scores de produções já publicadas.
- Produção ainda **não publicada** (`submetido`/`aceito`) usa o peso **vigente atual** (provisório); ao ser publicada, o peso fica travado na versão vigente naquela data.
- O histórico de versões fica visível à coordenação.

---

## US-VQ04 — Registrar métricas descritivas de qualidade do veículo

**Como** coordenador,
**quero** registrar Índice H, Percentil Scopus e Fator de Impacto JCR de um veículo,
**para que** essas métricas auxiliem a avaliação manual da relevância — **sem** alterar a pontuação da RL05.

**Critérios de Aceitação:**
- `indice_h` (inteiro positivo), `percentil_scopus` (decimal 0–100) e `jcr` (decimal positivo) são campos **opcionais e puramente descritivos**: não entram no cálculo da RL05.
- O campo **JCR** só é exibido/habilitado quando o tipo do veículo for **revista**; para **evento**, fica oculto (não aplicável).
- A validação "JCR só para revista" ocorre no **service layer**, não no router.
- Campos não preenchidos são exibidos como "—".

---

## US-VQ05 — Visualizar métricas de qualidade ao consultar um veículo

**Como** orientador ou coordenador,
**quero** ver, na tela de detalhes de um veículo, o nível Qualis e as métricas descritivas disponíveis (Índice H, Percentil Scopus e JCR quando aplicável),
**para que** eu possa avaliar rapidamente a relevância de uma produção bibliográfica associada a esse veículo.

**Critérios de Aceitação:**
- A tela de detalhes exibe, em seção dedicada: nível Qualis, Índice H, Percentil Scopus e, quando aplicável, JCR.
- Campos não preenchidos são exibidos como "—" (não ocultados).
- Discentes e orientadores têm acesso de leitura a essa tela; apenas coordenadores podem editar nível, pesos e métricas.

---

## Notas de Implementação

- O nível do veículo permanece em `programs/{id}/vehicle_levels/`; a escala passa de 7 níveis (`A1–A4, B1, B2, SC`) para **A1–A8 + fallback**, substituindo a fonte global estática `PESO_POR_NIVEL` (ver ADR-0003, que supera R1/R4 de `data-model-decisions.md`).
- Os pesos por nível deixam de ser constante de código e passam a config **versionada por programa** (`vigente_desde`, `alterado_por`, `alterado_em`).
- A RL05 (`production_scoring.py`) **não muda de forma** — continua `score = base × peso`; quem muda é o `inference_service`, que resolve o peso vigente na **data de publicação** da produção e o injeta como fato (motor segue isolado).
- `seed_firestore`, fixtures e testes RL05 precisam refletir a nova escala e a resolução de peso por data.
- `indice_h`, `percentil_scopus` e `jcr` são metadados do veículo, **fora** da RL05.

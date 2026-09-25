# `extensions` como coleção raiz

> **Status:** aceita e implementada. A decisão foi levantada na revisão do PR #174 e já
> está realizada no `development` pelo #326 — cujo `extension_repository.py` aponta para a
> coleção raiz `extensions/` (`super().__init__("extensions")`). Esta ADR registra a
> justificativa escrita, que faltava, sem alterar o comportamento em vigor.

Fixamos `extensions` (prorrogações) como **coleção raiz** chaveada por `auto-id`, com
`student_id`/`aluno_id`, `requester_id` e `programa_id` como **campos** do documento — e
**não** como sub-coleção de `students/{id}/extensions`. Esta ADR reconcilia a contradição
levantada na revisão do PR #174 (achado M3): a decisão Q12 do
[`data-model-decisions.md`](../data-model-decisions.md) descrevia `extensions` como
"composição (1:N)" a partir de `students`, enquanto o schema canônico e a Spec 08 tratam-na
como coleção raiz.

Decidimos pela raiz porque as três fontes autoritativas convergem para ela:

- **Schema canônico** — `docs/specs/03_firebase_schema.json` descreve o contrato "na coleção
  raiz `extensions/`", `documento_id: auto-id`, com `student_id` como campo de referência.
- **Data-model** — `docs/data-model.md §4` rotula a entidade explicitamente como "coleção raiz".
- **Contrato de API (Spec 08)** — `GET /extensions`, `POST /extensions`,
  `PATCH /extensions/{extension_id}/review`, `POST /extensions/{extension_id}/approve` e
  `POST /extensions/{extension_id}/reject` **não** carregam `student_id` no path; o
  `extension_id` (auto-id) identifica o documento sozinho, o que só é limpo numa coleção raiz.

A "composição (1:N)" da Q12 é apenas a **notação lógica** dos diagramas Mermaid (aninhamento
NoSQL, não FK), a mesma usada para `productions` — que a Q8/R3 já confirmaram ser **coleção
raiz**. A seta do ER permanece como relação lógica `students ||--o{ extensions`; não impõe
sub-coleção física.

## Consequências

- **Repositório aponta para `extensions/` raiz.** Elimina os proxies de sub-coleção e a
  *collection group query* (`collection_group("extensions")`) — que exigiria índice dedicado
  não previsto no modelo. Alinha com os demais repositórios de coleção raiz
  (`transfer_requests`, `productions`, `activity_types`).
- **`student_id`/`programa_id` são campos persistidos.** Habilitam consulta por aluno e por
  programa (relatórios por tenant), sem depender do path.
- **Endpoints seguem a Spec 08 sem `student_id` no path.** O `extension_id` identifica o
  documento; a posse (aluno dono / orientador do aluno) é verificada no service via os campos.
- **Q12 fica superada nesta leitura.** Registrada como R5 no `data-model-decisions.md`, que
  passa a apontar para esta ADR.

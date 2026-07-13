# Departamento como pai estrutural do Programa

Promovemos **Departamento** de um campo de texto livre (hoje digitado no perfil do
orientador/discente) para uma **entidade de primeiro nível** que sedia um ou mais
Programas: cada `programa` ganha um `departamento_id` obrigatório, e o registro de
departamentos é **global à instituição**, com CRUD exclusivo do papel `adm`.

Escolhemos esse modelo estrutural em vez da alternativa mais barata — um simples
vocabulário controlado ortogonal ao Programa — porque o domínio precisa da hierarquia
Departamento → Programa explícita.

## Consequências

- **Campo `departamento` por pessoa passa a ser derivado.** Orientadores e discentes
  não armazenam mais um departamento próprio; ele é lido de `programa.departamento_id`.
  Fonte única de verdade, sem divergência.
- **Claims do JWT permanecem `{ role, programa_id }`.** O departamento é sempre
  derivável do programa; adicioná-lo ao token seria estado redundante a sincronizar.
  A autorização (A01) continua chaveada por `programa_id`.
- **Migração:** `departamento_id` é obrigatório em `programa`. Os programas existentes
  são apontados para um Departamento default semeado no backfill.

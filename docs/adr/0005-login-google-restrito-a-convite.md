# Login com Google restrito a convite (sem token por e-mail)

O cadastro no SAGA é **exclusivamente por convite**: a coordenação/adm cria um
convite, o papel e o `programa_id` ficam ligados a ele, e a ativação (`first-access`)
nunca lê o papel do cliente. Ao adicionar "Entrar com Google", mantivemos esse portão:
o Google é apenas um **método de autenticação alternativo**, não uma via de
auto-provisionamento.

## Fluxo

1. Usuário clica "Continuar com Google" → OAuth.
2. O backend procura um **convite pendente cujo e-mail bate com a conta Google**.
3. **Com convite:** ativa a conta usando o convite (papel e `programa_id` vêm dele); a
   identidade Google passa a ser a credencial. **Não há senha nem token por e-mail** —
   o Google já verificou o e-mail, então o token de primeiro acesso seria redundante.
4. **Sem convite:** acesso negado ("e-mail sem convite; procure a coordenação"). Nenhuma
   conta, sessão ou token é criado.

## Consequências

- Um estranho com conta Google **não** consegue se auto-provisionar — o convite continua
  sendo o único ponto de atribuição de papel.
- O fluxo de token por e-mail permanece **apenas** para a ativação por senha; a via Google
  o dispensa. Existem, portanto, dois caminhos de ativação para o mesmo convite (senha+token
  e Google sem token), ambos convergindo no mesmo `first-access` que aplica os claims.

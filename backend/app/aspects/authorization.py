"""
Aspecto A01 — Autorização por Papel (Before advice).

Responsabilidades:
- Implementar o decorador @requires_role(*roles) usando mecanismos nativos do Python
  (decorador de função, sem bibliotecas externas de AOP).
- Antes de executar a função decorada:
    1. Verifica flag AUTHORIZATION_ENABLED em aspect_config; se False, passa direto.
    2. Extrai CurrentUser do contexto FastAPI (injetado pela dependência get_current_user).
    3. Verifica se user.role está em *roles; se não, lança HTTPException(403).
    4. Para join points com restrição de propriedade (aluno vê próprio, orientador vê
       orientandos): verifica relação no Firestore antes de permitir acesso.
- Join points cobertos: todos os endpoints de mutação e leitura sensível listados na
  spec 02_aspectos_aop.json > aspecto A01.
- Paradigma AOP aplicado: decorador Python como mecanismo de weaving explícito.
"""

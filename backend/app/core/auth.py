"""
Dependência FastAPI para autenticação e extração de identidade via Firebase Auth.

Responsabilidades:
- Definir o dataclass/Pydantic model CurrentUser com campos: uid, role, programa_id, email.
- Implementar a dependência assíncrona `get_current_user(authorization: str = Header(...))
  -> CurrentUser` que:
    1. Extrai o Bearer token do header Authorization.
    2. Verifica o token com firebase_admin.auth.verify_id_token().
    3. Lê os custom claims 'role' e 'programa_id' do token decodificado.
    4. Lança HTTPException(401) para token inválido/expirado.
    5. Lança HTTPException(403) se custom claims estiverem ausentes (conta não ativada).
- Ser a base sobre a qual o aspecto @requires_role (authorization.py) opera.
"""

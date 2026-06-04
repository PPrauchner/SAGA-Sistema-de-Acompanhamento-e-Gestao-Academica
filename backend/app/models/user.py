"""
Modelos Pydantic para a entidade User (perfil de usuário).

Responsabilidades:
- Definir UserBase com campos comuns: uid, email, nome, role, programa_id, ativo.
- Definir UserCreate para criação via first-access (campos: token, senha).
- Definir UserResponse para retorno em GET /api/v1/auth/me, incluindo student_id ou
  advisor_id opcionais conforme o papel do usuário.
- Mapear o documento Firestore da coleção users/{uid}, sincronizado com custom claims
  do Firebase Auth (role, programa_id).
"""

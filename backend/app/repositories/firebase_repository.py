"""
Repositório base genérico para operações no Firestore via Firebase Admin SDK.

Responsabilidades:
- Definir a classe FirebaseRepository com métodos assíncronos genéricos reutilizados por
  todos os repositórios concretos: get(collection, doc_id), create(collection, data),
  update(collection, doc_id, data), delete(collection, doc_id), query(collection,
  filters, order_by, limit).
- Encapsular o cliente Firestore assíncrono obtido de backend/app/core/firebase.py.
- Converter Timestamps do Firestore para datetime Python e vice-versa.
- Tratar DocumentNotFoundError lançando HTTPException(404) padronizada.
- Ser a única camada que importa google.cloud.firestore — todos os outros módulos
  acessam dados exclusivamente através dos repositórios concretos.
"""

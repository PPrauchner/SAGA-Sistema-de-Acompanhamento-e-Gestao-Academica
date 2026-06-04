"""
Script de seed para popular o Firestore com dados de configuração iniciais do SAGA.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Criar o documento programs/prog_default com as configurações do PPGCC: duracao_meses=24,
  creditos_grupo_basico_min=12, creditos_grupo_especifico_min=8,
  creditos_grupo_tecnologico_max=4, creditos_total_min=24, max_prorrogacoes=1,
  duracao_prorrogacao_meses=6, meses_ate_qualificacao=12.
- Popular programs/prog_default/vehicle_levels/ com os 4 níveis de relevância padrão:
  A1 (peso 2.0), A2 (peso 1.5), B (peso 1.0), C (peso 0.5).
- Popular activity_types/ com os 6 tipos de atividade padrão: Artigo Publicado (específico,
  pontuacao_base=10), Artigo Submetido (específico, 5), Disciplina Cursada (básico, 4),
  Estágio Docência (básico, 2), Software Registrado (tecnológico, 3, limite=4),
  Participação Banca (básico, 1).
- Executar uma única vez no setup do ambiente de desenvolvimento ou produção.
- Idempotente: verificar existência de documentos antes de criar para evitar duplicatas.
"""

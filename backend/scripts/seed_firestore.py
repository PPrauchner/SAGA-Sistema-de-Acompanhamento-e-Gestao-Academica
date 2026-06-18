"""
Script de seed para popular o Firestore com dados de configuração iniciais do SAGA.

Responsabilidades:
- Inicializar o Firebase Admin SDK com as credenciais do ambiente.
- Criar o documento programs/prog_default com as configurações do PPGCC: duracao_meses=24,
  creditos_grupo_basico_min=12, creditos_grupo_especifico_min=8,
  creditos_grupo_tecnologico_max=4, creditos_total_min=24, max_prorrogacoes=1,
  duracao_prorrogacao_meses=6, meses_ate_qualificacao=12.
- Popular programs/prog_default/vehicle_levels/ com os níveis de relevância padrão
  (configuráveis): A1 (peso 1.0), A2 (0.85), A3 (0.7), A4 (0.7), B1 (0.5), B2 (0.5),
  SC/Sem Classificação (0.2).
- Popular activity_types/ com os 4 tipos de atividade creditável NÃO bibliográfica:
  Disciplina Cursada (básico, 4), Estágio Docência (básico, 2),
  Software Registrado (tecnológico, 3, limite=4), Participação Banca (básico, 1).
  Publicações (artigo/livro/capítulo) são produções (subcoleção productions, RL05), não
  activity_types — a distinção publicado/submetido vive em status_publicacao.
- Executar uma única vez no setup do ambiente de desenvolvimento ou produção.
- Idempotente: verificar existência de documentos antes de criar para evitar duplicatas.
"""

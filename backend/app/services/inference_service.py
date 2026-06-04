"""
Serviço orquestrador da carga de fatos e execução do motor de inferência.

Responsabilidades:
- run_inference(student_id, programa_id) -> InferenceResult: método principal que:
    1. Carrega student do Firestore (data_ingresso, prazo_final, proficiencia_comprovada,
       qualificacao_aprovada).
    2. Carrega configurações do programa (créditos mínimos, pesos de relevância).
    3. Carrega atividades aprovadas e calcula créditos por categoria (básico, específico,
       tecnológico).
    4. Carrega tasks do plano e determina quais etapas estão concluídas.
    5. Carrega produções aprovadas e verifica ao menos 1 bibliográfica.
    6. Calcula fatos derivados temporais: prazo_estourado, prazo_qualificacao_proximo,
       plano_atrasado, qualificacao_pendente, creditos_insuficientes.
    7. Monta FactBase com todos os fatos coletados.
    8. Instancia InferenceEngine (de backend/inference_engine/) com FactBase + RuleBase.
    9. Executa queries: apto_defesa, creditos_validos, em_risco, atividades_elegiveis,
       pontuacoes_producoes.
   10. Persiste snapshot em students/{id}/inferred_status/ e atualiza situacao_inferida.
- É o único módulo que instancia o InferenceEngine — outros serviços não acessam o motor
  diretamente.
"""

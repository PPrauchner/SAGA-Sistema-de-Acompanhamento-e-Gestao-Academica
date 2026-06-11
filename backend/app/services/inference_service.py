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
from backend.app.repositories.program_repository import ProgramRepository
from backend.inference_engine.terms import Compound, Atom
from backend.inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine

class InferenceService:
    """Serviço responsável por coordenar a carga de dados e executar o motor lógico."""

    def __init__(self):
        self._program_repo = ProgramRepository()

    async def _load_program_facts(self, programa_id: str) -> list[Compound]:
        """Carrega as configurações do programa e converte em fatos para o motor.

        Args:
            programa_id: O ID do programa.

        Returns:
            Lista de fatos (Compound) configurando os limites de créditos.
        """
        config = await self._program_repo.get_by_id(programa_id)
        if not config:
            return []

        prog_atom = Atom(programa_id)
        return [
            Compound("min_creditos_basico", [prog_atom, Atom(config.creditos_grupo_basico_min)]),
            Compound("min_creditos_especifico", [prog_atom, Atom(config.creditos_grupo_especifico_min)]),
            Compound("max_creditos_tecnologico", [prog_atom, Atom(config.creditos_grupo_tecnologico_max)]),
            Compound("min_creditos_total", [prog_atom, Atom(config.creditos_total_min)]),
        ]

    async def run_inference(self, student_id: str, programa_id: str) -> dict[str, bool]:
        """Orquestra a carga de dados do aluno e executa as inferências do motor lógico.

        Args:
            student_id: ID do aluno.
            programa_id: ID do programa do qual o aluno faz parte.

        Returns:
            Dicionário com os resultados booleanos das inferências (ex: creditos_validos).
        """
        # 1. Carregar configurações em formato de fatos lógicos
        program_facts = await self._load_program_facts(programa_id)
        
        # 2. Instanciar FactBase e RuleBase
        fact_base = FactBase()
        for fact in program_facts:
            fact_base.add_fact(fact)
            
        rule_base = RuleBase()
        
        # 3. Instanciar o motor
        engine = InferenceEngine(fact_base, rule_base)
        
        # 4. Executar as consultas (queries)
        student_atom = Atom(student_id)
        
        creditos_validos = engine.query_bool(Compound("creditos_validos", [student_atom]))
        
        return {
            "creditos_validos": creditos_validos
        }



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

from __future__ import annotations

from typing import Any

from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine
from inference_engine.rules import register_all
from inference_engine.terms import Atom, Compound


class InferenceService:
    """Orquestrador do motor de inferência."""

    async def validate_activity_eligibility(
        self,
        activity_id: str,
        student_id: str,
        fatos: dict[str, bool],
    ) -> bool:
        """Valida RL04 (elegibilidade de atividade) com os 4 fatos preliminares.

        Join Point: chamado por ActivityService.submit_activity() após validações básicas.
        Fatos esperados em `fatos`:
        - dentro_periodo_curso: bool
        - tem_comprovante: bool
        - tipo_ativo: bool
        - nao_excede_limite_categoria: bool

        Args:
            activity_id: ID da atividade.
            student_id: UID do aluno.
            fatos: Dict com os 4 booleanos dos fatos de RL04.

        Returns:
            True se atividade_elegivel(activity_id, student_id) é verdadeiro.
        """
        fb = FactBase()
        rb = RuleBase()
        register_all(rb)

        if fatos.get("dentro_periodo_curso"):
            fb.add_fact(
                Compound("dentro_periodo_curso", [Atom(activity_id), Atom(student_id)])
            )
        if fatos.get("tem_comprovante"):
            fb.add_fact(Compound("tem_comprovante", [Atom(activity_id)]))
        if fatos.get("tipo_ativo"):
            fb.add_fact(Compound("tipo_ativo", [Atom(activity_id)]))
        if fatos.get("nao_excede_limite_categoria"):
            fb.add_fact(
                Compound(
                    "nao_excede_limite_categoria",
                    [Atom(activity_id), Atom(student_id)],
                )
            )

        engine = InferenceEngine(fb, rb)
        goal = Compound("atividade_elegivel", [Atom(activity_id), Atom(student_id)])
        results = engine.query(goal)
        return len(results) > 0

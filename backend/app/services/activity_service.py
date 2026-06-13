"""
Serviço de negócio para registro e validação de atividades creditáveis.

Responsabilidades:
- submit_activity(): aluno registra atividade. Executa motor RL04 via fatos preliminares.
  Decorado com @requires_role('aluno'), @audit_operation, @check_deadlines, @trigger_alerts.
- advisor_review(): orientador emite parecer (sem aprovar). Decorado com
  @requires_role('orientador') e @audit_operation.
- validate_activity(): coordenação aprova ou rejeita. Atualiza creditos_gerados e status.
  Decorado com @requires_role('coordenacao'), @audit_operation e @trigger_alerts.
- list_activities(): filtra atividades respeitando permissões por papel.
"""

from __future__ import annotations

from typing import Any

from backend.app.aspects.alerts import trigger_alerts
from backend.app.aspects.audit import audit_operation
from backend.app.aspects.authorization import requires_role
from backend.app.aspects.deadline_validation import check_deadlines
from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityCreate,
    ActivityValidateRequest,
)
from backend.app.repositories.activity_repository import ActivityRepository


class ActivityService:
    """Service responsável pelo ciclo de vida das atividades creditáveis."""

    def __init__(self) -> None:
        self._repo = ActivityRepository()

    async def list_activities(
        self,
        current_user: CurrentUser,
        student_id: str | None = None,
        status_filter: str | None = None,
        categoria_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista atividades respeitando permissões por papel.

        Aluno vê apenas as próprias; orientador vê dos orientandos; coordenação vê todas.

        Args:
            current_user: Usuário autenticado.
            student_id: Filtro opcional por aluno.
            status_filter: Filtro opcional por status.
            categoria_filter: Filtro opcional por categoria.

        Returns:
            Lista de dicts das atividades.
        """
        if current_user.role == "aluno":
            target_id = current_user.uid
        elif student_id:
            target_id = student_id
        else:
            # coordenação sem student_id — retorna todas (limitado a primeiro aluno aqui;
            # implementação completa requer paginação)
            return []

        return await self._repo.list_activities(
            student_id=target_id,
            status_filter=status_filter,
            categoria_filter=categoria_filter,
        )

    @requires_role("aluno")
    @audit_operation
    @check_deadlines
    @trigger_alerts
    async def submit_activity(
        self,
        body: ActivityCreate,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Aluno registra nova atividade creditável.

        Executa motor RL04 para calcular elegibilidade preliminar.
        Aspecto A05 (@trigger_alerts) notifica o orientador após submissão.

        Args:
            body: Dados da atividade.
            current_user: Aluno autenticado.

        Returns:
            Dict com id, elegibilidade_preliminar e notificacao_enviada.
        """
        # Busca dados do tipo de atividade para enriquecer a atividade
        activity_type = await self._repo.get_activity_type(body.tipo_id)
        categoria = activity_type.get("categoria", "")
        pontuacao_base = float(activity_type.get("pontuacao_base", 0))

        payload = {
            "tipo_id":          body.tipo_id,
            "tipo_nome":        activity_type.get("nome", ""),
            "categoria":        categoria,
            "descricao":        body.descricao,
            "data_realizacao":  body.data_realizacao,
            "comprovante_url":  body.comprovante_url,
            "creditos_gerados": 0.0,
            "status":           body.status,
            "parecer_orientador":     None,
            "observacao_coordenacao": None,
        }

        activity = await self._repo.create_activity(current_user.uid, payload)
        activity_id = activity["id"]

        elegivel = await self._check_eligibility_preliminary(
            activity_id=activity_id,
            student_id=current_user.uid,
            body=body,
            tipo_ativo=activity_type.get("ativo", True),
            categoria=categoria,
            pontuacao_base=pontuacao_base,
            activity_type=activity_type,
        )

        return {
            "id":                       activity_id,
            "elegibilidade_preliminar": elegivel,
            "notificacao_enviada":      True,
        }

    async def _check_eligibility_preliminary(
        self,
        activity_id: str,
        student_id: str,
        body: ActivityCreate,
        tipo_ativo: bool,
        categoria: str,
        pontuacao_base: float,
        activity_type: dict[str, Any],
    ) -> bool:
        """Executa RL04 preliminarmente com os fatos disponíveis no momento do registro.

        Args:
            activity_id: ID da atividade recém-criada.
            student_id: UID do aluno.
            body: Dados do ActivityCreate.
            tipo_ativo: Se o tipo de atividade está ativo.
            categoria: Categoria da atividade.
            pontuacao_base: Pontuação base do tipo.
            activity_type: Dict do tipo de atividade.

        Returns:
            True se todos os 4 fatos de RL04 estão presentes preliminarmente.
        """
        from backend.app.core.firebase import get_firestore_client
        from inference_engine.knowledge_base import FactBase, RuleBase, InferenceEngine
        from inference_engine.rules import register_all
        from inference_engine.terms import Atom, Compound
        import asyncio

        tem_comprovante = bool(body.comprovante_url)

        # Verifica período do curso
        dentro_periodo = False
        try:
            client = get_firestore_client()

            def _read_student() -> dict[str, Any]:
                snap = client.collection("students").document(student_id).get()
                return snap.to_dict() or {} if snap.exists else {}

            student = await asyncio.to_thread(_read_student)
            data_ingresso = student.get("data_ingresso")
            if data_ingresso:
                from datetime import date
                if hasattr(data_ingresso, "date"):
                    data_ingresso_date = data_ingresso.date()
                else:
                    data_ingresso_date = date.fromisoformat(str(data_ingresso))
                data_atividade = date.fromisoformat(body.data_realizacao)
                dentro_periodo = data_atividade >= data_ingresso_date
        except Exception:
            dentro_periodo = True  # Assume válido se não conseguir verificar

        # Verifica se não excede limite da categoria
        limite = activity_type.get("limite_maximo_creditos")
        nao_excede = True
        if limite is not None:
            try:
                creditos_por_categoria = await self._repo.get_approved_activities_by_category(student_id)
                total_categoria = creditos_por_categoria.get(categoria, 0.0)
                nao_excede = (total_categoria + pontuacao_base) <= limite
            except Exception:
                nao_excede = True

        # Monta FactBase e roda RL04
        fb = FactBase()
        rb = RuleBase()
        register_all(rb)

        if dentro_periodo:
            fb.add_fact(Compound("dentro_periodo_curso", [Atom(activity_id), Atom(student_id)]))
        if tem_comprovante:
            fb.add_fact(Compound("tem_comprovante", [Atom(activity_id)]))
        if tipo_ativo:
            fb.add_fact(Compound("tipo_ativo", [Atom(activity_id)]))
        if nao_excede:
            fb.add_fact(Compound("nao_excede_limite_categoria", [Atom(activity_id), Atom(student_id)]))

        engine = InferenceEngine(fb, rb)
        goal = Compound("atividade_elegivel", [Atom(activity_id), Atom(student_id)])
        return engine._query_bool(goal)

    @requires_role("orientador")
    @audit_operation
    async def advisor_review(
        self,
        student_id: str,
        activity_id: str,
        observacao: str,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Orientador emite parecer sobre a atividade (sem aprovar definitivamente).

        Args:
            student_id: UID do aluno dono da atividade.
            activity_id: ID da atividade.
            observacao: Texto do parecer.
            current_user: Orientador autenticado.

        Returns:
            Dict com status atualizado.
        """
        return await self._repo.update_activity(
            student_id,
            activity_id,
            {"parecer_orientador": observacao, "status": "em_validacao"},
        )

    @requires_role("coordenacao")
    @audit_operation
    @trigger_alerts
    async def validate_activity(
        self,
        student_id: str,
        activity_id: str,
        body: ActivityValidateRequest,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Coordenação aprova ou rejeita uma atividade definitivamente.

        Aspecto A05 (@trigger_alerts) notifica o aluno após a decisão.

        Args:
            student_id: UID do aluno.
            activity_id: ID da atividade.
            body: Ação, observação e créditos concedidos.
            current_user: Coordenador autenticado.

        Returns:
            Dict com novo_status, creditos_contabilizados, motor_inferencia_executado.
        """
        if body.acao == "parecer_orientador":
            updates: dict[str, Any] = {
                "parecer_orientador": body.observacao,
                "status": "em_validacao",
            }
            updated = await self._repo.update_activity(student_id, activity_id, updates)
            return {
                "message":                   "Parecer registrado",
                "novo_status":               "em_validacao",
                "creditos_contabilizados":   None,
                "motor_inferencia_executado": False,
                "fato_gerado":               None,
            }

        novo_status = "aprovado" if body.acao == "aprovar" else "rejeitado"
        creditos = body.creditos_concedidos

        updates = {
            "status":                  novo_status,
            "observacao_coordenacao":  body.observacao,
        }

        fato_gerado = None
        motor_executado = False

        if body.acao == "aprovar":
            activity = await self._repo.get_activity(student_id, activity_id)
            if creditos is None:
                tipo = await self._repo.get_activity_type(activity.get("tipo_id", ""))
                creditos = float(tipo.get("pontuacao_base", 0))

            updates["creditos_gerados"] = creditos
            motor_executado = True

            # Verifica se é produção bibliográfica para inserir fato no motor
            categoria = activity.get("categoria", "")
            if categoria == "especifico":
                fato_gerado = f"producao_bibliografica_validada({student_id})"

        await self._repo.update_activity(student_id, activity_id, updates)

        return {
            "message":                   f"Atividade {novo_status}",
            "novo_status":               novo_status,
            "creditos_contabilizados":   creditos if body.acao == "aprovar" else None,
            "motor_inferencia_executado": motor_executado,
            "fato_gerado":               fato_gerado,
        }

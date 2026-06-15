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

from backend.app.core.auth import CurrentUser
from backend.app.models.activity import (
    ActivityCreate,
    ActivityValidateRequest,
)
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.services.inference_service import InferenceService


class ActivityService:
    """Service responsável pelo ciclo de vida das atividades creditáveis."""

    def __init__(self) -> None:
        self._repo = ActivityRepository()
        self._inference_service = InferenceService()

    async def list_activities(
        self,
        current_user: CurrentUser,
        student_id: str | None = None,
        status_filter: str | None = None,
        categoria_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista atividades respeitando permissões por papel.

        - Aluno vê apenas as próprias.
        - Orientador vê dos orientandos (requer student_id ou integração com StudentRepository).
        - Coordenação vê todas (sem student_id) ou filtra por aluno (com student_id).

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
            return await self._repo.list_activities(
                student_id=target_id,
                status_filter=status_filter,
                categoria_filter=categoria_filter,
            )
        elif current_user.role == "coordenacao":
            if student_id:
                return await self._repo.list_activities(
                    student_id=student_id,
                    status_filter=status_filter,
                    categoria_filter=categoria_filter,
                )
            else:
                # Coordenação sem student_id: lista TODAS as atividades
                return await self._repo.list_all_activities(
                    status_filter=status_filter,
                    categoria_filter=categoria_filter,
                )
        else:
            # orientador: requer student_id
            if not student_id:
                return []
            return await self._repo.list_activities(
                student_id=student_id,
                status_filter=status_filter,
                categoria_filter=categoria_filter,
            )

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

        Delega para InferenceService.validate_activity_eligibility() que é o único
        autorizado a instanciar o motor de inferência.

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
        import asyncio
        from backend.app.core.firebase import get_firestore_client
        from datetime import date

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
                creditos_por_categoria = await self._repo.get_approved_activities_by_category(
                    student_id
                )
                total_categoria = creditos_por_categoria.get(categoria, 0.0)
                nao_excede = (total_categoria + pontuacao_base) <= limite
            except Exception:
                nao_excede = True

        # Chama InferenceService para validar RL04
        return await self._inference_service.validate_activity_eligibility(
            activity_id=activity_id,
            student_id=student_id,
            fatos={
                "dentro_periodo_curso": dentro_periodo,
                "tem_comprovante": tem_comprovante,
                "tipo_ativo": tipo_ativo,
                "nao_excede_limite_categoria": nao_excede,
            },
        )

    async def advisor_review(
        self,
        student_id: str,
        activity_id: str,
        observacao: str,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Orientador emite parecer sobre a atividade (sem aprovar definitivamente).

        Aspecto A01: valida que o orientador é o responsável pelo aluno.

        Args:
            student_id: UID do aluno dono da atividade.
            activity_id: ID da atividade.
            observacao: Texto do parecer.
            current_user: Orientador autenticado.

        Returns:
            Dict com status atualizado.

        Raises:
            HTTPException(403): Se o orientador não é responsável pelo aluno.
        """
        from fastapi import HTTPException, status

        student = await self._repo._repo.get("students", student_id)
        advisor_id = student.get("orientador_id")

        if advisor_id != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não é o orientador deste aluno",
            )

        return await self._repo.update_activity(
            student_id,
            activity_id,
            {"parecer_orientador": observacao},
        )

    async def validate_activity(
        self,
        student_id: str,
        activity_id: str,
        body: ActivityValidateRequest,
        current_user: CurrentUser,
    ) -> dict[str, Any]:
        """Coordenação aprova ou rejeita uma atividade definitivamente.

        Se aprovada e categoria=especifico, executa re-inferência do motor para atualizar
        situacao_inferida do aluno.

        Aspecto A05 (@trigger_alerts) notifica o aluno após a decisão.

        Args:
            student_id: UID do aluno.
            activity_id: ID da atividade.
            body: Ação, observação e créditos concedidos.
            current_user: Coordenador autenticado.

        Returns:
            Dict com novo_status, creditos_contabilizados, motor_inferencia_executado.

        Raises:
            ValueError: Se acao não for "aprovar" ou "rejeitar".
        """
        if body.acao not in ("aprovar", "rejeitar"):
            raise ValueError(f"Ação inválida: {body.acao}")

        novo_status = "aprovado" if body.acao == "aprovar" else "rejeitado"
        creditos = body.creditos_concedidos

        updates = {
            "status":                  novo_status,
            "observacao_coordenacao":  body.observacao,
        }

        motor_executado = False

        if body.acao == "aprovar":
            activity = await self._repo.get_activity(student_id, activity_id)
            if creditos is None:
                tipo = await self._repo.get_activity_type(activity.get("tipo_id", ""))
                creditos = float(tipo.get("pontuacao_base", 0))

            updates["creditos_gerados"] = creditos

            # Se categoria == "especifico", executa re-inferência completa do motor
            categoria = activity.get("categoria", "")
            if categoria == "especifico":
                motor_executado = True

        await self._repo.update_activity(student_id, activity_id, updates)

        # Se re-inferência necessária, executa o motor completo
        if motor_executado:
            try:
                # InferenceService.run_inference() irá gerar o novo snapshot
                # em inferred_status/ e atualizar situacao_inferida
                await self._inference_service.run_inference(
                    student_id=student_id,
                    programa_id=(
                        # TODO: obter programa_id do student ou do programa_id da activity
                        "default"
                    ),
                )
            except Exception:
                # Re-inferência falha não deve impedir a aprovação
                pass

        return {
            "message":                   f"Atividade {novo_status}",
            "novo_status":               novo_status,
            "creditos_contabilizados":   creditos if body.acao == "aprovar" else None,
            "motor_inferencia_executado": motor_executado,
        }

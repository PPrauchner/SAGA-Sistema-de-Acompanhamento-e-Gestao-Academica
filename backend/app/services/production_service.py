"""
Serviço de negócio para registro e pontuação de produções bibliográficas.

Responsabilidades:
- create_production(): cria a produção na sub-coleção students/{id}/productions e executa o
  motor RL05 (via InferenceService.score_production) para gravar pontuacao_calculada,
  nivel_veiculo e peso_aplicado a partir do nível de relevância do veículo.
- list_productions(): lista produções visíveis ao usuário (reaproveita a visibilidade de
  StudentService) enriquecidas com veiculo_nome, nível e pontuação.

Acoplamento com atividade (#45) DEFERIDO: a produção é subtipo de atividade e deveria
referenciar um activity_id e herdar o fluxo rascunho→enviado→aprovado. Enquanto a #45
(ActivityService/activity_types) não existe, o activity_id fica None e a pontuacao_base é
resolvida por _resolve_pontuacao_base() (artigo modulado por status_publicacao; livro e
capítulo com base única). Toda essa interinidade está isolada
em create_production() para reconciliação localizada quando a #45 entrar.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.production import ProductionCreate
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.repositories.vehicle_repository import VehicleRepository
from backend.app.services.inference_service import InferenceService
from backend.app.services.student_service import StudentService

# Pontuação base por NATUREZA bibliográfica da produção. Publicações não são activity_types
# (modelo de produção bibliográfica isolado); a #45 dará à produção um activity_id para também
# gerar crédito. Para artigo a situação de publicação modula a base; livro e capítulo têm base única.
PONTUACAO_BASE_ARTIGO_POR_STATUS: dict[str, float] = {
    "publicado": 1.0,
    "aceito": 0.8,
    "submetido": 0.3,
}
PONTUACAO_BASE_POR_TIPO: dict[str, float] = {
    "livro": 1.0,
    "capitulo": 0.6,
}


def _resolve_pontuacao_base(tipo_producao: str, status_publicacao: str) -> float:
    """Resolve a pontuação base de uma produção a partir da sua natureza e situação.

    Args:
        tipo_producao: Natureza da produção ('artigo' | 'livro' | 'capitulo').
        status_publicacao: Situação de publicação ('publicado' | 'submetido' | 'aceito').

    Returns:
        Pontuação base: para 'artigo' depende de status_publicacao; para os demais tipos
        é única.
    """
    if tipo_producao == "artigo":
        return PONTUACAO_BASE_ARTIGO_POR_STATUS[status_publicacao]
    return PONTUACAO_BASE_POR_TIPO[tipo_producao]


class ProductionService:
    """Serviço de negócio para produções bibliográficas e pontuação RL05."""

    def __init__(self) -> None:
        self._productions = ProductionRepository()
        self._vehicles = VehicleRepository()
        self._students_service = StudentService()
        self._inference = InferenceService(InferenceRepository())

    async def _resolve_student_id(self, user: CurrentUser) -> str:
        """Resolve o id do documento do aluno a partir do uid autenticado."""
        students = await self._students_service.list_students(user)
        student = next((s for s in students if s.get("uid") == user.uid), None)
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado para o usuário atual",
            )
        return student["id"]

    async def _resolve_vehicle_level(
        self,
        programa_id: str,
        veiculo_id: str,
    ) -> tuple[str, float]:
        """Resolve (nivel, peso) do veículo a partir de programs/{id}/vehicle_levels/."""
        levels = await self._vehicles.list_levels(programa_id)
        level = next((lv for lv in levels if lv["id"] == veiculo_id), None)
        if level is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Veículo sem nível de relevância configurado",
            )
        return level["nivel"], float(level["peso"])

    async def create_production(self, data: ProductionCreate, user: CurrentUser) -> dict:
        student_id = await self._resolve_student_id(user)
        nivel, peso = await self._resolve_vehicle_level(user.programa_id, data.veiculo_id)
        pontuacao_base = _resolve_pontuacao_base(data.tipo_producao, data.status_publicacao)

        score = self._inference.score_production(nivel, peso, pontuacao_base)

        production_id = await self._productions.create(
            student_id,
            {
                # Acoplamento de atividade deferido para a #45.
                "activity_id": None,
                "status": "enviado",
                "titulo": data.titulo,
                "doi": data.doi,
                "veiculo_id": data.veiculo_id,
                "tipo_producao": data.tipo_producao,
                "status_publicacao": data.status_publicacao,
                "observacao": data.observacao,
                "autores": [user.uid],
                "data_realizacao": data.data_realizacao,
                "comprovante_url": data.comprovante_url,
                "pontuacao_base": pontuacao_base,
                "pontuacao_calculada": score,
                "nivel_veiculo": nivel,
                "peso_aplicado": peso,
                "criado_em": datetime.now(timezone.utc),
            },
        )

        return {
            "id": production_id,
            "activity_id": None,
            "pontuacao_calculada": score,
            "nivel_veiculo": nivel,
            "peso_aplicado": peso,
        }

    async def list_productions(self, user: CurrentUser) -> list[dict]:
        students = await self._students_service.list_students(user)
        vehicles = await self._vehicles.list_all()
        nome_by_vehicle = {v["id"]: v.get("nome", "") for v in vehicles}

        result: list[dict] = []
        for student in students:
            productions = await self._productions.list_by_student(student["id"])
            for production in productions:
                result.append(
                    {
                        "id": production["id"],
                        # aluno_id deriva do dono da subcoleção students/{id}/productions,
                        # não de `autores` (que admite coautores).
                        "aluno_id": student["id"],
                        "aluno_nome": student.get("nome", ""),
                        "titulo": production.get("titulo"),
                        "doi": production.get("doi"),
                        "veiculo_nome": nome_by_vehicle.get(production.get("veiculo_id"), ""),
                        "nivel_veiculo": production.get("nivel_veiculo", ""),
                        "tipo_producao": production.get("tipo_producao"),
                        "status_publicacao": production.get("status_publicacao"),
                        "observacao": production.get("observacao"),
                        "pontuacao_calculada": production.get("pontuacao_calculada", 0.0),
                        "peso_aplicado": production.get("peso_aplicado", 0.0),
                        "status_atividade": production.get("status", ""),
                    }
                )
        return result

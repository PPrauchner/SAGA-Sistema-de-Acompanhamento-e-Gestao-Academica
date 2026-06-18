"""
Serviço de negócio para registro e pontuação de produções bibliográficas.

Responsabilidades:
- create_production(): cria a produção na sub-coleção students/{id}/productions e executa o
  motor RL05 (via InferenceService.score_production) para gravar pontuacao_calculada,
  nivel_veiculo e peso_aplicado a partir do nível de relevância do veículo.
- list_productions(): lista produções visíveis ao usuário (reaproveita a visibilidade de
  StudentService) enriquecidas com veiculo_nome, nível e pontuação.

Acoplamento com atividade (#45): a produção é subtipo de atividade. create_production()
grava uma atividade dedicada em students/{id}/activities (categoria
'producao_bibliografica', sem tipo_id de activity_types — o request de produção não envia
tipo) e referencia o activity_id gerado, fazendo a produção herdar o fluxo
rascunho→enviado→aprovado. A pontuacao_base bibliográfica é resolvida por
_resolve_pontuacao_base() (artigo modulado por status_publicacao; livro e capítulo com base
única) e alimenta tanto o RL05 quanto os creditos_gerados da atividade.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.production import ProductionCreate
from backend.app.repositories.activity_repository import ActivityRepository
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

# Categoria da atividade dedicada criada para cada produção bibliográfica. Não vem de
# activity_types (a produção não tem tipo_id); identifica a atividade como subtipo produção.
ACTIVITY_CATEGORIA_PRODUCAO = "producao_bibliografica"


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
        self._activities = ActivityRepository()
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
        now = datetime.now(timezone.utc)

        activity_id = await self._create_linked_activity(student_id, data, pontuacao_base, now)

        production_id = await self._productions.create(
            student_id,
            {
                "activity_id": activity_id,
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
                "criado_em": now,
            },
        )

        return {
            "id": production_id,
            "activity_id": activity_id,
            "pontuacao_calculada": score,
            "nivel_veiculo": nivel,
            "peso_aplicado": peso,
        }

    async def _create_linked_activity(
        self,
        student_id: str,
        data: ProductionCreate,
        pontuacao_base: float,
        now: datetime,
    ) -> str:
        """Cria a atividade dedicada (subtipo produção) e retorna o activity_id gerado.

        A produção é subtipo de atividade: grava um documento em students/{id}/activities sem
        tipo_id de activity_types (o request de produção não envia tipo), com categoria fixa
        ACTIVITY_CATEGORIA_PRODUCAO e o mesmo formato das atividades regulares, para herdar o
        fluxo rascunho→enviado→aprovado e a validação do orientador.

        Args:
            student_id: ID do aluno dono da produção/atividade.
            data: Dados da produção registrada.
            pontuacao_base: Pontuação base bibliográfica (RL05), gravada em creditos_gerados.
            now: Timestamp de criação, compartilhado com o documento de produção.

        Returns:
            ID do documento de atividade recém-criado.
        """
        return await self._activities.create_activity(
            student_id,
            {
                "tipo_id": None,
                "aluno_id": student_id,
                "categoria": ACTIVITY_CATEGORIA_PRODUCAO,
                "descricao": data.titulo,
                "data_realizacao": data.data_realizacao,
                "comprovante_url": data.comprovante_url,
                "creditos_gerados": pontuacao_base,
                "creditos_concedidos": None,
                "status": "enviado",
                "parecer_orientador": None,
                "observacao_coordenacao": None,
                "validado_por": None,
                "validado_em": None,
                "criado_em": now,
                "atualizado_em": now,
            },
        )

    async def list_productions(self, user: CurrentUser) -> list[dict]:
        students = await self._students_service.list_students(user)
        vehicles = await self._vehicles.list_all()
        nome_by_vehicle = {v["id"]: v.get("nome", "") for v in vehicles}

        result: list[dict] = []
        for student in students:
            productions = await self._productions.list_by_student(student["id"])
            activities = await self._activities.list_by_student(student["id"])
            status_by_activity = {a["id"]: a.get("status", "") for a in activities}
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
                        # status_atividade vem da atividade ligada (fonte do fluxo de
                        # validação); cai no status da própria produção para docs antigos.
                        "status_atividade": status_by_activity.get(
                            production.get("activity_id"), production.get("status", "")
                        ),
                    }
                )
        return result

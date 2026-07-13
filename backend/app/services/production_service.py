"""
Serviço de negócio para registro e pontuação de produções bibliográficas.

Responsabilidades:
- create_production(): cria a produção na coleção raiz productions/ e executa o motor RL05
  (via InferenceService.score_production) para gravar pontuacao_calculada, nivel_veiculo e
  peso_aplicado a partir do nível de relevância do veículo.
- list_productions(): lista produções visíveis ao usuário (reaproveita a visibilidade de
  StudentService) enriquecidas com veiculo_nome, nível e pontuação.

Acoplamento com atividade (FK invertida): a produção é coleção raiz e cada aluno autor tem
uma atividade dedicada em students/{id}/activities com activities.producao_id apontando para
productions/{id} (categoria 'producao_bibliografica', sem tipo_id de activity_types — o
request de produção não envia tipo), por onde herda o fluxo rascunho→enviado→aprovado. Em
co-autoria, cria-se uma atividade por autor que seja uid de aluno cadastrado. A
pontuacao_base bibliográfica é resolvida por _resolve_pontuacao_base() (artigo modulado por
status_publicacao; livro e capítulo com base única) e alimenta o RL05; a pontuacao_calculada
resultante é o default de creditos_gerados de cada atividade (ajustável via
creditos_concedidos pela coordenação).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from backend.app.core.auth import CurrentUser
from backend.app.models.production import ProductionCreate
from backend.app.repositories.activity_repository import ActivityRepository
from backend.app.repositories.advisor_repository import AdvisorRepository
from backend.app.repositories.inference_repository import InferenceRepository
from backend.app.repositories.production_repository import ProductionRepository
from backend.app.repositories.student_repository import StudentRepository
from backend.app.repositories.vehicle_repository import VehicleRepository
from backend.app.services.inference_service import InferenceService
from backend.app.services.qualis_weights_service import QualisWeightsService
from backend.app.services.student_service import StudentService

# Pontuação base por NATUREZA bibliográfica da produção. Publicações não são activity_types
# (modelo de produção bibliográfica isolado); cada autor cadastrado recebe uma atividade com
# FK producao_id que gera crédito. Para artigo a situação de publicação modula a base; livro e
# capítulo têm base única.
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
        self._advisors = AdvisorRepository()
        self._vehicles = VehicleRepository()
        self._students = StudentRepository()
        self._students_service = StudentService()
        self._inference = InferenceService(InferenceRepository())
        self._qualis_weights = QualisWeightsService()

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
        # Resolução de co-autores precisa enxergar todo aluno cadastrado no programa, não só
        # os visíveis ao papel do usuário atual: StudentService.list_students(user) escopa a
        # visibilidade por papel (um 'aluno' só vê a si mesmo), o que faria co-autores
        # cadastrados nunca serem encontrados. StudentRepository.list_by_program() é a leitura
        # não-escopada correta aqui (ADR-0006: crédito cheio a cada co-autor cadastrado).
        students = await self._students.list_by_program(user.programa_id)
        student_by_uid = {s["uid"]: s for s in students if s.get("uid")}
        author_student = student_by_uid.get(user.uid)
        if author_student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aluno não encontrado para o usuário atual",
            )

        nivel, _ = await self._resolve_vehicle_level(user.programa_id, data.veiculo_id)
        pontuacao_base = _resolve_pontuacao_base(data.tipo_producao, data.status_publicacao)
        now = datetime.now(timezone.utc)
        # Peso versionado por data (ADR-0003): produção publicada trava o peso na versão
        # vigente em data_realizacao; submetida/aceita usa o peso vigente atual (provisório).
        when = data.data_realizacao if data.status_publicacao == "publicado" else now
        weights = await self._qualis_weights.get_weights_at(user.programa_id, when)
        peso = weights.get(nivel, weights.get("SC", 0.0))
        score = self._inference.score_production(nivel, peso, pontuacao_base)

        # O autor que registra é sempre incluído em autores[].
        autores = list(data.autores)
        if user.uid not in autores:
            autores.insert(0, user.uid)

        production_id = await self._productions.create(
            {
                "titulo": data.titulo,
                "doi": data.doi,
                "veiculo_id": data.veiculo_id,
                "tipo_producao": data.tipo_producao,
                "status_publicacao": data.status_publicacao,
                "observacao": data.observacao,
                "autores": autores,
                "pontuacao_base": pontuacao_base,
                "pontuacao_calculada": score,
                "nivel_veiculo": nivel,
                "peso_aplicado": peso,
                "programa_id": user.programa_id,
                "criado_em": now,
            }
        )

        # Co-autoria: uma atividade dedicada (FK producao_id) por autor cadastrado como aluno,
        # começando pelo autor que registra. creditos_gerados usa a pontuacao_calculada (score).
        author_student_ids: list[str] = []
        for student in [author_student] + [
            student_by_uid[uid] for uid in autores if uid in student_by_uid
        ]:
            if student["id"] not in author_student_ids:
                author_student_ids.append(student["id"])
        for student_id in author_student_ids:
            await self._create_linked_activity(student_id, data, production_id, score, now)

        return {
            "id": production_id,
            "pontuacao_calculada": score,
            "nivel_veiculo": nivel,
            "peso_aplicado": peso,
        }

    async def _create_linked_activity(
        self,
        student_id: str,
        data: ProductionCreate,
        production_id: str,
        creditos: float,
        now: datetime,
    ) -> str:
        """Cria a atividade dedicada (subtipo produção) e retorna o activity_id gerado.

        Grava um documento em students/{id}/activities com a FK invertida producao_id →
        productions/{id}, sem tipo_id de activity_types (o request de produção não envia tipo),
        com categoria fixa ACTIVITY_CATEGORIA_PRODUCAO e o mesmo formato das atividades
        regulares, para herdar o fluxo rascunho→enviado→aprovado e a validação do orientador.

        Args:
            student_id: ID do aluno autor (dono desta atividade).
            data: Dados da produção registrada.
            production_id: ID da produção na coleção raiz (FK producao_id).
            creditos: Pontuação calculada (RL05), gravada como default de creditos_gerados.
            now: Timestamp de criação, compartilhado com o documento de produção.

        Returns:
            ID do documento de atividade recém-criado.
        """
        return await self._activities.create_activity(
            student_id,
            {
                "tipo_id": None,
                "producao_id": production_id,
                "aluno_id": student_id,
                "categoria": ACTIVITY_CATEGORIA_PRODUCAO,
                "descricao": data.titulo,
                "data_realizacao": data.data_realizacao,
                "comprovante_url": data.comprovante_url,
                "creditos_gerados": creditos,
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

    async def list_productions(
        self, user: CurrentUser, status: str | None = None
    ) -> list[dict]:
        """Lista produções visíveis ao usuário, enriquecidas e opcionalmente filtradas.

        Args:
            user: Usuário autenticado; define a visibilidade (aluno/orientador/coordenação).
            status: Quando informado, restringe ao status_atividade correspondente
                (ex.: 'enviado' para a fila de validação da coordenação).

        Returns:
            Produções com aluno_nome, orientador_nome, data de submissão (criado_em da
            atividade vinculada) e status_atividade.
        """
        students = await self._students_service.list_students(user)
        vehicles = await self._vehicles.list_all()
        nome_by_vehicle = {v["id"]: v.get("nome", "") for v in vehicles}
        advisor_name_by_id = {
            advisor["id"]: advisor.get("nome", "")
            for advisor in await self._advisors.list_all()
        }

        result: list[dict] = []
        for student in students:
            orientador_nome = advisor_name_by_id.get(student.get("orientador_id"))
            # Com a FK invertida, o vínculo aluno↔produção é a atividade (producao_id); o
            # status_atividade é o da própria atividade (fonte do fluxo de validação).
            activities = await self._activities.list_by_student(student["id"])
            for activity in activities:
                producao_id = activity.get("producao_id")
                if not producao_id:
                    continue
                if status is not None and activity.get("status") != status:
                    continue
                production = await self._productions.get(producao_id)
                if production is None:
                    continue
                result.append(
                    {
                        "id": production["id"],
                        "aluno_id": student["id"],
                        "aluno_nome": student.get("nome", ""),
                        "orientador_nome": orientador_nome,
                        "titulo": production.get("titulo"),
                        "doi": production.get("doi"),
                        "veiculo_nome": nome_by_vehicle.get(production.get("veiculo_id"), ""),
                        "nivel_veiculo": production.get("nivel_veiculo", ""),
                        "tipo_producao": production.get("tipo_producao"),
                        "status_publicacao": production.get("status_publicacao"),
                        "observacao": production.get("observacao"),
                        "autores": production.get("autores", []),
                        "pontuacao_calculada": production.get("pontuacao_calculada", 0.0),
                        "peso_aplicado": production.get("peso_aplicado", 0.0),
                        "status_atividade": activity.get("status", ""),
                        "criado_em": activity.get("criado_em"),
                    }
                )
        return result

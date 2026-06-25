"""
Auditoria de autorização (A01) — tentativas de acesso com papel incorreto.

Cobre US-PA03: para cada rota restrita de `api/v1/`, papéis não autorizados
recebem 403. Em particular nenhuma rota administrativa de escrita
(POST/PUT/DELETE/PATCH) é acessível por `aluno`, e o superusuário global `adm`
(ADR-0001) não acessa operações acadêmicas.

Estratégia: `@requires_role` é o decorador mais externo e curto-circuita antes de
qualquer dependência de serviço ou aspecto subsequente, então um papel proibido
nunca alcança o Firestore. Basta injetar um `CurrentUser` falso via
`app.dependency_overrides` e enviar um corpo válido (a validação de corpo do
FastAPI ocorre antes do gate de papel; um corpo inválido produziria 422 e
mascararia o 403).

As rotas dos routers `auth`, `audit_logs`, `transfers` e `coordination_transfers`
já têm cobertura de 403 em seus próprios arquivos de teste.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.core.auth import CurrentUser, get_current_user
from backend.app.main import app

ALL_ROLES = ("aluno", "orientador", "coordenacao", "adm")

# Corpos válidos mínimos por modelo de request (suficientes para passar a
# validação Pydantic e chegar ao gate de papel).
_STUDENT_CREATE = {
    "nome": "Aluno",
    "email": "aluno@x.com",
    "matricula": "M1",
    "orientador_id": "adv1",
    "nivel": "mestrado",
    "data_ingresso": "2026-01-01T00:00:00Z",
    "programa_id": "prog",
}
_QUALIFICACAO = {"aprovada": True, "data_qualificacao": "2026-01-01T00:00:00Z"}
_PROFICIENCIA = {"comprovada": True}
_SITUACAO = {"situacao_registrada": "regular"}
_ADVISOR_CREATE = {
    "nome": "Orientador",
    "email": "o@x.com",
    "departamento": "DC",
    "programa_id": "prog",
}
_ACTIVITY_CREATE = {
    "tipo_id": "t1",
    "descricao": "d",
    "data_realizacao": "2026-01-01T00:00:00Z",
}
_PARECER = {"parecer": "ok"}
_VALIDATE = {"acao": "aprovar"}
_PRODUCTION_CREATE = {
    "titulo": "T",
    "veiculo_id": "v1",
    "tipo_producao": "artigo",
    "status_publicacao": "publicado",
    "data_realizacao": "2026-01-01T00:00:00Z",
}
_WORKPLAN_CREATE = {
    "titulo": "T",
    "data_inicio": "2026-01-01T00:00:00Z",
    "data_fim_prevista": "2026-06-01T00:00:00Z",
}
_STAGE_CREATE = {
    "nome": "revisao",
    "ordem": 1,
    "data_inicio": "2026-01-01T00:00:00Z",
    "data_fim": "2026-02-01T00:00:00Z",
}
_TASK_CREATE = {"titulo": "T", "prazo": "2026-02-01T00:00:00Z"}
_TASK_STATUS = {"status": "em_andamento"}
_PROGRESS_UPDATE = {"conteudo": "c", "percentual": 50.0}
_ACTIVITY_TYPE_CREATE = {"nome": "N", "categoria": "basico", "pontuacao_base": 1.0}
_ACTIVITY_TYPE_TOGGLE = {"ativo": False}
_VEHICLE_CREATE = {"nome": "V", "tipo": "revista", "nivel": "A1"}
_VEHICLE_LEVEL_UPDATE = {"nivel": "A2"}
_TRANSFER_CROSS_CREATE = {
    "student_id": "s1",
    "orientador_destino_id": "adv2",
    "programa_destino_id": "prog2",
    "motivo": "motivo valido",
}
_TRANSFER_CROSS_REJECT = {"motivo": "motivo valido"}

# (id, método, path, corpo_json, papéis_permitidos)
# `path` já inclui o prefixo /api/v1.
_ROUTES: list[tuple[str, str, str, dict | None, tuple[str, ...]]] = [
    # students
    ("students.list", "GET", "/api/v1/students", None, ("coordenacao", "orientador")),
    ("students.get", "GET", "/api/v1/students/x", None, ("aluno", "orientador", "coordenacao")),
    ("students.create", "POST", "/api/v1/students", _STUDENT_CREATE, ("coordenacao",)),
    ("students.update", "PUT", "/api/v1/students/x", {"nome": "A"}, ("coordenacao",)),
    ("students.delete", "DELETE", "/api/v1/students/x", None, ("coordenacao",)),
    ("students.qualificacao", "PATCH", "/api/v1/students/x/qualificacao", _QUALIFICACAO, ("coordenacao",)),
    ("students.proficiencia", "PATCH", "/api/v1/students/x/proficiencia", _PROFICIENCIA, ("coordenacao",)),
    ("students.situacao", "PATCH", "/api/v1/students/x/situacao", _SITUACAO, ("coordenacao",)),
    # advisors
    ("advisors.list", "GET", "/api/v1/advisors", None, ("coordenacao", "orientador")),
    ("advisors.get", "GET", "/api/v1/advisors/x", None, ("coordenacao",)),
    ("advisors.create", "POST", "/api/v1/advisors", _ADVISOR_CREATE, ("coordenacao",)),
    ("advisors.update", "PUT", "/api/v1/advisors/x", {"nome": "O"}, ("coordenacao",)),
    ("advisors.delete", "DELETE", "/api/v1/advisors/x", None, ("coordenacao",)),
    # activities
    ("activities.list", "GET", "/api/v1/activities", None, ("aluno", "orientador", "coordenacao")),
    ("activities.create", "POST", "/api/v1/activities", _ACTIVITY_CREATE, ("aluno",)),
    ("activities.parecer", "PATCH", "/api/v1/activities/x/parecer", _PARECER, ("orientador",)),
    ("activities.validate", "PATCH", "/api/v1/activities/x/validate", _VALIDATE, ("coordenacao",)),
    # productions
    ("productions.list", "GET", "/api/v1/productions", None, ("aluno", "orientador", "coordenacao")),
    ("productions.create", "POST", "/api/v1/productions", _PRODUCTION_CREATE, ("aluno",)),
    # work_plan
    ("work_plan.get", "GET", "/api/v1/work-plan/x", None, ("aluno", "orientador", "coordenacao")),
    ("work_plan.create", "POST", "/api/v1/work-plan/x", _WORKPLAN_CREATE, ("orientador", "coordenacao")),
    ("work_plan.update", "PUT", "/api/v1/work-plan/x", {}, ("orientador", "coordenacao")),
    ("work_plan.create_stage", "POST", "/api/v1/work-plan/x/stages", _STAGE_CREATE, ("orientador", "coordenacao")),
    ("work_plan.update_stage", "PATCH", "/api/v1/stages/x", {}, ("orientador", "coordenacao")),
    ("work_plan.create_task", "POST", "/api/v1/stages/x/tasks", _TASK_CREATE, ("orientador", "coordenacao")),
    ("work_plan.update_task", "PATCH", "/api/v1/tasks/x", {}, ("orientador", "coordenacao")),
    ("work_plan.task_status", "PATCH", "/api/v1/tasks/x/status", _TASK_STATUS, ("orientador", "coordenacao")),
    ("work_plan.add_update", "POST", "/api/v1/tasks/x/updates", _PROGRESS_UPDATE, ("aluno",)),
    ("work_plan.list_updates", "GET", "/api/v1/tasks/x/updates", None, ("aluno", "orientador", "coordenacao")),
    ("work_plan.fact", "GET", "/api/v1/work-plan/x/facts/plano-concluido", None, ("aluno", "orientador", "coordenacao")),
    # activity_types
    ("activity_types.list", "GET", "/api/v1/activity-types", None, ("aluno", "orientador", "coordenacao")),
    ("activity_types.create", "POST", "/api/v1/activity-types", _ACTIVITY_TYPE_CREATE, ("coordenacao",)),
    ("activity_types.update", "PUT", "/api/v1/activity-types/x", {"nome": "N"}, ("coordenacao",)),
    ("activity_types.toggle", "PATCH", "/api/v1/activity-types/x/toggle", _ACTIVITY_TYPE_TOGGLE, ("coordenacao",)),
    # programs
    ("programs.get_config", "GET", "/api/v1/programs/config", None, ("aluno", "orientador", "coordenacao")),
    ("programs.update_config", "PUT", "/api/v1/programs/config", {}, ("coordenacao",)),
    # vehicles
    ("vehicles.list", "GET", "/api/v1/vehicles", None, ("aluno", "orientador", "coordenacao")),
    ("vehicles.create", "POST", "/api/v1/vehicles", _VEHICLE_CREATE, ("coordenacao",)),
    ("vehicles.update_level", "PUT", "/api/v1/vehicle-levels/x", _VEHICLE_LEVEL_UPDATE, ("coordenacao",)),
    ("vehicles.delete", "DELETE", "/api/v1/vehicles/x", None, ("coordenacao",)),
    # dashboard
    ("dashboard.aluno", "GET", "/api/v1/dashboard/aluno/x", None, ("aluno", "orientador", "coordenacao")),
    ("dashboard.orientador", "GET", "/api/v1/dashboard/orientador/x", None, ("orientador", "coordenacao")),
    ("dashboard.coordenacao", "GET", "/api/v1/dashboard/coordenacao", None, ("coordenacao",)),
    # reports
    ("reports.at_risk", "GET", "/api/v1/reports/students-at-risk", None, ("coordenacao",)),
    ("reports.by_status", "GET", "/api/v1/reports/students-by-status", None, ("coordenacao",)),
    ("reports.by_advisor", "GET", "/api/v1/reports/students-by-advisor", None, ("coordenacao",)),
    ("reports.completion", "GET", "/api/v1/reports/completion-time", None, ("coordenacao",)),
    ("reports.productions", "GET", "/api/v1/reports/productions", None, ("coordenacao",)),
    # checklist / inference (rotas corrigidas nesta issue)
    ("checklist.get", "GET", "/api/v1/checklist/x", None, ("aluno", "orientador", "coordenacao")),
    ("inference.get", "GET", "/api/v1/inference/x", None, ("aluno", "orientador", "coordenacao")),
    # notifications
    ("notifications.read", "PATCH", "/api/v1/notifications/x/read", None, ("aluno", "orientador", "coordenacao")),
    # transfer_cross
    ("transfer_cross.create", "POST", "/api/v1/transfers-cross/", _TRANSFER_CROSS_CREATE, ("orientador", "coordenacao")),
    ("transfer_cross.aprovar_origem", "POST", "/api/v1/transfers-cross/x/aprovar-origem", None, ("coordenacao",)),
    ("transfer_cross.aprovar_destino", "POST", "/api/v1/transfers-cross/x/aprovar-destino", None, ("coordenacao",)),
    ("transfer_cross.rejeitar", "POST", "/api/v1/transfers-cross/x/rejeitar", _TRANSFER_CROSS_REJECT, ("coordenacao",)),
]


def _forbidden_cases() -> list[Any]:
    """Expande a tabela em (método, path, corpo, papel_proibido) com ids legíveis."""
    cases = []
    for route_id, method, path, body, allowed in _ROUTES:
        for role in ALL_ROLES:
            if role not in allowed:
                cases.append(pytest.param(method, path, body, role, id=f"{route_id}-{role}"))
    return cases


@pytest.fixture
def client() -> TestClient:
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_user(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        uid=f"uid-{role}", role=role, programa_id="prog", email=f"{role}@saga.test"
    )


@pytest.mark.parametrize("method, path, body, role", _forbidden_cases())
def test_papel_incorreto_recebe_403(
    client: TestClient,
    method: str,
    path: str,
    body: dict | None,
    role: str,
) -> None:
    _override_user(role)

    kwargs: dict[str, Any] = {}
    if body is not None:
        kwargs["json"] = body

    response = client.request(method, path, **kwargs)

    assert response.status_code == 403, (
        f"{method} {path} deveria negar o papel '{role}' com 403, "
        f"mas retornou {response.status_code}"
    )


# O upload de comprovante exige multipart (UploadFile = File(...)); um corpo
# ausente produziria 422 antes do gate de papel, então enviamos um arquivo dummy.
@pytest.mark.parametrize("role", ["orientador", "coordenacao", "adm"])
def test_comprovante_upload_papel_incorreto_403(client: TestClient, role: str) -> None:
    _override_user(role)

    response = client.post(
        "/api/v1/activities/x/comprovante",
        files={"file": ("comprovante.pdf", b"%PDF-1.4 dummy", "application/pdf")},
    )

    assert response.status_code == 403

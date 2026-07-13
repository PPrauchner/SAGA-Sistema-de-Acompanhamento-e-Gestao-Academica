import pytest

@pytest.fixture(autouse=True)
def disable_aspects_global(monkeypatch):
    """
    Desabilita os aspectos de auditoria e histórico globalmente nos testes
    para evitar inicialização do Firebase nos testes de mutação.

    Também substitui o cliente Firestore de work_plan_repository por um fake
    vazio: FixtureRepository.get_plan_tasks delega a WorkPlanRepository, e sem
    este patch os testes de inferência/checklist disparariam a inicialização real
    do Firebase. Com o fake vazio o repositório não encontra plano e o motor cai
    no fixture _TASKS em memória.
    """
    from backend.app.aspects import aspect_config
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)

    from backend.app.repositories import work_plan_repository
    from backend.app.tests.fake_firestore import FakeFirestore
    fake = FakeFirestore()
    monkeypatch.setattr(work_plan_repository, "get_firestore_client", lambda: fake)

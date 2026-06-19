import pytest

@pytest.fixture(autouse=True)
def disable_aspects_global(monkeypatch):
    """
    Desabilita os aspectos de auditoria e histórico globalmente nos testes
    para evitar inicialização do Firebase nos testes de mutação.
    """
    from backend.app.aspects import aspect_config
    monkeypatch.setattr(aspect_config, "AUDIT_ENABLED", False)
    monkeypatch.setattr(aspect_config, "HISTORY_ENABLED", False)

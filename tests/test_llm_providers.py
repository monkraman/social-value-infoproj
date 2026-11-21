"""Provider order and fallback: one provider out of quota must not stop the generator."""
import pytest

from app.core.config import settings
from app.services import llm_client
from app.services.llm_client import LLMUnavailable, complete_json_with_source


@pytest.fixture
def three_providers(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "LLM_FALLBACK", "gemini, openai")
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT", "test-deployment")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-openai")


def test_order_is_active_then_fallbacks(three_providers):
    assert settings.provider_order == ["azure", "gemini", "openai"]


def test_unconfigured_fallback_is_skipped(three_providers, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    assert settings.provider_order == ["azure", "gemini"]


def test_azure_without_deployment_is_not_used(three_providers, monkeypatch):
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT", "")
    assert settings.provider_order[0] == "gemini"


def test_falls_back_when_first_is_out_of_quota(three_providers, monkeypatch):
    def call(provider, system, user):
        if provider == "azure":
            raise LLMUnavailable("Azure OpenAI request failed: 429 quota exceeded")
        return {"initiatives": []}, f"{provider}/m"

    monkeypatch.setattr(llm_client, "_call", call)
    assert complete_json_with_source("s", "u") == ({"initiatives": []}, "gemini/m")


def test_all_down_reports_every_reason(three_providers, monkeypatch):
    def call(provider, system, user):
        raise LLMUnavailable(f"{provider} down")

    monkeypatch.setattr(llm_client, "_call", call)
    with pytest.raises(LLMUnavailable) as e:
        complete_json_with_source("s", "u")
    assert "azure down" in str(e.value) and "gemini down" in str(e.value) and "openai down" in str(e.value)


def test_embeddings_stay_on_gemini_when_chat_is_azure(three_providers):
    assert settings.embedding_provider == "gemini"


def test_embeddings_on_azure_when_chosen(three_providers, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    assert settings.embedding_provider == "azure"


def test_azure_embeddings_need_their_own_deployment(three_providers, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", None)
    assert settings.embedding_provider == "none"


def test_auto_embeddings_use_azure_only_when_nothing_else(three_providers, monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "auto")
    monkeypatch.setattr(settings, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    assert settings.embedding_provider == "gemini"
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    assert settings.embedding_provider == "azure"


def test_azure_embeddings_call_the_embedding_deployment(three_providers, monkeypatch):
    from types import SimpleNamespace

    from app.services.embedding_service import EmbeddingService

    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "emb-deploy")
    seen = {}

    def create(input, model, dimensions):
        seen.update(model=model, dimensions=dimensions, n=len(input))
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0] + [0.0] * (dimensions - 1)) for _ in input])

    service = EmbeddingService()
    service._azure_client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    vectors = service.get_embeddings(["one", "two"])
    assert seen == {"model": "emb-deploy", "dimensions": settings.EMBEDDING_DIMENSION, "n": 2}
    assert len(vectors) == 2 and len(vectors[0]) == settings.EMBEDDING_DIMENSION


# ── The admin switch: super-admins pick the first provider; keys never pass through it ────

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import ai_settings_service as ai  # noqa: E402
from tests.conftest import login_headers, make_test_user  # noqa: E402


@pytest.fixture(scope="module")
def admin_client():
    email, password = make_test_user("superadmin")
    with TestClient(app) as c:
        c.headers.update(login_headers(email, password))
        yield c
        c.put("/admin/ai", json={"provider": "default"})  # never leave a test choice behind


def test_switch_is_superadmin_only():
    email, password = make_test_user("bid_author")
    with TestClient(app) as c:
        assert c.get("/admin/ai").status_code == 401
        assert c.get("/admin/ai", headers=login_headers(email, password)).status_code == 403


def test_switch_lists_providers_without_keys(admin_client):
    data = admin_client.get("/admin/ai").json()
    assert {p["id"] for p in data["providers"]} == {"azure", "gemini", "openai"}
    assert "key" not in str(data).lower().replace("keys", "")


def test_switch_refuses_provider_without_key(admin_client, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    res = admin_client.put("/admin/ai", json={"provider": "openai"})
    assert res.status_code == 422 and "no key" in res.json()["detail"]


def test_switch_changes_order_and_is_audited(admin_client):
    from app.core.database import SessionLocal
    from app.models.audit_log import SystemAuditLog

    res = admin_client.put("/admin/ai", json={"provider": "gemini"})
    assert res.status_code == 200, res.text
    assert res.json()["selected"] == "gemini" and res.json()["order"][0] == "gemini"
    assert ai.effective_order()[0] == "gemini"
    with SessionLocal() as db:
        log = (db.query(SystemAuditLog).filter(SystemAuditLog.event_type == "AI_PROVIDER_CHANGED")
               .order_by(SystemAuditLog.timestamp.desc()).first())
    assert log is not None and log.metadata_payload["to"] == "gemini"

    back = admin_client.put("/admin/ai", json={"provider": "default"}).json()
    assert back["selected"] == "default" and back["order"] == back["default_order"]

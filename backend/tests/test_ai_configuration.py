import json
import stat

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.research.configuration.service import AIConfiguration, AIInput


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/history.db",
        ai_config_file=tmp_path / "private" / "config.json",
        llm_model="existing-model",
        llm_api_key="original-secret",
    )


def body(**kwargs):
    return {"base_url": "http://127.0.0.1:4000/v1", "model_id": "new-model", **kwargs}


def test_save_restart_reset_and_permissions(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/settings/ai", json=body())
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert "original-secret" not in response.text and "api_key" not in response.json()
        assert response.json()["has_api_key"]
        assert settings.llm_model == "existing-model"
        assert client.get("/api/health").json()["model_configured"]
    assert stat.S_IMODE(settings.ai_config_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(settings.ai_config_file.parent.stat().st_mode) == 0o700
    assert json.loads(settings.ai_config_file.read_text())["api_key"] == "original-secret"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/settings/ai").json()["model_id"] == "new-model"
        assert client.delete("/api/settings/ai").json()["model_id"] == "existing-model"
        assert not settings.ai_config_file.exists()


@pytest.mark.parametrize(
    "url",
    [
        "http://evil.example/v1",
        "https://user:secret@example.org/v1",
        "https://example.org/v1?api_key=secret",
        "file:///tmp/key",
        "https://example.org/#secret",
        "http://192.168.1.1/v1",
    ],
)
def test_invalid_endpoint_and_key_never_echoed(settings, url):
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/settings/ai", json=body(base_url=url, api_key="secret\r\nkey"))
        assert response.status_code == 422
        assert "secret" not in response.text and url not in response.text
        assert not settings.ai_config_file.exists()


def test_changed_endpoint_needs_explicit_key_and_can_clear(settings):
    with TestClient(create_app(settings)) as client:
        changed = body(base_url="http://host.docker.internal:4000/v1")
        assert client.post("/api/settings/ai", json=changed).status_code == 422
        changed["api_key"] = ""
        assert not client.post("/api/settings/ai", json=changed).json()["has_api_key"]
        assert client.get("/api/health").json()["mode"] == "fixtures"
        assert client.get("/api/health").json()["model_id"] == "fixture-stub"


def test_test_connection_uses_candidate_without_saving(settings, monkeypatch, caplog):
    observed = []

    def handle(request):
        observed.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    real_client = httpx.Client

    def factory(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return real_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("app.modules.research.configuration.service.httpx.Client", factory)
    service = AIConfiguration(settings)
    snapshot = service.current()
    result = service.test(AIInput(**body(model_id="candidate-model", api_key="candidate-secret")))
    assert result.ok
    assert observed[0].headers["authorization"] == "Bearer candidate-secret"
    assert json.loads(observed[0].content)["model"] == "candidate-model"
    assert not settings.ai_config_file.exists()
    service.save(AIInput(**body(api_key="replacement-secret")))
    assert snapshot.llm_api_key == "original-secret"
    assert service.current().llm_api_key == "replacement-secret"
    assert "candidate-secret" not in caplog.text


@pytest.mark.parametrize("kind", ["error", "redirect", "invalid", "timeout"])
def test_test_failure_is_safe_and_nonmutating(settings, monkeypatch, kind):
    def handle(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("secret provider message")
        return httpx.Response(
            302 if kind == "redirect" else 401 if kind == "error" else 200,
            json={"error": "secret provider message"},
            headers={"Location": "https://evil.example/"},
        )

    real_client = httpx.Client
    monkeypatch.setattr(
        "app.modules.research.configuration.service.httpx.Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw),
    )
    result = AIConfiguration(settings).test(AIInput(**body()))
    assert not result.ok and "secret" not in result.message
    assert not settings.ai_config_file.exists()


def test_origins_hosts_and_validation_errors_protect_secrets(settings):
    with TestClient(create_app(settings)) as client:
        for path in ["/api/settings/ai", "/api/settings/ai/test"]:
            assert (
                client.post(path, json=body(), headers={"origin": "https://evil.example"}).status_code == 403
            )
            assert client.post(path, json=body(), headers={"host": "evil.example"}).status_code == 400
            for data in [{"api_key": "do-not-echo"}, ["do-not-echo"], {"base_url": {"do-not-echo": 1}}]:
                response = client.post(path, json=data)
                assert response.status_code == 422 and "do-not-echo" not in response.text
        assert client.delete("/api/settings/ai", headers={"origin": "null"}).status_code == 403


def test_corrupt_storage_fails_closed(settings):
    settings.ai_config_file.parent.mkdir()
    settings.ai_config_file.write_text("secret corrupt file")
    with pytest.raises(RuntimeError, match="Cannot load private AI configuration") as error:
        AIConfiguration(settings)
    assert "secret" not in str(error.value)


def test_save_failure_preserves_previous_settings(settings, monkeypatch):
    service = AIConfiguration(settings)
    service.save(AIInput(**body(api_key="saved-secret")))
    old = settings.ai_config_file.read_bytes()

    def fail(*args):
        raise OSError("synthetic write failure")

    monkeypatch.setattr("app.modules.research.configuration.service.os.replace", fail)
    with pytest.raises(OSError):
        service.save(AIInput(**body(api_key="changed-secret")))
    assert settings.ai_config_file.read_bytes() == old
    assert service.current().llm_api_key == "saved-secret"
    assert list(settings.ai_config_file.parent.iterdir()) == [settings.ai_config_file]


def test_runtime_configuration_reaches_new_operations_and_preserves_run_snapshot(settings, monkeypatch):
    from threading import Event

    from app.contracts.api import ChatRequest, ResearchRequest
    from app.modules.intelligence.service import IntelligenceService
    from app.modules.market_data.service import DataService
    from app.modules.research.repository import ResearchRepository
    from app.modules.research.service import ResearchService

    settings.data_mode = "live"
    ai = AIConfiguration(settings)
    data = DataService(settings)
    repo = ResearchRepository(settings.database_url)
    entered, release = Event(), Event()
    captured = []

    def execute(self, run_id):
        entered.set()
        release.wait(timeout=5)
        captured.append(self.settings.llm_model)

    monkeypatch.setattr("app.modules.research.service.ResearchOrchestrator.execute", execute)
    monkeypatch.setattr("app.modules.research.service.answer_chat", lambda body, data, cfg: cfg.llm_model)
    monkeypatch.setattr("app.modules.intelligence.service.summarize_news", lambda data, cfg: cfg.llm_model)
    research = ResearchService(repo, data, settings, lambda slug: {}, ai.current)
    intel = IntelligenceService(data, settings, ai.current)
    try:
        run = research.start(ResearchRequest(symbol="AAPL"))
        assert entered.wait(timeout=5)
        ai.save(AIInput(**body()))
        assert run["model_id"] == "existing-model"
        assert research.chat(ChatRequest(symbol="AAPL", message="Test")) == "new-model"
        assert intel.summarize_news() == "new-model"
    finally:
        release.set()
        research.shutdown()
        repo.close()
    assert captured == ["existing-model"]


def test_live_health_updates_without_restart(settings):
    settings.data_mode = "live"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["model_id"] == "existing-model"
        client.post("/api/settings/ai", json=body())
        assert client.get("/api/health").json()["model_id"] == "new-model"
        client.delete("/api/settings/ai")
        assert client.get("/api/health").json()["model_id"] == "existing-model"

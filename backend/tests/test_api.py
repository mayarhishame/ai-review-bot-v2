from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.errors import LLMUnavailableError

client = TestClient(app)


class FakeLLM:
    async def complete(self, system, user):
        return '{"comments": []}'


def test_api_review_ok(monkeypatch):
    monkeypatch.setattr("app.main.LLMClient", FakeLLM)
    r = client.post("/api/review", json={"diff": ""})
    assert r.status_code == 200 and r.json()["comments"] == []


def test_standards_get_and_put(monkeypatch, tmp_path):
    f = tmp_path / "standards.yml"       # never touch the real standards file
    monkeypatch.setattr(settings, "standards_path", str(f))
    assert client.get("/api/standards").json() == {"yaml": ""}
    ok = client.put("/api/standards", json={"yaml": "global_rules: []"})
    assert ok.status_code == 200 and f.exists()
    assert client.put("/api/standards", json={"yaml": "languages: 5"}).status_code == 400


def test_reviews_endpoint_returns_list():
    assert isinstance(client.get("/api/reviews").json(), list)


def test_simulate_state():
    assert "enabled" in client.get("/api/simulate-failure").json()
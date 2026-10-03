import hashlib, hmac, json
from fastapi.testclient import TestClient
from app import store
from app.config import settings
from app.main import app
from app.webhook import process_pr

client = TestClient(app)
SECRET = "s3cret"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def send(payload, event="pull_request", delivery="d1", sig=None):
    body = json.dumps(payload).encode()
    return client.post("/webhook", content=body, headers={
        "X-Hub-Signature-256": sig or sign(body), "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery, "Content-Type": "application/json"})


PR = {"action": "opened", "number": 1, "repository": {"full_name": "a/b"},
      "pull_request": {"head": {"sha": "abc"}}}


def setup_function():
    settings.webhook_secret = SECRET
    store.seen_deliveries.clear()
    store.history.clear()


def test_bad_signature():
    assert send(PR, sig="sha256=bad").status_code == 401


def test_non_pr_event_ignored():
    assert send(PR, event="push").json()["status"] == "ignored"


def test_closed_action_ignored():
    assert send({**PR, "action": "closed"}).json()["status"] == "ignored"


def test_duplicate_delivery(monkeypatch):
    async def noop(*a, **k): pass
    monkeypatch.setattr("app.webhook.process_pr", noop)
    assert send(PR, delivery="x").json()["status"] == "accepted"
    assert send(PR, delivery="x").json()["status"] == "duplicate"


def test_health_and_simulate_toggle():
    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/api/simulate-failure", json={"enabled": True}).json()["enabled"]
    client.post("/api/simulate-failure", json={"enabled": False})


def test_api_review_bad_standards():
    r = client.post("/api/review", json={"diff": "", "standards_yaml": "languages: 5"})
    assert r.status_code == 400


class FakeGH:
    def __init__(self, fail=False): self.fail, self.posted = fail, None
    async def get_diff(self, repo, pr):
        from app.errors import GitHubAPIError
        if self.fail: raise GitHubAPIError("boom")
        return ""
    async def post_review(self, repo, pr, sha, result): self.posted = result


async def test_process_pr_success_and_github_failure():
    gh = FakeGH()
    await process_pr("a/b", 1, "abc", gh=gh, llm=object())
    assert store.history[0]["status"] == "ok" and gh.posted is not None
    await process_pr("a/b", 2, "abc", gh=FakeGH(fail=True), llm=object())
    assert store.history[0]["status"] == "error"
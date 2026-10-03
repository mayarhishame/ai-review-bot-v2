import httpx
import pytest
from app.config import settings
from app.errors import GitHubAPIError, LLMRateLimitError, LLMUnavailableError
from app.github_client import GitHubClient
from app.llm_client import LLMClient
from app.reviewer import Comment, ReviewResult


class FakeResp:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        return self._body


def fake_async_client(responses=None, exc=None):
    """Replacement for httpx.AsyncClient. Returns queued responses or raises exc."""
    queue = list(responses or [])

    class FakeAsyncClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

        async def _next(self):
            if exc:
                raise exc
            return queue.pop(0)

        async def post(self, *a, **k): return await self._next()
        async def get(self, *a, **k): return await self._next()

    return FakeAsyncClient


@pytest.fixture(autouse=True)
def no_sim(monkeypatch):
    monkeypatch.setattr(settings, "simulate_llm_failure", False)
    monkeypatch.setattr(settings, "retry_base_delay", 0)


# ---------- LLM client ----------
async def test_llm_success(monkeypatch):
    body = {"choices": [{"message": {"content": '{"comments": []}'}}]}
    monkeypatch.setattr("app.llm_client.httpx.AsyncClient", fake_async_client([FakeResp(200, body)]))
    assert await LLMClient()._call("s", "u") == '{"comments": []}'


async def test_llm_429_raises_rate_limit(monkeypatch):
    monkeypatch.setattr("app.llm_client.httpx.AsyncClient", fake_async_client([FakeResp(429)]))
    with pytest.raises(LLMRateLimitError):
        await LLMClient()._call("s", "u")


async def test_llm_http_error_raises_unavailable(monkeypatch):
    monkeypatch.setattr("app.llm_client.httpx.AsyncClient", fake_async_client([FakeResp(404, text="model_not_found")]))
    with pytest.raises(LLMUnavailableError):
        await LLMClient()._call("s", "u")


async def test_llm_timeout_raises_unavailable(monkeypatch):
    monkeypatch.setattr("app.llm_client.httpx.AsyncClient", fake_async_client(exc=httpx.ReadTimeout("slow")))
    with pytest.raises(LLMUnavailableError):
        await LLMClient()._call("s", "u")


async def test_llm_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    async def flaky(self, system, user):
        calls["n"] += 1
        if calls["n"] < 3:
            raise LLMRateLimitError("429")
        return "ok"

    monkeypatch.setattr(LLMClient, "_call", flaky)
    assert await LLMClient().complete("s", "u") == "ok"
    assert calls["n"] == 3


# ---------- GitHub client ----------
RESULT = ReviewResult(comments=[Comment(file="a.py", line=1, severity="error", rule_id="G1", message="secret")])


async def test_get_diff_ok(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client([FakeResp(200, text="DIFF")]))
    assert await GitHubClient().get_diff("a/b", 1) == "DIFF"


async def test_get_diff_http_error(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client([FakeResp(404)]))
    with pytest.raises(GitHubAPIError):
        await GitHubClient().get_diff("a/b", 1)


async def test_get_diff_network_error(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client(exc=httpx.ConnectError("down")))
    with pytest.raises(GitHubAPIError):
        await GitHubClient().get_diff("a/b", 1)


async def test_post_review_ok(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client([FakeResp(200)]))
    await GitHubClient().post_review("a/b", 1, "sha", RESULT)


async def test_post_review_422_falls_back_to_summary(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client([FakeResp(422), FakeResp(200)]))
    await GitHubClient().post_review("a/b", 1, "sha", RESULT)  # no exception = fallback worked


async def test_post_review_server_error(monkeypatch):
    monkeypatch.setattr("app.github_client.httpx.AsyncClient", fake_async_client([FakeResp(500)]))
    with pytest.raises(GitHubAPIError):
        await GitHubClient().post_review("a/b", 1, "sha", RESULT)
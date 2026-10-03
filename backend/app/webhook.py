import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Header, Request
from . import store
from .config import settings
from .errors import InvalidSignatureError, ReviewBotError
from .github_client import GitHubClient
from .llm_client import LLMClient
from .reviewer import review_diff
from .standards import load_standards

logger = logging.getLogger("webhook")
router = APIRouter()


def verify_signature(secret: str, body: bytes, header: str | None):
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not header or not hmac.compare_digest(expected, header):
        raise InvalidSignatureError("Bad webhook signature")


async def process_pr(repo: str, pr: int, sha: str, gh=None, llm=None):
    gh, llm = gh or GitHubClient(), llm or LLMClient()
    record = {"repo": repo, "pr": pr, "time": datetime.now(timezone.utc).isoformat()}
    try:
        diff = await gh.get_diff(repo, pr)
        result = await review_diff(diff, load_standards(settings.standards_path), llm)
        await gh.post_review(repo, pr, sha, result)
        record.update(status="ok", result=result.model_dump())
    except ReviewBotError as e:
        logger.error("Review failed for %s#%s: %s", repo, pr, e)
        record.update(status="error", error=str(e))
    store.history.appendleft(record)


@router.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks,
                  x_hub_signature_256: str | None = Header(None),
                  x_github_event: str = Header(""),
                  x_github_delivery: str = Header("")):
    body = await request.body()
    verify_signature(settings.webhook_secret, body, x_hub_signature_256)
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": "not a pull_request event"}
    p = json.loads(body)
    if p.get("action") not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "reason": f"action {p.get('action')}"}
    key = x_github_delivery or f"{p['repository']['full_name']}#{p['number']}"
    if key in store.seen_deliveries:
        return {"status": "duplicate"}
    store.seen_deliveries.add(key)
    bg.add_task(process_pr, p["repository"]["full_name"], p["number"], p["pull_request"]["head"]["sha"])
    return {"status": "accepted"}
import logging
import httpx
from .config import settings
from .errors import GitHubAPIError
from .reviewer import ReviewResult

logger = logging.getLogger("github")
API = "https://api.github.com"


def format_summary(result: ReviewResult) -> str:
    n = len(result.comments)
    text = f"## 🤖 AI Code Review\nFound **{n}** issue(s)."
    if result.failed_chunks:
        files = ", ".join(f for c in result.failed_chunks for f in c["files"])
        text += f"\n\n⚠️ Review incomplete: the AI service failed for: {files}."
    if result.skipped_files:
        text += f"\n\nSkipped: {', '.join(result.skipped_files)}"
    return text


def format_comment(c) -> str:
    body = f"**[{c.severity.upper()}] {c.rule_id}**: {c.message}"
    return body + (f"\n\n💡 {c.suggestion}" if c.suggestion else "")


class GitHubClient:
    def _headers(self, accept="application/vnd.github+json"):
        return {"Authorization": f"Bearer {settings.github_token}", "Accept": accept}

    async def get_diff(self, repo: str, pr: int) -> str:
        url = f"{API}/repos/{repo}/pulls/{pr}"
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(url, headers=self._headers("application/vnd.github.v3.diff"))
        except httpx.HTTPError as e:
            raise GitHubAPIError(f"GitHub unreachable: {type(e).__name__}") from e
        if r.status_code != 200:
            raise GitHubAPIError(f"get_diff HTTP {r.status_code}")
        return r.text

    async def post_review(self, repo: str, pr: int, sha: str, result: ReviewResult):
        url = f"{API}/repos/{repo}/pulls/{pr}/reviews"
        base = {"commit_id": sha, "event": "COMMENT", "body": format_summary(result)}
        inline = {**base, "comments": [
            {"path": c.file, "line": c.line, "side": "RIGHT", "body": format_comment(c)}
            for c in result.comments]}
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(url, json=inline, headers=self._headers())
                if r.status_code == 422 and result.comments:  # fallback: summary only
                    logger.warning("Inline comments rejected, posting summary only")
                    body = base["body"] + "\n\n" + "\n".join(
                        f"- `{x.file}:{x.line}` {format_comment(x)}" for x in result.comments)
                    r = await c.post(url, json={**base, "body": body}, headers=self._headers())
        except httpx.HTTPError as e:
            raise GitHubAPIError(f"GitHub unreachable: {type(e).__name__}") from e
        if r.status_code >= 300:
            raise GitHubAPIError(f"post_review HTTP {r.status_code}")
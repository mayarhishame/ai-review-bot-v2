import asyncio
import logging
import httpx
from .config import settings
from .errors import LLMUnavailableError, LLMRateLimitError

logger = logging.getLogger("llm")
URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMClient:
    async def complete(self, system: str, user: str) -> str:
        last: Exception | None = None
        for attempt in range(settings.llm_max_retries):
            try:
                return await self._call(system, user)
            except (LLMUnavailableError, LLMRateLimitError) as e:
                last = e
                delay = settings.retry_base_delay * (2 ** attempt)
                logger.warning("LLM attempt %d failed: %s (retry in %.1fs)", attempt + 1, e, delay)
                await asyncio.sleep(delay)
        raise last  # type: ignore[misc]

    async def _call(self, system: str, user: str) -> str:
        if settings.simulate_llm_failure:
            raise LLMUnavailableError("Simulated LLM outage")
        payload = {
            "model": settings.groq_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.groq_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(URL, json=payload, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise LLMUnavailableError(f"Network/timeout: {type(e).__name__}") from e
        if r.status_code == 429:
            raise LLMRateLimitError("Rate limited by LLM provider")
        if r.status_code >= 400:
            logger.error("LLM HTTP %s body: %s", r.status_code, r.text[:300])
            raise LLMUnavailableError(f"LLM HTTP {r.status_code}")
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error("Unexpected LLM response body: %s", r.text[:300])
            raise LLMUnavailableError("LLM returned an unexpected response") from e
        if not isinstance(content, str):
            raise LLMUnavailableError("LLM returned non-text content")
        return content
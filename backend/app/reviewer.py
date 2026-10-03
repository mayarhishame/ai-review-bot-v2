import json
import logging
import re
from typing import Literal
from pydantic import BaseModel, ValidationError
from .config import settings
from .diff_parser import parse_diff, chunk_files
from .errors import LLMInvalidOutputError, LLMUnavailableError, LLMRateLimitError
from .prompt_builder import build_system_prompt, build_user_prompt
from .standards import Standards

logger = logging.getLogger("reviewer")


class Comment(BaseModel):
    file: str
    line: int
    severity: Literal["error", "warning", "info"]
    rule_id: str
    message: str
    suggestion: str | None = None


class LLMOutput(BaseModel):
    comments: list[Comment]


class ReviewResult(BaseModel):
    comments: list[Comment] = []
    skipped_files: list[str] = []
    failed_chunks: list[dict] = []
    dropped_invalid_lines: int = 0


def parse_llm_output(raw: str | None) -> list[Comment]:
    if not isinstance(raw, str) or not raw.strip():
        raise LLMInvalidOutputError("Bad LLM output: empty response")
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return LLMOutput(**json.loads(text)).comments
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        raise LLMInvalidOutputError(f"Bad LLM output: {e}") from e


async def _review_chunk(llm, system: str, user: str) -> list[Comment]:
    raw = await llm.complete(system, user)
    try:
        return parse_llm_output(raw)
    except LLMInvalidOutputError:
        logger.warning("Invalid JSON from LLM, re-prompting once")
        raw = await llm.complete(system, user + "\n\nYour last reply was invalid. Return ONLY valid JSON.")
        return parse_llm_output(raw)


async def review_diff(diff_text: str, standards: Standards, llm) -> ReviewResult:
    result = ReviewResult()
    reviewable = []
    for f in parse_diff(diff_text):
        if not f.reviewable or standards.is_ignored(f.path):
            result.skipped_files.append(f.path)
        else:
            reviewable.append(f)
    valid = {f.path: f.added_line_numbers for f in reviewable}
    seen: set[tuple] = set()

    for chunk in chunk_files(reviewable, settings.max_chunk_chars):
        system = build_system_prompt(standards, {f.language for f in chunk})
        user = build_user_prompt(chunk)[: settings.max_chunk_chars * 2]  # hard cap for huge files
        try:
            comments = await _review_chunk(llm, system, user)
        except (LLMUnavailableError, LLMRateLimitError, LLMInvalidOutputError) as e:
            result.failed_chunks.append({"files": [f.path for f in chunk], "error": str(e)})
            continue  # graceful degradation: other chunks still reviewed
        for c in comments:
            if c.line not in valid.get(c.file, set()):
                result.dropped_invalid_lines += 1
                continue
            key = (c.file, c.line, c.rule_id)
            if key not in seen:
                seen.add(key)
                result.comments.append(c)
    return result
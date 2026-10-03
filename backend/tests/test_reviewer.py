import json
import pytest
from app.config import settings
from app.errors import LLMUnavailableError
from app.llm_client import LLMClient
from app.reviewer import parse_llm_output, review_diff
from app.standards import Standards, load_standards, parse_standards
from app.errors import LLMInvalidOutputError, StandardsError

DIFF = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 import os
+password = "abc"
+x = 1
"""


class FakeLLM:
    def __init__(self, replies): self.replies, self.calls = list(replies), 0
    async def complete(self, system, user):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception): raise r
        return r


def good(line=2):
    return json.dumps({"comments": [{"file": "app.py", "line": line, "severity": "error",
                                      "rule_id": "G1", "message": "secret"}]})


async def test_valid_comment_kept():
    r = await review_diff(DIFF, Standards(), FakeLLM([good()]))
    assert len(r.comments) == 1


async def test_invalid_line_dropped():
    r = await review_diff(DIFF, Standards(), FakeLLM([good(line=99)]))
    assert r.comments == [] and r.dropped_invalid_lines == 1


async def test_duplicates_removed():
    both = json.dumps({"comments": json.loads(good())["comments"] * 2})
    r = await review_diff(DIFF, Standards(), FakeLLM([both]))
    assert len(r.comments) == 1


async def test_reprompt_on_bad_json():
    llm = FakeLLM(["not json", good()])
    r = await review_diff(DIFF, Standards(), llm)
    assert llm.calls == 2 and len(r.comments) == 1


async def test_llm_failure_degrades_gracefully():
    r = await review_diff(DIFF, Standards(), FakeLLM([LLMUnavailableError("down")]))
    assert r.comments == [] and len(r.failed_chunks) == 1


async def test_ignored_path_skipped():
    s = Standards(ignore_paths=["app.py"])
    r = await review_diff(DIFF, s, FakeLLM([]))
    assert r.skipped_files == ["app.py"]


def test_fenced_json_parsed():
    assert len(parse_llm_output("```json\n" + good() + "\n```")) == 1


def test_invalid_output_raises():
    with pytest.raises(LLMInvalidOutputError):
        parse_llm_output("{}oops")


def test_empty_output_raises():
    with pytest.raises(LLMInvalidOutputError):
        parse_llm_output(None)


def test_standards_invalid_yaml():
    with pytest.raises(StandardsError):
        parse_standards("languages: 5")


def test_standards_rules_for():
    s = parse_standards("global_rules: [{id: G1, description: d}]\nlanguages: {python: [{id: P1, description: d}]}")
    assert [r.id for r in s.rules_for("python")] == ["G1", "P1"]


def test_standards_missing_file_falls_back_to_default():
    s = load_standards("does-not-exist.yml")
    assert s == Standards()


async def test_llm_client_retries_then_raises(monkeypatch):
    monkeypatch.setattr(settings, "simulate_llm_failure", True)
    monkeypatch.setattr(settings, "retry_base_delay", 0)
    with pytest.raises(LLMUnavailableError):
        await LLMClient().complete("s", "u")
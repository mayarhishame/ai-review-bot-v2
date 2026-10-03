from app.diff_parser import parse_diff
from app.github_client import format_comment, format_summary
from app.prompt_builder import build_system_prompt, build_user_prompt
from app.reviewer import Comment, ReviewResult
from app.standards import Rule, Standards


def test_format_comment_includes_rule_and_suggestion():
    c = Comment(file="a.py", line=1, severity="error", rule_id="G1", message="secret", suggestion="use env")
    text = format_comment(c)
    assert "G1" in text and "ERROR" in text and "use env" in text


def test_summary_reports_failed_chunks():
    r = ReviewResult(failed_chunks=[{"files": ["app.py"], "error": "down"}])
    assert "incomplete" in format_summary(r)


def test_summary_counts_issues():
    r = ReviewResult(comments=[Comment(file="a.py", line=1, severity="info", rule_id="X", message="m")])
    assert "1" in format_summary(r)


def test_prompt_marks_diff_as_untrusted():
    assert "untrusted" in build_system_prompt(Standards(), {"python"}).lower()


def test_prompt_without_rules_has_default():
    assert "no custom rules" in build_system_prompt(Standards(), {"python"})


def test_typescript_rules_in_prompt():
    standards = Standards(
        global_rules=[Rule(id="G1", description="No hardcoded secrets", severity="error")],
        languages={"typescript": [Rule(id="TS1", description="No any type", severity="warning")]},
    )
    prompt = build_system_prompt(standards, {"python", "typescript"})
    assert "G1" in prompt and "TS1" in prompt
    assert prompt.count("G1") == 1  # global rule not duplicated across languages


def test_build_user_prompt_renders_each_file():
    diff = (
        "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
        "@@ -1,1 +1,2 @@\n import os\n+x = 1\n"
    )
    files = parse_diff(diff)
    prompt = build_user_prompt(files)
    assert "FILE: a.py (python)" in prompt
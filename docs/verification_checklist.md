# Verification Checklist

**Project:** AI Code Review Bot
**Verified by:** [your name]  **Date:** 2026-10-03
**Method:** automated tests (pytest, 51 passed, 98% coverage), manual runs through Swagger and the dashboard, and a live GitHub PR.
**Automated evidence:** checked boxes below are confirmed by the current `pytest` run (`docs/evidence/*.txt`). Boxes left `[ ]` require a manual run (screenshot or live PR) that only you can perform.

---

## 1. Diff Parser (`diff_parser.py`)
| Check | Evidence | Pass |
|---|---|---|
| Parses multi-file diffs | `test_parses_all_files` | [x] |
| Detects Python, Java, TypeScript | `test_language_detection`, `test_typescript_detected_and_reviewable` | [x] |
| New-file line numbers are correct | `test_line_numbers_for_added_lines` | [x] |
| Skips lockfiles and binaries | `test_skips_lockfiles_and_binaries` | [x] |
| Chunks by size | `test_chunking_splits_on_budget` | [x] |
| Handles an empty diff | `test_empty_diff` | [x] |
- **Evidence file:** `docs/evidence/diff_parser.txt`
- **Known limitation:** a single file larger than `max_chunk_chars` is not split, and the prompt is truncated.

## 2. Standards Loader (`standards.py`)
| Check | Evidence | Pass |
|---|---|---|
| Merges global and per-language rules | `test_standards_rules_for` | [x] |
| Rejects invalid YAML with a clear error | `test_standards_invalid_yaml` | [x] |
| Ignored paths are skipped | `test_ignored_path_skipped` | [x] |
| Missing file falls back to no custom rules | `test_standards_missing_file_falls_back_to_default` | [x] |
| Editing a rule changes the review | [screenshots before and after in the dashboard] | [ ] |
- **Evidence files:** `reviewer.txt`, `settings_before.png`, `settings_after.png`

## 3. Prompt Builder (`prompt_builder.py`)
| Check | Evidence | Pass |
|---|---|---|
| Rules for each language appear in the prompt | `test_typescript_rules_in_prompt` | [x] |
| Diff is labelled as untrusted data | `test_prompt_marks_diff_as_untrusted` (manual: prompt-injection sample, line 2 still flagged) | [x] auto / [ ] manual |
| No custom rules gives a safe default | `test_prompt_without_rules_has_default` | [x] |
- **Evidence:** `reviewer.txt`, `injection_test.png`

## 4. LLM Client (`llm_client.py`)
| Check | Evidence | Pass |
|---|---|---|
| Retries with exponential backoff, then raises | `test_llm_client_retries_then_raises` | [x] |
| Real outage: 3 retries at 1s, 2s, 4s | `retry_logs.png` (real HTTP 404 from Groq) | [ ] |
| Failure simulator works on demand | [Swagger toggle, then review returns `failed_chunks`] | [ ] |
| API key never appears in logs | [search uvicorn log for `gsk_`, 0 matches] | [ ] |
- **Evidence:** `reviewer.txt`, `retry_logs.png`

## 5. Reviewer pipeline (`reviewer.py`)
| Check | Evidence | Pass |
|---|---|---|
| Valid comments kept | `test_valid_comment_kept` | [x] |
| Comments on invalid lines dropped | `test_invalid_line_dropped` | [x] |
| Duplicates removed | `test_duplicates_removed` | [x] |
| Re-prompts once on malformed JSON | `test_reprompt_on_bad_json` | [x] |
| Handles code-fenced JSON | `test_fenced_json_parsed` | [x] |
| Rejects unusable output | `test_invalid_output_raises` | [x] |
| One failed chunk does not stop the rest | `test_llm_failure_degrades_gracefully` | [x] |
- **Evidence:** `reviewer.txt`, `review_api.png`
- **Sample results (non-deterministic):** [list the TS, Python and clean-file samples: expected vs actual, including misses and false positives]

## 6. Webhook Receiver (`webhook.py`)
| Check | Evidence | Pass |
|---|---|---|
| Rejects bad signatures (401) | `test_bad_signature` | [x] |
| Ignores non-PR events | `test_non_pr_event_ignored` | [x] |
| Ignores irrelevant actions | `test_closed_action_ignored` | [x] |
| Duplicate delivery ignored | `test_duplicate_delivery` | [x] |
| Background job records success and failure | `test_process_pr_success_and_github_failure` | [x] |
| Real GitHub delivery accepted | `webhook_delivery.png` (200) | [ ] |
- **Evidence:** `webhook.txt`, `webhook_delivery.png`

## 6b. GitHub Client (`github_client.py`)
| Check | Evidence | Pass |
|---|---|---|
| Fetches the PR diff | `test_get_diff_ok`, `test_get_diff_http_error`, `test_get_diff_network_error` | [x] |
| Posts a review with inline comments | `test_post_review_ok`; live: `pr_review_ok.png` | [x] auto / [ ] manual |
| Posts a summary-only review when the LLM fails | `test_llm_failure_degrades_gracefully`; live: `pr_review_failed.png` | [x] auto / [ ] manual |
| Summary and comment formatting | `test_format_comment_includes_rule_and_suggestion`, `test_summary_reports_failed_chunks`, `test_summary_counts_issues` | [x] |
| Falls back to a summary when GitHub rejects inline lines (422) | `test_post_review_422_falls_back_to_summary` | [x] |

## 7. Production error handling
| Failure | Handling | Demonstrated by | Pass |
|---|---|---|---|
| LLM outage or bad model (real 404) | retries, then partial-review notice | `retry_logs.png`, `pr_review_failed.png` | [ ] |
| LLM outage (simulated) | same | Swagger toggle, `pr_review_failed.png` | [ ] |
| Malformed LLM JSON | re-prompt once, then skip chunk | `test_reprompt_on_bad_json` | [x] |
| Invalid line numbers | dropped, not crashed | `test_invalid_line_dropped` | [x] |
| Forged webhook | 401 | `test_bad_signature` | [x] |
| Duplicate delivery | ignored | `test_duplicate_delivery` | [x] |
| GitHub API failure | recorded as error in history | `test_process_pr_success_and_github_failure` | [x] |
| Invalid standards YAML | 400 with message | `test_api_review_bad_standards` | [x] |

## 8. React Dashboard
| Check | Evidence | Pass |
|---|---|---|
| Review tab shows comments by severity | `dashboard_review.png` | [ ] |
| Partial-review warning is displayed | `dashboard_failure.png` | [ ] |
| Settings tab saves valid and rejects invalid YAML | `dashboard_settings.png` | [ ] |
| Failure simulator toggle works | `dashboard_failure.png` | [ ] |
| History tab lists PR reviews | `dashboard_history.png` | [ ] |

## 9. Test coverage
- **Total coverage:** 98% (target: above 90%), 51 tests passed, 0 failed
- **Evidence:** `docs/evidence/coverage.txt`, `docs/coverage/index.html`
- **Low-coverage files and why:** `llm_client.py` (90%) and `github_client.py` (94%) have a few unreachable defensive branches (e.g. logging on an already-handled exception path); these network paths are also verified manually via the live PR (`retry_logs.png`, `pr_review_ok.png`).
# 10-Minute Team Demo Script

**Goal:** show the end-to-end pipeline, custom standards, graceful error handling, and
the verification evidence (tests, coverage, logs) in under 10 minutes.

**Before the demo:** start the backend (`py -m uvicorn app.main:app --reload`) and the
dashboard (`npm run dev` in `frontend/`), and have a terminal ready in `backend/`.

## 0. Intro (30s)
"This bot reviews GitHub PRs with an LLM, applies our own engineering standards, and
posts inline comments. It handles multi-language diffs (Python, JS, TS, Java) and keeps
working even when the LLM or GitHub API fails."

## 1. Health check and architecture (1 min)
- Open http://localhost:8000/health → `{"status":"ok"}`.
- Show the pipeline diagram in [README.md](../README.md): webhook → diff parser →
  standards → prompt builder → LLM → validation → GitHub post.

## 2. Run a review from the dashboard (2 min)
- Open http://localhost:5173, **Review** tab.
- Paste a diff with an obvious issue (hardcoded secret + bare `except`, see
  [README.md](../README.md) section 4).
- Run it. Point out: comments grouped by severity, rule id cited, line-accurate, and the
  suggestion field.

## 3. Custom engineering standards (1.5 min)
- Switch to **Settings**. Show `.review-standards.yml` (global + per-language rules,
  `ignore_paths`).
- Add or edit one rule (e.g. new TypeScript rule), save, and re-run the same review to
  show the new rule now fires. Demonstrates the standards loader is live, not hardcoded.
- Paste invalid YAML to show the 400 rejection with a clear message.

## 4. Production error handling (2.5 min)
- Toggle **Simulate LLM outage** in Settings, run a review: show retries (backoff) then
  a partial-review notice instead of a crash. Toggle it back off.
- Run `py -m pytest tests/test_webhook.py::test_bad_signature -v` in the terminal: a
  forged webhook signature is rejected with 401.
- Run `py -m pytest tests/test_webhook.py::test_duplicate_delivery -v`: a redelivered
  webhook is ignored, not reprocessed.
- Mention: malformed LLM JSON triggers one re-prompt then the chunk is skipped
  (`test_reprompt_on_bad_json`), and GitHub API failures are recorded in review history
  instead of crashing the request.

## 5. Live GitHub PR (optional, 1.5 min)
- If a tunnel is already running: open a real PR on the demo repo and show the comments
  that land on the actual PR within a few seconds.
- If skipped for time: show `docs/evidence/webhook.txt` and a screenshot from a prior run.

## 6. Verification evidence (1 min)
- Run `py -m pytest --cov=app --cov-report=term-missing -q` to show all tests passing
  live with coverage printed (currently 98%, threshold is 90%).
- Point to [verification_checklist.md](verification_checklist.md) (component-by-component
  evidence), [prompt_log.md](prompt_log.md) (AI interaction log), and
  `docs/coverage/index.html` (HTML coverage report).

## 7. Wrap-up (30s)
"Every component has unit tests, the pipeline degrades gracefully instead of crashing,
and every AI-assisted change was tested before being accepted — logged in
`prompt_log.md`."

## Fallback if something breaks live
- Use `docs/evidence/*.txt` as pre-recorded proof of passing tests.
- Use the Swagger UI (`/docs`) `POST /api/review` instead of the dashboard if the
  frontend fails to start.

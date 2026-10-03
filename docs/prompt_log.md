# AI Interaction Log: AI Code Review Bot

**Tool:** Claude (Anthropic), chat interface
**Policy:** Every AI output was run, tested, or checked before acceptance. Entries record what was accepted, modified or rejected, and the evidence.

---

## Entry 001: Project planning
- **Date/Time:** [ ]
- **Component:** Architecture and roadmap
- **Prompt:** Asked for the steps and topics to study for a multi-language AI PR review bot with custom standards, a prompt log, a verification checklist, a coverage report, error handling, and a 10-minute demo.
- **Output summary:** Pipeline design (webhook, diff parser, standards loader, prompt builder, LLM client, publisher), study topics, demo structure.
- **Accepted / modified / rejected:** Accepted the component breakdown. [Note anything you changed.]
- **Verification:** Compared the plan against the assignment requirements.

## Entry 002: Stack selection
- **Prompt:** Requested React + FastAPI with a free LLM, and asked whether clarification was needed.
- **Output summary:** Proposed FastAPI, React/Vite, Groq (free tier), a provider-agnostic LLM client, and a PAT-based GitHub integration.
- **Accepted / modified / rejected:** Accepted. [State your reasons.]
- **Verification:** Confirmed the Groq key works (Entry 009).

## Entry 003: Config, errors and diff parser
- **Prompt:** Asked for the first code with a 15-day plan.
- **Output summary:** `config.py`, `errors.py`, `diff_parser.py` (unified-diff parsing, language detection, chunking) and unit tests.
- **Accepted / modified / rejected:** [e.g. added a language, extended tests]
- **Verification:** `pytest` output: [paste]. Checklist section: Diff Parser.

## Entry 004: Full pipeline in one day
- **Prompt:** Asked for all steps and the structure in one day.
- **Output summary:** Standards loader (YAML), prompt builder, LLM client with retries and a failure simulator, reviewer with JSON validation and line-number checks, GitHub client, HMAC webhook with idempotency, React dashboard, tests.
- **Accepted / modified / rejected:** [list what you changed]
- **Verification:** `pytest --cov` results: [paste]. Dashboard screenshots: [attach].

## Entry 005: Debugging, ImportError for `settings`
- **Prompt:** Pasted the uvicorn traceback (`cannot import name 'settings'`).
- **Output summary:** Diagnosed an empty or unsaved `config.py`, supplied the full file and an install command for missing packages.
- **Accepted / modified / rejected:** Accepted. Replaced the file and installed dependencies.
- **Verification:** Server started without the error.

## Entry 006: Debugging, missing error classes and `parse_diff`
- **Prompt:** Pasted two further ImportErrors (`LLMUnavailableError`, `parse_diff`).
- **Output summary:** Identified incomplete `errors.py` and `diff_parser.py`, supplied full files and a per-module import check.
- **Accepted / modified / rejected:** Accepted.
- **Verification:** `uvicorn` printed "Application startup complete".

## Entry 007: Secrets and credentials
- **Prompt:** Asked where to get the Groq key, webhook secret and GitHub token.
- **Output summary:** Step-by-step sources for each key, `.env` format, `.gitignore` guidance.
- **Accepted / modified / rejected:** Accepted. I accidentally pasted my Groq key into the ngrok command, so I revoked it and created a new one. [Confirm this is true.]
- **Verification:** New key stored only in `backend/.env`, which is git-ignored.

## Entry 008: Public tunnel for webhooks
- **Prompt:** Reported `ngrok` not recognized, then a token error, then an "agent too old" error, then ERR_NGROK_8012.
- **Output summary:** PATH refresh, correct authtoken, `ngrok update`, and using `127.0.0.1:8000` to fix the IPv6 mismatch.
- **Accepted / modified / rejected:** Accepted all fixes.
- **Verification:** `/health` returned `{"status":"ok"}` through the public URL. [Screenshot]

## Entry 009: Live PR test and real LLM failure
- **Prompt:** Pasted the PR comment ("review incomplete") and the logs showing HTTP 404 from Groq.
- **Output summary:** Diagnosed a retired model name. Recommended listing available models and choosing a current one, plus logging the response body.
- **Accepted / modified / rejected:** Listed models with the Groq API and set `GROQ_MODEL=[model you chose]`. [Confirm.] Added error-body logging. [Confirm.]
- **Verification:** Logs show retries at 1s/2s/4s then graceful degradation (production error handling evidence). After the fix: [paste a successful review].

## Entry 010: TypeScript support and test samples
- **Prompt:** Asked how to test with TypeScript, then for sample code.
- **Output summary:** TS rules for `.review-standards.yml`, buggy `.ts`/`.tsx` samples, a clean file, a prompt-injection test, and a chunking test.
- **Accepted / modified / rejected:** [list which samples you ran]
- **Verification:** Bot output per sample: [paste what it flagged, including misses].
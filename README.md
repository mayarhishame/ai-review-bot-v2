# AI Code Review Bot

A bot that reviews GitHub pull requests using an LLM (Groq), applies custom engineering
standards from a YAML file, and posts inline comments. It supports Python, JavaScript,
TypeScript and Java. It includes a React dashboard for manual reviews, editing standards,
and a failure simulator.

## How it works

PR opened → GitHub webhook → FastAPI verifies signature → fetch diff → parse and chunk
→ build prompt with standards → LLM → validate JSON and line numbers → post review.

## Project structure

```
ai-review-bot/
├── backend/            FastAPI app, tests
│   ├── app/            main, webhook, reviewer, llm_client, github_client, ...
│   ├── tests/
│   ├── pytest.ini
│   └── .env.example
├── frontend/           React + Vite dashboard
├── docs/               prompt_log.md, verification_checklist.md, evidence/, coverage/
└── .review-standards.yml
```

## Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- A free Groq API key: https://console.groq.com (API Keys)
- For real PR testing only: a GitHub account, a test repo, a fine-grained token
  (Pull requests: read/write, Contents: read), and ngrok or cloudflared

## 1. Backend setup

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```
macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`.
If PowerShell blocks activation: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`.

If `requirements.txt` is missing:
```powershell
py -m pip install fastapi uvicorn pydantic-settings pyyaml httpx tenacity pytest pytest-cov pytest-asyncio
```

## 2. Configuration

Copy `backend/.env.example` to `backend/.env` and fill it in:

| Variable | Where to get it |
|---|---|
| `GROQ_API_KEY` | Groq console, API Keys (starts with `gsk_`) |
| `GROQ_MODEL` | A current chat model ID. List them with the command below |
| `GITHUB_TOKEN` | GitHub, Settings, Developer settings, Fine-grained tokens (only for real PRs) |
| `WEBHOOK_SECRET` | Any random string: `py -c "import secrets; print(secrets.token_hex(20))"` |

List the models your key can use:
```powershell
$k = "YOUR_GROQ_KEY"
(Invoke-RestMethod -Uri "https://api.groq.com/openai/v1/models" -Headers @{Authorization="Bearer $k"}).data | Select-Object id
```
Model names change over time. A `404` from the LLM in the logs usually means the model
name is retired. Never commit `.env`.

## 3. Run the backend

Always run from the `backend/` folder with the venv active, because the standards path is
relative (`../.review-standards.yml`):
```powershell
py -m uvicorn app.main:app --reload
```
- Health check: http://localhost:8000/health returns `{"status":"ok"}`
- API docs: http://localhost:8000/docs

Restart the server after editing `.env`, because settings are read at startup.

## 4. Test a review without GitHub

In http://localhost:8000/docs, open `POST /api/review`, click Try it out, and send:
```json
{"diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,5 @@\n import os\n+API_KEY = \"sk-live-12345\"\n+def process(d):\n+    try:\n+        return d[\"x\"]\n+    except:\n+        pass\n"}
```
Expected: comments for the hardcoded secret (G1) and the bare except (PY2). LLM output
varies slightly between runs.

## 5. Run the React dashboard

In a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The backend must be running on port 8000.

| Tab | What it does |
|---|---|
| review | Paste a diff (`git diff main`) and run a review |
| settings | Edit the YAML standards, and toggle the LLM failure simulator |
| history | Shows reviews triggered by real pull requests |

## 6. Custom engineering standards

Edit `.review-standards.yml` (or use the settings tab):
```yaml
global_rules:
  - {id: G1, description: "No hardcoded secrets", severity: error}
languages:
  python:
    - {id: PY2, description: "No bare except clauses", severity: error}
ignore_paths: ["tests/", "migrations/"]
```
Valid severities: `error`, `warning`, `info`. Supported languages: `python`,
`javascript`, `typescript`, `java`. Invalid YAML is rejected with a 400 error.

## 7. Run the tests and coverage

From `backend/`:
```powershell
py -m pytest -v
py -m pytest --cov=app --cov-report=term-missing --cov-report=html:../docs/coverage
```
Open `docs/coverage/index.html` for the HTML report. Tests mock the LLM and GitHub, so
no keys or network are needed.

## 8. Connect to a real GitHub pull request

1. Keep the backend running.
2. Start a tunnel in another terminal:
```powershell
   ngrok config add-authtoken YOUR_NGROK_TOKEN   # once
   ngrok http 127.0.0.1:8000
```
   Alternative with no account: `cloudflared tunnel --url http://127.0.0.1:8000`.
3. Check `https://YOUR-TUNNEL-URL/health` returns `{"status":"ok"}`.
4. In the test repo, go to Settings, Webhooks, Add webhook:
   - Payload URL: `https://YOUR-TUNNEL-URL/webhook`
   - Content type: `application/json`
   - Secret: the same value as `WEBHOOK_SECRET`
   - Events: Pull requests only
5. Open a PR with some buggy code. The review appears on the PR after a few seconds.
6. To re-run, push a new commit. Do not use "Redeliver", because duplicates are ignored.

The tunnel URL changes when you restart the tunnel, so update it in the webhook settings.

## 9. Demonstrate error handling

| Scenario | How |
|---|---|
| LLM outage | Turn on "Simulate LLM outage" in settings, then run a review. The result shows a partial-review notice after retries (1s, 2s, 4s). |
| Bad webhook signature | `pytest tests/test_webhook.py::test_bad_signature` |
| Malformed LLM JSON | `pytest tests/test_reviewer.py::test_reprompt_on_bad_json` |
| Duplicate delivery | `pytest tests/test_webhook.py::test_duplicate_delivery` |

Turn the simulator off afterwards.

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named uvicorn` | The venv isn't active. Activate it first |
| `ImportError: cannot import name ...` | A file in `backend/app/` is empty or unsaved |
| LLM `HTTP 404` in logs | Model name retired. Set `GROQ_MODEL` to a current one |
| LLM `HTTP 401` | Wrong or missing `GROQ_API_KEY`. Restart after editing `.env` |
| LLM `HTTP 429` | Free rate limit. Wait a minute |
| Webhook delivery `401` | `WEBHOOK_SECRET` differs from the GitHub secret |
| ngrok `ERR_NGROK_8012` | Use `ngrok http 127.0.0.1:8000`, and make sure uvicorn is running |
| ngrok "agent too old" | Run `ngrok update` |
| CORS error in dashboard | The frontend must run on port 5173 |

## Known limitations

- A single file larger than `max_chunk_chars` is not split, and its prompt is truncated.
- Review history is in memory and resets when the server restarts.
- LLM output is non-deterministic, so comments can vary between runs.
- Code in the diff is sent to the LLM provider. Do not use it on confidential code.

## Process documents

- `docs/prompt_log.md`: log of AI interactions
- `docs/verification_checklist.md`: evidence per component
- `docs/coverage/index.html`: coverage report
- `docs/demo_script.md`: 10-minute team demo script

## Quick Start: run the backend

### A. One-time setup

**1. Open a terminal in the project folder and go to `backend`:**
```powershell
cd ai-review-bot\backend
```

**2. Create and activate a virtual environment:**
```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```
The prompt must now start with `(.venv)`. (macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`)

**3. Install the dependencies:**
```powershell
py -m pip install -r requirements.txt
```

**4. Create your `.env` file:**
```powershell
copy .env.example .env
```
Open `backend\.env` and fill in:
```
GROQ_API_KEY=gsk_your_own_key
GROQ_MODEL=openai/gpt-oss-120b
WEBHOOK_SECRET=any_random_string
GITHUB_TOKEN=
```
Only `GROQ_API_KEY` is required to try the dashboard. `GITHUB_TOKEN` is needed only for real pull requests.

### B. Start the backend (every time)

```powershell
cd ai-review-bot\backend
.venv\Scripts\Activate.ps1
py -m uvicorn app.main:app --reload
```
Wait for `Application startup complete.` Leave this terminal open.

### C. Check that it works

- Open http://localhost:8000/health. You should see `{"status":"ok"}`.
- Open http://localhost:8000/docs, then `POST /api/review`, then **Try it out**, and send a diff to get review comments.

### D. Stop it

Press `Ctrl+C` in the backend terminal. After editing `.env`, stop and start again, because settings are read only at startup.

### Which terminal runs what

| Terminal | Folder | Command | Needed for |
|---|---|---|---|
| 1: Backend | `backend/` (venv active) | `py -m uvicorn app.main:app --reload` | everything |
| 2: Dashboard | `frontend/` | `npm install` (once), then `npm run dev` | the web UI at http://localhost:5173 |
| 3: Tunnel | anywhere | `ngrok http 127.0.0.1:8000` | real GitHub PRs only |
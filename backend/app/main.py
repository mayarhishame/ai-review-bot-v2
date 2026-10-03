import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from . import store
from .config import settings
from .errors import *
from .llm_client import LLMClient
from .reviewer import review_diff
from .standards import parse_standards
from .webhook import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title="AI Code Review Bot")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

STATUS = {InvalidSignatureError: 401, DiffParseError: 400, StandardsError: 400,
          LLMRateLimitError: 429, LLMUnavailableError: 503, GitHubAPIError: 502}


@app.exception_handler(ReviewBotError)
async def bot_error_handler(request: Request, exc: ReviewBotError):
    return JSONResponse({"detail": str(exc)}, status_code=STATUS.get(type(exc), 500))


class ReviewRequest(BaseModel):
    diff: str
    standards_yaml: str | None = None


class StandardsBody(BaseModel):
    yaml: str


class SimBody(BaseModel):
    enabled: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/review")
async def api_review(req: ReviewRequest):
    from .standards import load_standards
    standards = parse_standards(req.standards_yaml) if req.standards_yaml else load_standards(settings.standards_path)
    return await review_diff(req.diff, standards, LLMClient())


@app.get("/api/standards")
def get_standards():
    try:
        return {"yaml": open(settings.standards_path, encoding="utf-8").read()}
    except FileNotFoundError:
        return {"yaml": ""}


@app.put("/api/standards")
def put_standards(body: StandardsBody):
    parse_standards(body.yaml)  # validate before saving
    open(settings.standards_path, "w", encoding="utf-8").write(body.yaml)
    return {"status": "saved"}


@app.get("/api/reviews")
def reviews():
    return list(store.history)


@app.get("/api/simulate-failure")
def sim_state():
    return {"enabled": settings.simulate_llm_failure}


@app.post("/api/simulate-failure")
def sim_set(body: SimBody):
    settings.simulate_llm_failure = body.enabled
    return {"enabled": body.enabled}
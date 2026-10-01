"""FastAPI app: /api/chat, /api/knowledge, and the built React frontend (if present)."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field

from . import config
from .agent import run_agent
from .knowledge import load_registry

app = FastAPI(title=config.AGENT_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)


@app.get("/api/health")
def health():
    return {"status": "ok", "agent": config.AGENT_NAME}


@app.get("/api/knowledge")
def knowledge():
    return [{"key": e.key, "file": e.file, "description": e.description} for e in load_registry().values()]


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Last message must be from the user.")
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Server is missing GEMINI_API_KEY.")
    try:
        return run_agent([m.model_dump() for m in req.messages])
    except genai_errors.APIError as e:
        if e.code in (400, 401, 403):
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is invalid or not permitted.")
        raise HTTPException(status_code=502, detail=f"Model service error ({e.code}). Please retry.")
    except Exception:
        logging.exception("Agent failed")
        raise HTTPException(status_code=502, detail="The agent failed to respond. Please retry.")


# Serve the built frontend (single-service deployment). Absent in dev: use Vite.
if config.FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (config.FRONTEND_DIST / path).resolve()
        if path and candidate.is_file() and config.FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(config.FRONTEND_DIST / "index.html")

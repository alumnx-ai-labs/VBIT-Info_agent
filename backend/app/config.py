"""Central configuration. All paths are relative to the repository root so the
app behaves identically locally and after deployment from the GitHub checkout."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

DATA_DIR = ROOT_DIR / "data"
KNOWLEDGE_YAML = ROOT_DIR / "knowledge.yaml"
JOBS_FILE = DATA_DIR / "jobs.md"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

AGENT_NAME = "VBIT agent"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "VBIT-Agent")

# LangChain reads these from the environment; enable tracing only when a key is present.
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
MODEL = os.getenv("VBIT_MODEL", "gemini-2.5-flash")
MAX_TOOL_ROUNDS = 6
MAX_HISTORY_MESSAGES = 20
CORS_ORIGINS = [
    o.strip().rstrip("/")
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
# Optional, e.g. https://vbit-agent.*\.vercel\.app to also allow Vercel preview deployments
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX") or None

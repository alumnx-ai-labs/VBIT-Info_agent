# VBIT agent

Chat assistant for VBIT college. Python/FastAPI backend (LangChain + Gemini + Tavily + LangSmith), React (Vite) frontend, no database: all knowledge lives in `data/*.txt` and is described by `knowledge.yaml`.

> The files in `data/` contain **sample content**. Replace them with verified VBIT information before real use.

## How it works

```
Question -> model reads the catalogue built from knowledge.yaml -> knowledge_search(file_name, query)
         (once per relevant file) -> answer from retrieved text + "Source: <file>"
```

- File selection is done by the model from the descriptions in `knowledge.yaml`; there is no hard-coded routing.
- `knowledge_search` only accepts files registered in `knowledge.yaml` (the tool schema enum is generated from it, and the server re-checks and blocks path traversal).
- If the local knowledge base cannot answer a VBIT question, the agent falls back to **Tavily** web search and clearly labels web sources.
- **Resume matching**: paste a resume in the chat and the `match_jobs` tool scores it against the sample listings in `data/jobs.md` (keyword/skill overlap, a screening aid only).
- **LangSmith**: set `LANGSMITH_API_KEY` (and optionally `LANGSMITH_PROJECT`) to trace every agent run.

## Add knowledge

1. Put `newtopic.txt` in `data/`. Use `# Heading` lines and blank lines between sections.
2. Register it in `knowledge.yaml` with a clear `description`. No code changes or restart needed.

## Run locally

```bash
cp .env.example .env            # set GEMINI_API_KEY, TAVILY_API_KEY, LANGSMITH_API_KEY
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000   # from repo root

cd frontend && npm install && npm run dev            # http://localhost:5173 (proxies /api)
```

Single-service mode: `cd frontend && npm run build`, then open http://localhost:8000 (FastAPI serves `frontend/dist`).

## Deploy

### Option A: everything on Render
`Dockerfile` builds the frontend and serves UI and API from one container. Create a Render Web Service (runtime Docker) from the GitHub repo and set `GEMINI_API_KEY`.

### Option B: backend on Render, frontend on Vercel
1. **Render**: New Web Service (or Blueprint via `render.yaml`), runtime Docker. Environment variables:
   - `GEMINI_API_KEY` = your key
   - `CORS_ORIGINS` = your Vercel URL, e.g. `https://vbit-agent.vercel.app` (comma separate several)
   - optional `CORS_ORIGIN_REGEX` to also allow Vercel preview URLs
2. **Vercel**: import the repo, set **Root Directory** to `frontend` (Vite is auto-detected). Environment variable:
   - `VITE_API_URL` = the Render URL, e.g. `https://vbit-agent-api.onrender.com`
3. Redeploy Vercel after changing `VITE_API_URL` (it is baked in at build time).

Render's free tier sleeps when idle, so the first request after a pause can take about 30-60 seconds.

Also set `TAVILY_API_KEY` and `LANGSMITH_API_KEY` on Render. Optional env vars: `VBIT_MODEL`, `LANGSMITH_PROJECT`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`.

## Tests

```bash
pytest backend
```

## Code-auditor subagent (Google Antigravity)

The repo ships a read-only security/code-quality subagent at [`.agents/agents/code-auditor.md`](.agents/agents/code-auditor.md) (Markdown with YAML frontmatter). It is project-level, so Antigravity discovers it automatically when you open this repo.

### Trigger it on your local copy

1. Clone the repo and run the app locally (see [Run locally](#run-locally)): backend on http://localhost:8000, frontend on http://localhost:5173.
2. Open the repo folder (the one containing `.agents/`) in Google Antigravity.
3. Select a Gemini model in the chat (e.g. Gemini 3.6 Flash) and start a new conversation. (`/agents` may not exist in every Antigravity version.)
4. In the chat, ask the main agent to delegate, e.g.:
   > Use the code-auditor subagent to do a code-quality and best-practices review of this repo, including how API keys and file paths are handled.

   Or narrow it: *"Use the code-auditor subagent to check `backend/app/tools.py` for path traversal and prompt injection."*
5. The main agent calls it through its `invoke_subagent` tool, guided by the subagent's `description`.
6. Watch the chat for the `invoke_subagent` call and the separate `code-auditor` run. If your version has `/agents`, you can open the run there to see its reasoning log and tool calls.
7. Read the report (Critical / Warning / Suggestion, with file and line). The subagent is read-only; apply fixes yourself or ask the main agent to.

To customise it, edit the frontmatter (`tools`, `model`, `commandExecutionPolicy`) or the system prompt in `code-auditor.md`; Antigravity picks up changes on save. To make it available in all projects, copy it to `~/.gemini/config/agents/`.

### Claude Code version

The same subagent exists at [`.claude/agents/code-auditor.md`](.claude/agents/code-auditor.md) for Claude Code (the project-level folder Claude Code reads). After running the app locally, open the repo in Claude Code and ask: *"Use the code-auditor subagent to review this repo."* It runs read-only and reports Critical / Warning / Suggestion findings.

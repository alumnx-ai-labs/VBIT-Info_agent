"""Agent tools: knowledge_search (local files), tavily_vbit_search (web fallback), match_jobs (resume)."""
import json
import re
from typing import Literal

from langchain_core.tools import tool
from pydantic import Field, create_model

from . import config
from .knowledge import STOPWORDS, KnowledgeError, registered_files, search_file


def knowledge_search(file_name: str, query: str) -> dict:
    try:
        return search_file(file_name, query)
    except KnowledgeError as e:
        return {"file": file_name, "found": False, "error": str(e)}


def tavily_vbit_search(query: str) -> dict:
    """Search the public web for VBIT information that is not in the local knowledge base."""
    if not config.TAVILY_API_KEY:
        return {"query": query, "error": "Web search is not configured (missing TAVILY_API_KEY)."}
    search_query = query if "VBIT" in query.upper() else f"VBIT {query}"
    try:
        from tavily import TavilyClient

        response = TavilyClient(api_key=config.TAVILY_API_KEY).search(
            query=search_query,
            search_depth="advanced",
            max_results=5,
            include_answer=True,
            include_raw_content=False,
        )
        return {
            "query": search_query,
            "answer": response.get("answer", ""),
            "results": [
                {"title": i.get("title", ""), "url": i.get("url", ""), "content": i.get("content", "")}
                for i in response.get("results", [])
            ],
        }
    except Exception as e:
        return {"query": search_query, "error": str(e)}


def _read_jobs() -> list[dict]:
    if not config.JOBS_FILE.is_file():
        raise FileNotFoundError(f"Jobs file not found: {config.JOBS_FILE.name}")
    jobs = []
    for block in re.split(r"(?m)^##\s+", config.JOBS_FILE.read_text(encoding="utf-8"))[1:]:
        lines = block.strip().splitlines()
        if not lines:
            continue
        fields = {}
        for line in lines[1:]:
            m = re.match(r"^\*\*([^*]+)\*\*:\s*(.+)$", line.strip())
            if m:
                fields[m.group(1).strip().lower()] = m.group(2).strip()
        jobs.append({"title": lines[0].strip(), "body": "\n".join(lines[1:]).strip(), "fields": fields})
    return jobs


def _job_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9+#.]+", text.lower())
    return {w.rstrip("s") if len(w) > 3 else w for w in words if w not in STOPWORDS}


def match_jobs(resume_text: str, top_k: int = 5) -> dict:
    """Match a pasted resume against jobs in jobs.md using transparent lexical scoring."""
    if not resume_text or not resume_text.strip():
        return {"error": "Resume text is empty."}
    try:
        jobs = _read_jobs()
    except Exception as e:
        return {"error": str(e)}
    if not jobs:
        return {"error": "No jobs were found in jobs.md."}

    resume_tokens = _job_tokens(resume_text)
    resume_lower = resume_text.lower()
    scored = []
    for job in jobs:
        job_tokens = _job_tokens(f"{job['title']} {job['body']}")
        score = len(resume_tokens & job_tokens) / max(len(job_tokens), 1)

        skills = [s.strip().lower() for s in re.split(r"[,;|]", job["fields"].get("skills", "")) if s.strip()]
        matched = [s for s in skills if s in resume_lower]
        missing = [s for s in skills if s not in resume_lower]
        if skills:
            score += 0.5 * len(matched) / len(skills)

        scored.append({
            "title": job["title"],
            "company": job["fields"].get("company", ""),
            "location": job["fields"].get("location", ""),
            "skills": skills,
            "matched_skills": matched,
            "missing_skills": missing,
            "score": round(score, 3),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return {
        "jobs_file": config.JOBS_FILE.name,
        "resume_match_method": "keyword/skill overlap; this is a screening aid, not a hiring decision",
        "matches": scored[:top_k],
    }


def build_tools() -> list:
    """Built per request so the allowed file names always match knowledge.yaml."""
    schema = create_model(
        "KnowledgeSearchInput",
        file_name=(Literal[tuple(registered_files())], Field(description="Registered knowledge file to search.")),
        query=(str, Field(description="Keywords or question to look for in that file.")),
    )

    @tool("knowledge_search", args_schema=schema)
    def knowledge_search_tool(file_name: str, query: str) -> str:
        """Search one VBIT knowledge file for information relevant to a query.
        Call once per file; call several times for questions spanning several files."""
        return json.dumps(knowledge_search(file_name, query))

    @tool("tavily_vbit_search")
    def tavily_vbit_search_tool(query: str) -> str:
        """Search the public internet for VBIT information that is not available in the local VBIT knowledge base."""
        return json.dumps(tavily_vbit_search(query))

    @tool("match_jobs")
    def match_jobs_tool(resume_text: str) -> str:
        """Match a candidate's resume text against the jobs listed in jobs.md and return the most relevant matches."""
        return json.dumps(match_jobs(resume_text))

    return [knowledge_search_tool, tavily_vbit_search_tool, match_jobs_tool]

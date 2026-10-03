"""LangChain tool-using agent (Gemini): local knowledge first, Tavily web fallback, resume job matching.
Runs are traced in LangSmith when LANGSMITH_API_KEY is set."""
import json

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.errors import GraphRecursionError

from . import config
from .knowledge import catalog_text
from .tools import build_tools

SYSTEM_PROMPT = """You are {name}, the information assistant for VBIT college.

You have no built-in knowledge of VBIT. Use the tools as follows.

PRIMARY VBIT KNOWLEDGE WORKFLOW
1. For a VBIT question, first use knowledge_search against the relevant local knowledge file(s).
2. If the local knowledge base contains the answer, answer from that retrieved text.
3. If the local knowledge base does not contain enough information to answer the VBIT question, use tavily_vbit_search to search the public internet.
4. Clearly distinguish local knowledge from web information. Never present a web result as if it came from the local knowledge base.
5. Do not invent facts. If neither the local knowledge nor the web search provides a reliable answer, say that the information could not be verified.
6. When using local knowledge, end with: "Source: <file1>, <file2>" listing the files actually used.
7. When using Tavily, include a short "Web sources:" section with the relevant source titles and URLs returned by the tool.

JOB-MATCHING WORKFLOW
- If the user provides a resume or asks which jobs match a resume, use match_jobs.
- The tool compares the resume against the jobs in jobs.md.
- Report the matching jobs, matched skills, and notable missing skills.
- Explain that the match is based on the job records in jobs.md and is only a screening aid.
- Do not claim that a job is currently open unless that status is explicitly present in jobs.md or verified by the web-search tool.

TOOL USAGE
- Do not use tavily_vbit_search just because the user asks a general question. Use it when local VBIT knowledge is insufficient.
- For questions about what you can do or simple greetings, answer briefly without tools.
- For job matching, call match_jobs with the resume text supplied by the user.

Format answers in clean Markdown: short sentences, bullets or tables for comparisons, **bold** for key figures. Use at most "###" headings. Do not use horizontal rules.
Be concise and friendly. Use British English.

Local knowledge files:
{catalog}
"""


def _build_agent():
    model = ChatGoogleGenerativeAI(
        model=config.MODEL,
        google_api_key=config.GEMINI_API_KEY,
        max_output_tokens=1800,
    )
    return create_agent(
        model,
        tools=build_tools(),
        system_prompt=SYSTEM_PROMPT.format(name=config.AGENT_NAME, catalog=catalog_text()),
    )


def run_agent(history: list[dict]) -> dict:
    """history: [{'role': 'user'|'assistant', 'content': str}, ...] ending with a user turn.
    Returns {'answer', 'sources': [local files with hits], 'web_sources': [{'title','url'}]}."""
    messages = [
        (AIMessage if m["role"] == "assistant" else HumanMessage)(content=m["content"])
        for m in history[-config.MAX_HISTORY_MESSAGES:]
    ]
    try:
        result = _build_agent().invoke(
            {"messages": messages},
            {"recursion_limit": 2 * config.MAX_TOOL_ROUNDS + 1},
        )
    except GraphRecursionError:
        return {
            "answer": "Sorry, I could not complete the search. Please try rephrasing your question.",
            "sources": [],
            "web_sources": [],
        }

    new = result["messages"][len(messages):]
    sources: list[str] = []
    web_sources: dict[str, str] = {}
    for m in new:
        if not isinstance(m, ToolMessage):
            continue
        try:
            data = json.loads(m.text)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        if data.get("found") and data.get("file") not in sources:
            sources.append(data["file"])
        for item in data.get("results", []):
            if isinstance(item, dict) and item.get("url"):
                web_sources.setdefault(item["url"], item.get("title", ""))

    answer = next((m.text for m in reversed(new) if isinstance(m, AIMessage) and m.text), "").strip()
    return {
        "answer": answer,
        "sources": sources,
        "web_sources": [{"title": t or u, "url": u} for u, t in web_sources.items()],
    }

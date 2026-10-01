"""LangChain agent: question -> pick file(s) from knowledge.yaml -> knowledge_search -> answer."""
import json

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.errors import GraphRecursionError

from . import config
from .knowledge import catalog_text
from .tools import build_tool

SYSTEM_PROMPT = """You are {name}, the information assistant for VBIT college.

You have no built-in knowledge of VBIT. Everything you say about VBIT must come from the
knowledge_search tool. The knowledge base contains these files:

{catalog}

Workflow:
1. Understand the question and decide, from the file descriptions above, which file(s) are relevant.
2. Call knowledge_search(file_name, query) for each relevant file. If a question spans several
   topics (e.g. courses and fees), search every relevant file. If a search finds nothing, you may
   retry once with different wording or check another plausibly relevant file.
3. Answer using only the retrieved text. Never guess or fill gaps from general knowledge.
4. If the information is not in the retrieved text, say clearly that it is not present in the
   knowledge base. Say what you did find, if anything.
5. End every answer that uses retrieved information with a line: "Source: <file1>, <file2>"
   listing only the files you actually used.

Format answers in clean Markdown: short sentences, bullet lists or a table for comparisons,
**bold** for key figures. Use at most "###" headings, and only when an answer has several sections.
Do not use horizontal rules.

For greetings or questions about what you can do, reply briefly without searching.
Be concise and friendly. Use British English."""


def _build_agent():
    # Rebuilt per request so changes to knowledge.yaml apply without a restart.
    model = ChatGoogleGenerativeAI(
        model=config.MODEL, google_api_key=config.GEMINI_API_KEY, max_output_tokens=1500
    )
    return create_agent(
        model,
        tools=[build_tool()],
        system_prompt=SYSTEM_PROMPT.format(name=config.AGENT_NAME, catalog=catalog_text()),
    )


def _sources(messages) -> list[str]:
    """Files whose knowledge_search call returned hits, in call order."""
    found: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            try:
                data = json.loads(m.text)
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("found") and data["file"] not in found:
                found.append(data["file"])
    return found


def run_agent(history: list[dict]) -> dict:
    """history: [{'role': 'user'|'assistant', 'content': str}, ...] ending with a user turn.
    Returns {'answer': str, 'sources': [names of files that produced hits]}."""
    messages = [
        (HumanMessage if m["role"] == "user" else AIMessage)(content=m["content"])
        for m in history[-config.MAX_HISTORY_MESSAGES:]
    ]
    try:
        result = _build_agent().invoke(
            {"messages": messages}, {"recursion_limit": 2 * config.MAX_TOOL_ROUNDS + 1}
        )
    except GraphRecursionError:
        return {
            "answer": "Sorry, I could not complete the search. Please try rephrasing your question.",
            "sources": [],
        }
    out = result["messages"]
    answer = next((m.text for m in reversed(out) if isinstance(m, AIMessage) and m.text), "").strip()
    return {"answer": answer, "sources": _sources(out[len(messages):])}

"""Tool-using agent loop (Gemini): question -> pick file(s) from knowledge.yaml -> search -> answer."""
import json

from google import genai
from google.genai import types

from . import config
from .knowledge import catalog_text
from .tools import run_tool, tool_declaration

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


def run_agent(history: list[dict]) -> dict:
    """history: [{'role': 'user'|'assistant', 'content': str}, ...] ending with a user turn.
    Returns {'answer': str, 'sources': [names of files that produced hits]}."""
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in history[-config.MAX_HISTORY_MESSAGES:]
    ]
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT.format(name=config.AGENT_NAME, catalog=catalog_text()),
        tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**tool_declaration())])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        max_output_tokens=1500,
    )
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    sources: list[str] = []

    for _ in range(config.MAX_TOOL_ROUNDS):
        resp = client.models.generate_content(model=config.MODEL, contents=contents, config=cfg)
        calls = resp.function_calls or []
        if not calls:
            return {"answer": (resp.text or "").strip(), "sources": sources}

        contents.append(resp.candidates[0].content)
        parts = []
        for call in calls:
            output = json.loads(run_tool(call.name, dict(call.args or {})))
            if output.get("found") and output["file"] not in sources:
                sources.append(output["file"])
            parts.append(types.Part.from_function_response(name=call.name, response=output))
        contents.append(types.Content(role="user", parts=parts))

    return {
        "answer": "Sorry, I could not complete the search. Please try rephrasing your question.",
        "sources": sources,
    }

"""The agent's single tool: knowledge_search(file_name, query)."""
import json

from .knowledge import KnowledgeError, registered_files, search_file


def tool_declaration() -> dict:
    """Built from knowledge.yaml so the allowed files always match the registry."""
    return {
        "name": "knowledge_search",
        "description": (
            "Search one VBIT knowledge file for information relevant to a query. "
            "Call once per file; call several times for questions spanning several files."
        ),
        "parameters_json_schema": {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "enum": list(registered_files()),
                    "description": "Registered knowledge file to search.",
                },
                "query": {"type": "string", "description": "Keywords or question to look for in that file."},
            },
            "required": ["file_name", "query"],
        },
    }


def knowledge_search(file_name: str, query: str) -> dict:
    try:
        return search_file(file_name, query)
    except KnowledgeError as e:
        return {"file": file_name, "found": False, "error": str(e)}


def run_tool(name: str, args: dict) -> str:
    if name != "knowledge_search":
        return json.dumps({"error": f"Unknown tool '{name}'"})
    return json.dumps(knowledge_search(args.get("file_name", ""), args.get("query", "")))

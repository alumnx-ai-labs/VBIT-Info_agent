"""The agent's single tool: knowledge_search(file_name, query), exposed as a LangChain tool."""
import json
from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from .knowledge import KnowledgeError, registered_files, search_file


def knowledge_search(file_name: str, query: str) -> dict:
    try:
        return search_file(file_name, query)
    except KnowledgeError as e:
        return {"file": file_name, "found": False, "error": str(e)}


def _args_schema() -> type[BaseModel]:
    """Built from knowledge.yaml so the allowed file names always match the registry."""
    files = tuple(registered_files())
    return create_model(
        "KnowledgeSearchInput",
        file_name=(Literal[files], Field(description="Registered knowledge file to search.")),
        query=(str, Field(description="Keywords or question to look for in that file.")),
    )


def build_tool() -> StructuredTool:
    return StructuredTool.from_function(
        func=lambda file_name, query: json.dumps(knowledge_search(file_name, query)),
        name="knowledge_search",
        description=(
            "Search one VBIT knowledge file for information relevant to a query. "
            "Call once per file; call several times for questions spanning several files."
        ),
        args_schema=_args_schema(),
    )

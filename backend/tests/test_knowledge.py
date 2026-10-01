import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools import knowledge_search, run_tool, tool_declaration  # noqa: E402


def test_search_finds_relevant_chunk():
    r = knowledge_search("fees.txt", "tuition fee for ECE")
    assert r["found"] and "ECE" in r["results"][0]


def test_search_no_match():
    r = knowledge_search("fees.txt", "swimming pool olympic")
    assert r["found"] is False


def test_unregistered_file_rejected():
    for name in ["secret.txt", "../knowledge.yaml", "..\\.env", "/etc/passwd"]:
        r = knowledge_search(name, "anything")
        assert r["found"] is False and "error" in r


def test_schema_enum_matches_registry():
    assert "courses.txt" in tool_declaration()["parameters_json_schema"]["properties"]["file_name"]["enum"]


def test_run_tool_returns_json():
    assert json.loads(run_tool("knowledge_search", {"file_name": "courses.txt", "query": "branches"}))["found"]

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools import build_tools, knowledge_search, match_jobs  # noqa: E402


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


def test_tools_registered_and_enum_matches_registry():
    tools = {t.name: t for t in build_tools()}
    assert set(tools) == {"knowledge_search", "tavily_vbit_search", "match_jobs"}
    assert "courses.txt" in tools["knowledge_search"].args_schema.model_json_schema()["properties"]["file_name"]["enum"]


def test_match_jobs_ranks_relevant_job_first():
    r = match_jobs("B.Tech CS. Java, Spring Boot, MySQL, REST APIs.")
    assert r["matches"][0]["title"] == "Software Engineer Trainee"
    assert "java" in r["matches"][0]["matched_skills"]


def test_match_jobs_empty_resume():
    assert "error" in match_jobs("  ")

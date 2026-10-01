"""Knowledge registry (knowledge.yaml) and search over the registered data/*.txt files."""
import math
import re
from collections import Counter
from dataclasses import dataclass

import yaml

from .config import DATA_DIR, KNOWLEDGE_YAML

STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it its of on or "
    "the to what which who will with about me my tell vbit college there their "
    "any please give".split()
)
TOP_K = 5


@dataclass(frozen=True)
class KnowledgeEntry:
    key: str
    file: str
    description: str


class KnowledgeError(ValueError):
    """Raised for requests that must be rejected (unregistered file, etc.)."""


def load_registry() -> dict[str, KnowledgeEntry]:
    """Read knowledge.yaml fresh each call so new files need no restart."""
    with open(KNOWLEDGE_YAML, encoding="utf-8") as f:
        raw = (yaml.safe_load(f) or {}).get("knowledge", {})
    return {
        key: KnowledgeEntry(key, spec["file"], spec.get("description", ""))
        for key, spec in raw.items()
    }


def registered_files() -> dict[str, KnowledgeEntry]:
    """Map file name -> entry."""
    return {e.file: e for e in load_registry().values()}


def catalog_text() -> str:
    """Catalog built from knowledge.yaml, shown to the model."""
    return "\n".join(f"- {e.file}: {e.description}" for e in load_registry().values())


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w.rstrip("s") if len(w) > 3 else w for w in words if w not in STOPWORDS]


def _chunks(text: str) -> list[str]:
    """Split on blank lines; prefix each chunk with its nearest '#' heading."""
    heading, out = "", []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        if lines[0].startswith("#"):
            heading = lines[0].lstrip("# ").strip()
            if len(lines) == 1:
                continue
        elif heading:
            block = f"[{heading}]\n{block}"
        out.append(block)
    return out


def search_file(file_name: str, query: str) -> dict:
    """Search one registered file. Returns {file, found, results | message}."""
    files = registered_files()
    if file_name not in files:
        raise KnowledgeError(
            f"'{file_name}' is not registered in knowledge.yaml. "
            f"Available files: {', '.join(files)}"
        )
    path = (DATA_DIR / file_name).resolve()
    if path.parent != DATA_DIR.resolve() or not path.is_file():
        raise KnowledgeError(f"'{file_name}' could not be read from the data folder.")

    chunks = _chunks(path.read_text(encoding="utf-8"))
    q_tokens = set(_tokens(query))
    if not chunks or not q_tokens:
        return {"file": file_name, "found": False, "message": "No relevant information found."}

    chunk_tokens = [Counter(_tokens(c)) for c in chunks]
    n = len(chunks)
    scored = []
    for chunk, counts in zip(chunks, chunk_tokens):
        score = 0.0
        for t in q_tokens:
            if counts[t]:
                df = sum(1 for c in chunk_tokens if c[t])
                score += (1 + math.log(counts[t])) * (math.log((n + 1) / df) + 1)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return {"file": file_name, "found": False, "message": "No relevant information found in this file."}
    return {"file": file_name, "found": True, "results": [c for _, c in scored[:TOP_K]]}

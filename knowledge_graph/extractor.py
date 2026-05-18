"""
Entity Extractor — Extract people, projects, topics, and technologies from text.

Uses pattern-based extraction (no heavy ML models needed):
- Capitalized names → Person entities
- Technology keywords → Technology entities
- Markdown headers → Topic entities
- Project patterns → Project entities
- Action items → Task entities

This is intentionally lightweight. Phase 4 can upgrade to spaCy NER.
"""

import re
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Known technology keywords (expandable)
TECH_KEYWORDS = {
    "python", "javascript", "typescript", "java", "rust", "go", "c++",
    "react", "next.js", "nextjs", "fastapi", "flask", "django", "express",
    "docker", "kubernetes", "git", "github", "neo4j", "postgresql", "sqlite",
    "mongodb", "redis", "chromadb", "langchain", "langgraph", "pytorch",
    "tensorflow", "hugging face", "transformers", "sentence-transformers",
    "mcp", "openai", "claude", "chatgpt", "gemini", "llm", "rag",
    "html", "css", "tailwind", "vscode", "linux", "windows", "aws",
    "gcp", "azure", "vercel", "uvicorn", "pydantic", "watchdog",
    "spacy", "nltk", "pandas", "numpy", "scikit-learn",
}

# Patterns for extracting capitalized multi-word names (likely people)
NAME_PATTERN = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')

# Markdown header pattern
HEADER_PATTERN = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)

# Action item / task pattern
TASK_PATTERN = re.compile(r'- \[[ x]\]\s+(.+)$', re.MULTILINE)

# Project-like patterns (capitalized words or words with specific suffixes)
PROJECT_PATTERN = re.compile(r'\b([A-Z][a-zA-Z]*(?:AI|MCP|App|Tool|Bot|API|DB|Net))\b')


def extract_entities(text: str, source_file: str = "") -> list[dict[str, Any]]:
    """
    Extract entities from text content.

    Returns a list of entity dicts, each with:
    - name: The entity text
    - type: person, technology, topic, project, task
    - source: Where it was found

    Args:
        text: The text content to analyze.
        source_file: Name of the source file for metadata.

    Returns:
        List of entity dictionaries.
    """
    entities = []
    seen = set()

    def _add(name: str, entity_type: str):
        key = (name.lower(), entity_type)
        if key not in seen and len(name) > 2:
            seen.add(key)
            entities.append({
                "name": name.strip(),
                "type": entity_type,
                "source": source_file,
            })

    # Extract topics from markdown headers
    for match in HEADER_PATTERN.finditer(text):
        header = match.group(1).strip()
        # Clean up markdown formatting
        header = re.sub(r'[*_`#]', '', header).strip()
        if header and len(header) > 3:
            _add(header, "topic")

    # Extract technologies
    text_lower = text.lower()
    for tech in TECH_KEYWORDS:
        if tech in text_lower:
            _add(tech.title() if len(tech) > 3 else tech.upper(), "technology")

    # Extract person names (capitalized multi-word names)
    # Uses structural heuristics to reduce false positives:
    #   - Must be 2-3 words (real names are rarely 4+ words)
    #   - Each word must be 2-15 chars (filters out acronyms and long words)
    #   - Excludes words commonly found in headings and prose
    _NON_NAME_WORDS = {
        "the", "this", "that", "these", "those", "some", "each", "every",
        "phase", "step", "chapter", "section", "part", "note", "action",
        "key", "daily", "meeting", "project", "tech", "stack", "learning",
        "goals", "ideas", "notes", "journal", "summary", "review", "plan",
        "deep", "build", "local", "full", "open", "next", "using", "based",
        "recent", "current", "new", "old", "first", "last", "best", "top",
        "may", "june", "july", "august", "january", "february", "march",
        "april", "september", "october", "november", "december",
        "monday", "tuesday", "wednesday", "thursday", "friday",
        "personal", "unified", "semantic", "model", "context", "protocol",
    }

    for match in NAME_PATTERN.finditer(text):
        name = match.group(1)
        words = name.split()

        # Structural filters
        if len(words) < 2 or len(words) > 3:
            continue
        if any(len(w) < 2 or len(w) > 15 for w in words):
            continue
        if any(w.lower() in _NON_NAME_WORDS for w in words):
            continue

        _add(name, "person")

    # Extract projects
    for match in PROJECT_PATTERN.finditer(text):
        project = match.group(1)
        if project not in {"The", "This", "For"}:
            _add(project, "project")

    # Extract tasks
    for match in TASK_PATTERN.finditer(text):
        task = match.group(1).strip()
        if len(task) > 5:
            _add(task[:100], "task")  # Truncate long tasks

    return entities


def extract_relationships(
    entities: list[dict[str, Any]],
    source_file: str = "",
) -> list[dict[str, Any]]:
    """
    Infer relationships between entities found in the same document.

    Relationship types:
    - MENTIONED_IN: entity appears in a source file
    - RELATED_TO: entities co-occur in the same document
    - USES: project uses technology
    - WORKED_ON: person worked on project/task

    Args:
        entities: List of extracted entity dicts.
        source_file: Name of the source document.

    Returns:
        List of relationship dicts with from_entity, to_entity, type.
    """
    relationships = []

    # All entities are MENTIONED_IN the source file
    if source_file:
        for entity in entities:
            relationships.append({
                "from_name": entity["name"],
                "from_type": entity["type"],
                "to_name": source_file,
                "to_type": "document",
                "rel_type": "MENTIONED_IN",
            })

    # Co-occurring entities are RELATED_TO each other
    # Group by type for smarter relationships
    by_type: dict[str, list] = {}
    for e in entities:
        by_type.setdefault(e["type"], []).append(e)

    # People → Projects = WORKED_ON
    for person in by_type.get("person", []):
        for project in by_type.get("project", []):
            relationships.append({
                "from_name": person["name"],
                "from_type": "person",
                "to_name": project["name"],
                "to_type": "project",
                "rel_type": "WORKED_ON",
            })

    # Projects → Technologies = USES
    for project in by_type.get("project", []):
        for tech in by_type.get("technology", []):
            relationships.append({
                "from_name": project["name"],
                "from_type": "project",
                "to_name": tech["name"],
                "to_type": "technology",
                "rel_type": "USES",
            })

    # Topics ↔ Topics in same file = RELATED_TO
    topics = by_type.get("topic", [])
    for i in range(len(topics)):
        for j in range(i + 1, len(topics)):
            relationships.append({
                "from_name": topics[i]["name"],
                "from_type": "topic",
                "to_name": topics[j]["name"],
                "to_type": "topic",
                "rel_type": "RELATED_TO",
            })

    return relationships


def extract_from_file(filepath: Path) -> dict[str, Any]:
    """
    Extract entities and relationships from a single file.

    Args:
        filepath: Path to the file.

    Returns:
        Dict with entities, relationships, and metadata.
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError) as e:
        return {"error": str(e), "file": str(filepath)}

    entities = extract_entities(content, filepath.name)
    relationships = extract_relationships(entities, filepath.name)

    return {
        "file": filepath.name,
        "entities": entities,
        "relationships": relationships,
        "entity_count": len(entities),
        "relationship_count": len(relationships),
    }

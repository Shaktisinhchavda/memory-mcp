"""
Knowledge Graph MCP Server — Query your personal knowledge graph.

Exposes tools for searching entities, finding connections,
and exploring relationships in your Neo4j knowledge graph.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from knowledge_graph.graph_store import GraphStore
from knowledge_graph.extractor import extract_from_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("graph-mcp")

# Lazy-loaded graph store
_store: GraphStore | None = None


def _get_store() -> GraphStore:
    global _store
    if _store is None:
        _store = GraphStore()
    return _store


@mcp.tool()
def graph_search(entity: str, depth: int = 2) -> str:
    """
    Search the knowledge graph for an entity and its connected context.

    Finds people, projects, technologies, topics, and their relationships.
    Returns the entity and everything connected to it within the given depth.

    Args:
        entity: Name of the entity to search for (e.g., "FastAPI", "MCP", "portfolio").
        depth: How many relationship hops to traverse (1-4, default 2).

    Returns:
        JSON with the entity, its connections, and relationship types.
    """
    store = _get_store()
    if not store.is_connected():
        return json.dumps({"error": "Neo4j is not running. Start it with: docker compose up -d"})

    results = store.graph_search(entity, max_depth=depth)
    return json.dumps(results, indent=2, default=str)


@mcp.tool()
def find_connection(from_entity: str, to_entity: str) -> str:
    """
    Find how two entities are connected in the knowledge graph.

    Discovers the shortest path between any two entities, showing
    all intermediate nodes and relationships.

    Args:
        from_entity: Starting entity name.
        to_entity: Target entity name.

    Returns:
        JSON with paths connecting the two entities.
    """
    store = _get_store()
    if not store.is_connected():
        return json.dumps({"error": "Neo4j is not running. Start it with: docker compose up -d"})

    paths = store.find_paths(from_entity, to_entity)
    return json.dumps({
        "from": from_entity,
        "to": to_entity,
        "paths_found": len(paths),
        "paths": paths,
    }, indent=2, default=str)


@mcp.tool()
def graph_stats() -> str:
    """
    Get statistics about the knowledge graph.

    Returns total nodes, relationships, and counts by type.
    """
    store = _get_store()
    if not store.is_connected():
        return json.dumps({"error": "Neo4j is not running. Start it with: docker compose up -d"})

    stats = store.get_stats()
    return json.dumps(stats, indent=2, default=str)


@mcp.tool()
def ingest_file(filepath: str) -> str:
    """
    Extract entities from a file and add them to the knowledge graph.

    Reads the file, extracts people, projects, technologies, and topics,
    then creates nodes and relationships in Neo4j.

    Args:
        filepath: Path to the file to process.

    Returns:
        JSON with extraction and ingestion results.
    """
    store = _get_store()
    if not store.is_connected():
        return json.dumps({"error": "Neo4j is not running. Start it with: docker compose up -d"})

    path = Path(filepath)
    if not path.exists():
        return json.dumps({"error": f"File not found: {filepath}"})

    extraction = extract_from_file(path)
    if "error" in extraction:
        return json.dumps(extraction)

    ingestion = store.ingest_extraction(extraction)

    return json.dumps({
        "file": extraction["file"],
        "entities_found": extraction["entity_count"],
        "relationships_found": extraction["relationship_count"],
        "entities": extraction["entities"],
        **ingestion,
    }, indent=2, default=str)


def main():
    logger.info("Starting graph-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

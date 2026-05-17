"""Tests for the knowledge graph."""

import sys
sys.path.insert(0, ".")

from knowledge_graph.graph_store import GraphStore
from knowledge_graph.extractor import extract_entities, extract_relationships


def test_extractor():
    print("=== Testing Entity Extractor ===")
    text = """
# AI Project Meeting
**Attendees:** Shakti, Dev Team

We discussed using FastAPI and ChromaDB for the MCP server.
The VizDataAI project needs more work. LangGraph will be used
for the agent framework.

- [ ] Build Phase 1 core server
- [x] Set up ChromaDB
"""
    entities = extract_entities(text, "test.md")
    print(f"  Entities found: {len(entities)}")
    for e in entities:
        print(f"    [{e['type']}] {e['name']}")

    rels = extract_relationships(entities, "test.md")
    print(f"  Relationships: {len(rels)}")
    print("  [PASS] Extractor")


def test_graph_store():
    print("\n=== Testing Graph Store ===")
    store = GraphStore()

    if not store.is_connected():
        print("  [SKIP] Neo4j not running. Start with: docker compose up -d")
        return

    print("  Connected to Neo4j!")

    # Test search
    result = store.graph_search("FastAPI")
    count = result.get("results_count", 0)
    print(f"  Search 'FastAPI': {count} results")

    result2 = store.graph_search("MCP")
    count2 = result2.get("results_count", 0)
    print(f"  Search 'MCP': {count2} results")

    # Test stats
    stats = store.get_stats()
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total relationships: {stats['total_relationships']}")

    store.close()
    print("  [PASS] Graph Store")


if __name__ == "__main__":
    test_extractor()
    test_graph_store()
    print("\nAll Phase 3 tests complete!")

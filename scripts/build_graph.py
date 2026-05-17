"""
Build Knowledge Graph — Ingest all notes into Neo4j.

Run this after starting Neo4j:
    docker compose up -d
    uv run python scripts/build_graph.py
"""

import logging
import sys

sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from pathlib import Path
from knowledge_graph.graph_store import GraphStore
from knowledge_graph.extractor import extract_from_file
from config.settings import settings


def main():
    print("=" * 50)
    print("  Personal MCP - Knowledge Graph Builder")
    print("=" * 50)

    store = GraphStore()
    if not store.is_connected():
        print("\n[ERROR] Neo4j is not running!")
        print("Start it with: docker compose up -d")
        print("Then wait ~10 seconds and try again.")
        return

    print("\nConnected to Neo4j!")

    # Scan notes directory
    notes_dir = settings.notes_dir.resolve()
    extensions = {".md", ".txt", ".rst", ".org"}
    files = [f for f in notes_dir.rglob("*") if f.is_file() and f.suffix.lower() in extensions]

    print(f"Found {len(files)} files to process\n")

    total_entities = 0
    total_rels = 0

    for filepath in sorted(files):
        print(f"Processing: {filepath.name}")
        extraction = extract_from_file(filepath)

        if "error" in extraction:
            print(f"  [SKIP] {extraction['error']}")
            continue

        print(f"  Entities: {extraction['entity_count']}, Relationships: {extraction['relationship_count']}")

        result = store.ingest_extraction(extraction)
        total_entities += result.get("nodes_created", 0)
        total_rels += result.get("relationships_created", 0)

    print(f"\n{'=' * 50}")
    print(f"  Graph built!")
    print(f"  Nodes created:         {total_entities}")
    print(f"  Relationships created: {total_rels}")
    print(f"{'=' * 50}")

    # Show stats
    stats = store.get_stats()
    print(f"\nGraph totals:")
    print(f"  Total nodes:         {stats['total_nodes']}")
    print(f"  Total relationships: {stats['total_relationships']}")
    print(f"\n  By type:")
    for label, count in stats.get("nodes_by_type", {}).items():
        print(f"    {label}: {count}")

    store.close()


if __name__ == "__main__":
    main()

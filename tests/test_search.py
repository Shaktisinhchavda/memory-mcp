"""Tests for semantic search."""

import sys
sys.path.insert(0, ".")

from core_mcp.vector_store.indexer import Indexer
from core_mcp.tools.search import semantic_search, get_index_stats


def test_index_and_search():
    """Index notes then search them semantically."""
    print("Step 1: Indexing notes...")
    indexer = Indexer()
    stats = indexer.index_all_notes()
    print(f"  Indexed {stats['indexed_files']} files, {stats['total_chunks']} chunks")
    assert stats["indexed_files"] > 0, "No files were indexed"

    print("\nStep 2: Checking index stats...")
    idx_stats = get_index_stats()
    print(f"  Total entries: {idx_stats['total_entries']}")
    assert idx_stats["total_entries"] > 0

    print("\nStep 3: Semantic search for 'AI projects'...")
    results = semantic_search("AI projects", top_k=3)
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    - {r['filename']} (relevance: {r['relevance']})")
        print(f"      {r['content'][:80]}...")
    assert len(results) > 0, "No search results returned"

    print("\nStep 4: Semantic search for 'meeting decisions'...")
    results = semantic_search("meeting decisions", top_k=3)
    print(f"  Found {len(results)} results:")
    for r in results:
        print(f"    - {r['filename']} (relevance: {r['relevance']})")

    print("\n✅ test_index_and_search passed")


if __name__ == "__main__":
    test_index_and_search()
    print("\n🎉 All search tests passed!")

"""
Semantic Search Tool — Query your personal knowledge base by meaning.

This MCP tool wraps the ChromaDB vector store to let AI agents:
- Search notes and files by semantic similarity (not just keywords)
- Get the most relevant chunks with metadata and relevance scores
- Understand your personal context through natural language queries

The search is entirely local — embeddings are computed on your machine
using the all-MiniLM-L6-v2 model from sentence-transformers.
"""

import logging
from typing import Any

from core_mcp.vector_store.store import VectorStore

logger = logging.getLogger(__name__)

# Module-level store instance (lazy loaded)
_store: VectorStore | None = None


def _get_store() -> VectorStore:
    """Get or create the singleton VectorStore instance."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def semantic_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Search your personal notes and files by semantic meaning.

    This finds the most relevant content based on meaning, not just
    keyword matching. For example, searching "project deadlines" will
    also find notes mentioning "due dates" or "milestone timelines".

    Args:
        query: Natural language search query describing what you're looking for.
        top_k: Number of results to return (default: 5, max: 20).

    Returns:
        List of search results, each containing:
        - content: The matching text chunk
        - filename: Source file name
        - relevance: Similarity score (0-1, higher is better)
        - metadata: Additional info (date indexed, chunk position, etc.)
    """
    top_k = min(max(1, top_k), 20)  # Clamp between 1 and 20

    store = _get_store()

    if store.count == 0:
        return [{
            "message": "No documents indexed yet. Run 'python scripts/index_notes.py' first.",
            "hint": "Add some .md or .txt files to your data/notes/ directory, then index them.",
        }]

    raw_results = store.search(query, top_k=top_k)

    # Format results for clean MCP output
    results = []
    for r in raw_results:
        # Convert ChromaDB distance to a 0-1 relevance score
        # ChromaDB uses L2 distance by default; lower = more similar
        distance = r.get("distance", 0)
        relevance = max(0.0, 1.0 - (distance / 2.0))  # Approximate normalization

        results.append({
            "content": r["content"],
            "filename": r["metadata"].get("filename", "unknown"),
            "relevance": round(relevance, 4),
            "metadata": {
                k: v for k, v in r["metadata"].items()
                if k not in ("filename",)  # Don't duplicate
            },
        })

    return results


def get_index_stats() -> dict[str, Any]:
    """
    Get statistics about the current vector store index.

    Returns:
        Dict with total documents/chunks count and collection info.
    """
    store = _get_store()
    return {
        "total_entries": store.count,
        "collection_name": store.COLLECTION_NAME,
        "embedding_model": "all-MiniLM-L6-v2",
        "storage_path": str(store._client._path) if hasattr(store._client, '_path') else "unknown",
    }

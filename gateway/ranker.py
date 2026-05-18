"""
Context Ranker — Combines and ranks results from multiple sources.

Scoring formula:
  final_score = (semantic_weight * vector_score)
              + (graph_weight * graph_score)  
              + (recency_weight * recency_score)

This ensures the most relevant, connected, and recent information
surfaces to the top of the PersonalContext response.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Weights for combining scores (must sum to 1.0)
SEMANTIC_WEIGHT = 0.5
GRAPH_WEIGHT = 0.3
RECENCY_WEIGHT = 0.2


def compute_recency_score(timestamp_str: str, max_days: int = 30) -> float:
    """
    Score how recent something is (1.0 = now, 0.0 = max_days ago or older).

    Args:
        timestamp_str: ISO format timestamp.
        max_days: Timeframe for scoring.

    Returns:
        Float between 0.0 and 1.0.
    """
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        age = (now - ts).total_seconds() / 86400  # days
        return max(0.0, 1.0 - (age / max_days))
    except (ValueError, TypeError):
        return 0.3  # Default for unparseable timestamps


def rank_semantic_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add normalized scores to semantic search results (0-1 scale)."""
    for r in results:
        base_relevance = r.get("relevance", 0.5)
        recency = compute_recency_score(
            r.get("metadata", {}).get("indexed_at", "")
        )
        # Weighted blend, normalized to 0-1
        r["final_score"] = (0.7 * base_relevance) + (0.3 * recency)
    return sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)


def rank_graph_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score graph results by connection density (0-1 scale)."""
    for r in results:
        connections = len(r.get("connections", []))
        # More connections = higher relevance (normalized to 0-1)
        r["final_score"] = min(1.0, connections / 10.0)
    return sorted(results, key=lambda x: x.get("final_score", 0), reverse=True)


def rank_activity(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score activity events by recency (0-1 scale)."""
    for e in events:
        e["final_score"] = compute_recency_score(e.get("timestamp", ""))
    return sorted(events, key=lambda x: x.get("final_score", 0), reverse=True)


def merge_and_rank(
    semantic: list[dict] | None = None,
    graph: list[dict] | None = None,
    activity: list[dict] | None = None,
) -> list[dict[str, Any]]:
    """
    Merge all sources and produce a unified ranked list.

    Each item gets a final_score and source_type tag for the gateway.
    """
    all_results = []

    for r in rank_semantic_results(semantic or []):
        all_results.append({**r, "source_type": "semantic_search"})

    for r in rank_graph_results(graph or []):
        all_results.append({**r, "source_type": "knowledge_graph"})

    for r in rank_activity(activity or []):
        all_results.append({**r, "source_type": "recent_activity"})

    return sorted(all_results, key=lambda x: x.get("final_score", 0), reverse=True)

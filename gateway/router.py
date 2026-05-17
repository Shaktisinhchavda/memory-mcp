"""
Smart Router — Decides which tools to call based on the query.

Uses keyword analysis to route queries to the right MCP tools.
This is the rule-based fallback that always works without an LLM.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Keyword → tool mapping
ROUTE_RULES = [
    {
        "keywords": ["note", "notes", "journal", "daily", "meeting", "read note", "list note"],
        "tools": ["read_notes"],
        "category": "notes",
    },
    {
        "keywords": ["search", "find", "about", "related", "semantic", "what do i know", "meaning"],
        "tools": ["semantic_search"],
        "category": "semantic",
    },
    {
        "keywords": ["graph", "connection", "connected", "entity", "relationship", "linked", "knowledge graph"],
        "tools": ["graph_search"],
        "category": "graph",
    },
    {
        "keywords": ["file", "pdf", "document", "read file", "docx", "local file"],
        "tools": ["read_local_file", "list_local_files"],
        "category": "files",
    },
    {
        "keywords": ["browser", "history", "visited", "website", "browsing", "chrome"],
        "tools": ["recent_browsing_history", "search_browsing_history"],
        "category": "browser",
    },
    {
        "keywords": ["git", "commit", "code", "repo", "branch", "vscode", "recently opened"],
        "tools": ["recent_commits", "git_status", "vscode_recent"],
        "category": "code",
    },
    {
        "keywords": ["calendar", "schedule", "event", "meeting today", "upcoming"],
        "tools": ["upcoming_events", "todays_schedule"],
        "category": "calendar",
    },
    {
        "keywords": ["conversation", "chat", "claude", "chatgpt", "exported"],
        "tools": ["list_conversation_exports", "read_conversations"],
        "category": "conversations",
    },
    {
        "keywords": ["activity", "recent", "changed", "modified", "what happened"],
        "tools": ["get_recent_activity"],
        "category": "activity",
    },
    {
        "keywords": ["stat", "stats", "status", "index", "how many"],
        "tools": ["index_stats", "graph_stats"],
        "category": "stats",
    },
]

# Broad queries that should hit multiple sources
BROAD_KEYWORDS = [
    "everything", "all", "full picture", "summarize", "overview",
    "what do you know", "who am i", "about me", "my context",
]


def route_query(query: str) -> list[dict[str, Any]]:
    """
    Analyze a query and determine which tools to call.

    Args:
        query: Natural language query.

    Returns:
        List of route dicts with tools and categories to invoke.
    """
    query_lower = query.lower()
    matched_routes = []

    # Check if it's a broad query → hit everything
    is_broad = any(kw in query_lower for kw in BROAD_KEYWORDS)
    if is_broad:
        return [
            {"tools": ["semantic_search"], "category": "semantic", "priority": 1},
            {"tools": ["graph_search"], "category": "graph", "priority": 2},
            {"tools": ["get_recent_activity"], "category": "activity", "priority": 3},
            {"tools": ["read_notes"], "category": "notes", "priority": 4},
        ]

    # Match against keyword rules
    for rule in ROUTE_RULES:
        for keyword in rule["keywords"]:
            if keyword in query_lower:
                matched_routes.append({
                    "tools": rule["tools"],
                    "category": rule["category"],
                    "priority": len(matched_routes) + 1,
                })
                break  # Don't double-match same rule

    # Default: semantic search + graph search
    if not matched_routes:
        matched_routes = [
            {"tools": ["semantic_search"], "category": "semantic", "priority": 1},
            {"tools": ["graph_search"], "category": "graph", "priority": 2},
        ]

    return matched_routes

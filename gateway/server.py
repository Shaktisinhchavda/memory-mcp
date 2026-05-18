"""
Unified Gateway — Single FastAPI server for the entire MCP ecosystem.

Endpoints:
  POST /query     — Natural language query → PersonalContext response
  GET  /health    — Health check for all services
  GET  /sources   — List all available data sources and tools

Run:
  uv run uvicorn gateway.server:app --host 0.0.0.0 --port 8000
"""

import json
import logging
import sys
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from gateway.agent import query_context
from gateway.router import route_query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──

app = FastAPI(
    title="Memory MCP Gateway",
    description="Unified gateway to the Personal MCP Ecosystem. "
                "Query all your personal data sources through one API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response Models ──

class QueryRequest(BaseModel):
    query: str = Field(description="Natural language query")
    max_results: int = Field(default=10, description="Maximum results per source")


class HealthStatus(BaseModel):
    status: str
    services: dict[str, bool]


# ── Endpoints ──

@app.get("/", tags=["root"])
async def root():
    """Gateway root — shows available endpoints."""
    return {
        "name": "Memory MCP Gateway",
        "version": "1.0.0",
        "description": "Unified access to your Personal MCP Ecosystem",
        "endpoints": {
            "POST /query": "Natural language query → PersonalContext",
            "GET /health": "Service health check",
            "GET /sources": "List all data sources and tools",
            "GET /route?q=...": "Preview which tools a query would trigger",
        },
    }


@app.post("/query", tags=["query"])
async def query(request: QueryRequest):
    """
    Query your personal data using natural language.

    The gateway agent will:
    1. Analyze your query to determine relevant data sources
    2. Call the appropriate tools (vector search, graph, files, etc.)
    3. Rank and aggregate results
    4. Return a unified PersonalContext response
    """
    try:
        context = query_context(request.query)
        return context
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/route", tags=["debug"])
async def preview_route(q: str):
    """Preview which tools would be called for a query (without executing)."""
    routes = route_query(q)
    return {
        "query": q,
        "routes": routes,
        "tools_to_call": [tool for r in routes for tool in r["tools"]],
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Check the health of all backend services."""
    services = {}

    # Check ChromaDB / Vector Store
    try:
        from core_mcp.tools.search import get_index_stats
        stats = get_index_stats()
        services["vector_store"] = stats.get("total_entries", 0) > 0
    except Exception:
        services["vector_store"] = False

    # Check Neo4j
    try:
        from knowledge_graph.graph_store import GraphStore
        store = GraphStore()
        services["neo4j"] = store.is_connected()
        store.close()
    except Exception:
        services["neo4j"] = False

    # Check Event Logger
    try:
        from core_mcp.event_logger.database import get_recent_events
        get_recent_events(1)
        services["event_logger"] = True
    except Exception:
        services["event_logger"] = False

    # Check Browser History (Chrome/Edge/Firefox)
    try:
        from connectors.browser_mcp.tools import get_available_browsers
        browsers = get_available_browsers()
        services["browser_history"] = browsers.get("count", 0) > 0
    except Exception:
        services["browser_history"] = False

    all_healthy = all(services.values())

    return HealthStatus(
        status="healthy" if all_healthy else "degraded",
        services=services,
    )


@app.get("/sources", tags=["info"])
async def list_sources():
    """List all available data sources and their tools."""
    return {
        "sources": [
            {
                "name": "Core MCP",
                "server": "memory-mcp",
                "tools": ["read_notes", "semantic_search", "get_recent_activity", "index_stats", "save_note", "append_note"],
                "description": "Notes, semantic search, and file event tracking",
            },
            {
                "name": "Files",
                "server": "files-mcp",
                "tools": ["read_local_file", "list_local_files", "search_local_files"],
                "description": "Read PDFs, DOCX, Markdown, and text files",
            },
            {
                "name": "Browser",
                "server": "browser-mcp",
                "tools": ["recent_browsing_history", "most_visited_sites", "search_browsing_history", "browsing_stats", "detected_browsers"],
                "description": "Chrome, Edge, and Firefox browsing history (auto-detected)",
            },
            {
                "name": "Code",
                "server": "code-mcp",
                "tools": ["recent_commits", "git_status", "repo_statistics", "vscode_recent"],
                "description": "Git commits and VSCode activity",
            },
            {
                "name": "Conversations",
                "server": "conversations-mcp",
                "tools": ["list_conversation_exports", "read_conversations", "search_in_conversations"],
                "description": "Exported Claude and ChatGPT conversations",
            },
            {
                "name": "Knowledge Graph",
                "server": "graph-mcp",
                "tools": ["graph_search", "find_connection", "graph_stats", "ingest_file"],
                "description": "Neo4j knowledge graph with entity relationships",
            },
        ],
        "total_tools": 25,
    }

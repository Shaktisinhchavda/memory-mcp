"""
Personal MCP Server — The core of your Personal MCP Ecosystem.

This server exposes your personal data as MCP tools that any AI agent
(Claude Desktop, Claude Code, etc.) can use via the stdio transport.

Available tools:
  - read_notes: List and read notes from your local notes directory
  - semantic_search: Search your knowledge base by meaning using ChromaDB
  - get_recent_activity: See recent file changes from the event logger

Run directly:
    python -m core_mcp.server

Or via Claude Desktop config (see README.md).
"""

import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from config.settings import settings
from core_mcp.tools.notes import list_notes, read_note, save_note as _save_note, append_note as _append_note
from core_mcp.tools.search import semantic_search as _semantic_search, get_index_stats
from core_mcp.event_logger.database import get_recent_events, init_database

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(settings.mcp_server_name)


# ──────────────────────────────────────────────────────────
# Tool 1: read_notes — Access your personal notes
# ──────────────────────────────────────────────────────────

@mcp.tool()
def read_notes(filename: str | None = None) -> str:
    """
    Read personal notes from the local filesystem.

    If no filename is provided, lists all available notes with metadata.
    If a filename is provided, returns the full content of that note.

    Args:
        filename: Optional. Name of the note file to read (e.g. "ideas.md").
                  If omitted, returns a list of all available notes.

    Returns:
        JSON string with note content or list of available notes.
    """
    if filename:
        result = read_note(filename)
    else:
        notes = list_notes()
        result = {
            "total_notes": len(notes),
            "notes": notes,
            "hint": "Pass a filename to read_notes to see its content.",
        }
    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Tool 2: semantic_search — Query by meaning
# ──────────────────────────────────────────────────────────

@mcp.tool()
def semantic_search(query: str, top_k: int = 5) -> str:
    """
    Search personal notes and files by semantic meaning.

    Uses vector embeddings to find content related to your query,
    even if the exact words don't match. For example, searching
    "project deadlines" will find notes about "due dates" or "milestones".

    Args:
        query: Natural language description of what you're looking for.
        top_k: Number of results to return (1-20, default 5).

    Returns:
        JSON string with ranked search results and relevance scores.
    """
    results = _semantic_search(query, top_k=top_k)
    return json.dumps({
        "query": query,
        "results_count": len(results),
        "results": results,
    }, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Tool 3: get_recent_activity — File change timeline
# ──────────────────────────────────────────────────────────

@mcp.tool()
def get_recent_activity(limit: int = 20) -> str:
    """
    Get recent file system activity from watched directories.

    Shows the latest file changes (created, modified, deleted, moved)
    in your notes and files directories. Useful for understanding
    what you've been working on recently.

    Args:
        limit: Number of recent events to return (default 20, max 100).

    Returns:
        JSON string with recent file events and timestamps.
    """
    limit = min(max(1, limit), 100)
    events = get_recent_events(limit)
    return json.dumps({
        "total_events": len(events),
        "events": events,
    }, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Tool 4: index_stats — Vector store status
# ──────────────────────────────────────────────────────────

@mcp.tool()
def index_stats() -> str:
    """
    Get statistics about the vector search index.

    Shows how many documents/chunks are indexed, which embedding
    model is being used, and where the data is stored.

    Returns:
        JSON string with index statistics.
    """
    stats = get_index_stats()
    return json.dumps(stats, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Tool 5: save_note — Write memories back
# ──────────────────────────────────────────────────────────

@mcp.tool()
def save_note(filename: str, content: str) -> str:
    """
    Save a new note or overwrite an existing one.

    Use this to write memories, meeting summaries, conversation notes,
    or any context back into the personal knowledge base.

    Args:
        filename: Name for the note file (e.g., "meeting-summary.md").
        content: Full content to write.

    Returns:
        JSON string with saved file metadata.
    """
    result = _save_note(filename, content)
    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Tool 6: append_note — Add to existing notes
# ──────────────────────────────────────────────────────────

@mcp.tool()
def append_note(filename: str, content: str) -> str:
    """
    Append content to an existing note.

    Use this to add follow-up context, action items, or updates
    to an existing note without overwriting it.

    Args:
        filename: Name of the existing note file.
        content: Content to append.

    Returns:
        JSON string with updated file metadata.
    """
    result = _append_note(filename, content)
    return json.dumps(result, indent=2, default=str)


# ──────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────

def main():
    """Start the MCP server with the configured transport."""
    logger.info(f"Starting {settings.mcp_server_name} server...")
    logger.info(f"Transport: {settings.mcp_transport}")
    logger.info(f"Notes dir: {settings.notes_dir.resolve()}")

    # Ensure the events database exists
    try:
        init_database()
    except Exception as e:
        logger.warning(f"Could not initialize event database: {e}")

    settings.ensure_directories()
    mcp.run(transport=settings.mcp_transport)


if __name__ == "__main__":
    main()

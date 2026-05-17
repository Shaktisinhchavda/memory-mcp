"""
Browser MCP Server — Read Chrome browsing history.

Exposes tools for querying your local Chrome history database.
Chrome does NOT need to be closed — the DB is safely copied before reading.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.browser_mcp.tools import (
    get_recent_history, get_most_visited, search_history, get_history_stats,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("browser-mcp")


@mcp.tool()
def recent_browsing_history(limit: int = 30) -> str:
    """
    Get recent Chrome browsing history.

    Returns the most recently visited URLs with titles and visit counts.

    Args:
        limit: Number of entries (default 30, max 200).

    Returns:
        JSON list of recent browsing history entries.
    """
    results = get_recent_history(limit)
    return json.dumps({"count": len(results), "history": results}, indent=2, default=str)


@mcp.tool()
def most_visited_sites(limit: int = 20) -> str:
    """
    Get the most frequently visited websites.

    Returns sites ranked by total visit count.

    Args:
        limit: Number of sites (default 20, max 100).

    Returns:
        JSON list of most visited sites.
    """
    results = get_most_visited(limit)
    return json.dumps({"count": len(results), "sites": results}, indent=2, default=str)


@mcp.tool()
def search_browsing_history(query: str, limit: int = 20) -> str:
    """
    Search Chrome history by keyword.

    Searches both URLs and page titles for the given query.

    Args:
        query: Search term (e.g., "github", "python docs", "stackoverflow").
        limit: Max results (default 20).

    Returns:
        JSON list of matching history entries.
    """
    results = search_history(query, limit)
    return json.dumps({"query": query, "count": len(results), "results": results}, indent=2, default=str)


@mcp.tool()
def browsing_stats() -> str:
    """
    Get overall Chrome browsing statistics.

    Returns total URLs tracked, total visits, and database path.
    """
    stats = get_history_stats()
    return json.dumps(stats, indent=2, default=str)


def main():
    logger.info("Starting browser-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

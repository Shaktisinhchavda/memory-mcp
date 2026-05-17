"""
Browser MCP Server — Read browsing history from Chrome, Edge, or Firefox.

Auto-detects installed browsers. Supports Windows, macOS, and Linux.
Databases are safely copied before reading — no need to close the browser.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.browser_mcp.tools import (
    get_recent_history, get_most_visited, search_history,
    get_history_stats, get_available_browsers,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("browser-mcp")


@mcp.tool()
def recent_browsing_history(limit: int = 30, browser: str = "") -> str:
    """
    Get recent browsing history.

    Auto-detects your browser. Supports Chrome, Edge, and Firefox.

    Args:
        limit: Number of entries (default 30, max 200).
        browser: Optional. Force a specific browser ("chrome", "edge", "firefox").

    Returns:
        JSON list of recent browsing history entries.
    """
    results = get_recent_history(limit, browser or None)
    return json.dumps({"count": len(results), "history": results}, indent=2, default=str)


@mcp.tool()
def most_visited_sites(limit: int = 20) -> str:
    """
    Get the most frequently visited websites.

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
    Search browsing history by keyword.

    Searches both URLs and page titles across Chrome, Edge, or Firefox.

    Args:
        query: Search term (e.g., "github", "python docs").
        limit: Max results (default 20).

    Returns:
        JSON list of matching history entries.
    """
    results = search_history(query, limit)
    return json.dumps({"query": query, "count": len(results), "results": results}, indent=2, default=str)


@mcp.tool()
def browsing_stats() -> str:
    """
    Get overall browsing statistics from all detected browsers.

    Returns stats per browser and lists which browsers were found.
    """
    stats = get_history_stats()
    return json.dumps(stats, indent=2, default=str)


@mcp.tool()
def detected_browsers() -> str:
    """
    List all browsers detected on this system.

    Shows which browsers have accessible history databases.
    """
    info = get_available_browsers()
    return json.dumps(info, indent=2, default=str)


def main():
    logger.info("Starting browser-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

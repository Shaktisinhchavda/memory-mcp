"""
Conversations MCP Server — Read exported Claude and ChatGPT conversations.

Place your exported conversation JSON files in data/conversations/
and this server will make them searchable.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.conversations_mcp.tools import (
    list_conversation_files, load_conversations, search_conversations,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("conversations-mcp")


@mcp.tool()
def list_conversation_exports() -> str:
    """
    List all conversation export files in data/conversations/.

    Shows available Claude and ChatGPT export files that can be loaded.

    Returns:
        JSON list of available conversation files.
    """
    files = list_conversation_files()
    return json.dumps({
        "directory": "data/conversations/",
        "count": len(files),
        "files": files,
        "hint": "Export conversations from claude.ai or chat.openai.com and place JSON files here.",
    }, indent=2, default=str)


@mcp.tool()
def read_conversations(filepath: str, source: str = "auto") -> str:
    """
    Load and parse a conversation export file.

    Supports Claude and ChatGPT export formats. Auto-detects the source.

    Args:
        filepath: Path to the JSON file (absolute or relative to data/conversations/).
        source: "claude", "chatgpt", or "auto" (default: auto-detect).

    Returns:
        JSON with parsed conversations including titles and message summaries.
    """
    conversations = load_conversations(filepath, source)
    return json.dumps({
        "source": source,
        "total_conversations": len(conversations),
        "conversations": conversations[:50],  # Cap output
    }, indent=2, default=str)


@mcp.tool()
def search_in_conversations(filepath: str, query: str, source: str = "auto") -> str:
    """
    Search conversation exports for a keyword.

    Searches through conversation titles and messages.

    Args:
        filepath: Path to the conversation export file.
        query: Search term (e.g., "portfolio", "deployment", "bug fix").
        source: "claude", "chatgpt", or "auto".

    Returns:
        JSON list of conversations containing the search term.
    """
    matches = search_conversations(filepath, query, source)
    return json.dumps({
        "query": query,
        "matches": len(matches),
        "results": matches,
    }, indent=2, default=str)


def main():
    logger.info("Starting conversations-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

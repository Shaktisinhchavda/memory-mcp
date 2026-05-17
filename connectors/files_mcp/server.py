"""
Files MCP Server — Read local files (PDF, DOCX, Markdown, text).

Exposes tools for reading, listing, and searching local files.
Supports PDF extraction via PyMuPDF and DOCX via python-docx.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.files_mcp.tools import read_file, list_files, search_files

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("files-mcp")


@mcp.tool()
def read_local_file(filepath: str) -> str:
    """
    Read a local file and extract its text content.

    Supports PDF, DOCX, Markdown, plain text, code files, and more.
    Provide the full path to the file you want to read.

    Args:
        filepath: Absolute path to the file (e.g. "D:/documents/report.pdf").

    Returns:
        JSON with file content, metadata, and file type.
    """
    result = read_file(filepath)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
def list_local_files(directory: str, recursive: bool = True) -> str:
    """
    List all supported files in a directory.

    Scans for PDF, DOCX, Markdown, text, code, and config files.

    Args:
        directory: Path to the directory to scan.
        recursive: Include subdirectories (default True).

    Returns:
        JSON list of files with name, path, size, and modification date.
    """
    files = list_files(directory, recursive)
    return json.dumps({"total_files": len(files), "files": files}, indent=2, default=str)


@mcp.tool()
def search_local_files(directory: str, pattern: str) -> str:
    """
    Search for files by name pattern in a directory.

    Uses glob patterns: "*.pdf" for all PDFs, "report*" for files
    starting with "report", etc.

    Args:
        directory: Directory to search in.
        pattern: Glob pattern (e.g., "*.pdf", "notes*.md").

    Returns:
        JSON list of matching files.
    """
    files = search_files(directory, pattern)
    return json.dumps({"pattern": pattern, "matches": len(files), "files": files}, indent=2, default=str)


def main():
    logger.info("Starting files-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""
Code MCP Server — Read git commits and VSCode activity.

Exposes tools for querying git history, repo status, and VSCode recent files.
"""

import json
import logging
import sys

from mcp.server.fastmcp import FastMCP

from connectors.code_mcp.tools import (
    get_recent_commits, get_commit_details, get_git_status,
    get_repo_stats, get_vscode_recent_files,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("code-mcp")


@mcp.tool()
def recent_commits(repo_path: str, limit: int = 15) -> str:
    """
    Get recent git commits from a repository.

    Args:
        repo_path: Absolute path to the git repository (e.g. "/home/user/my-project").
        limit: Number of commits to return (default 15, max 100).

    Returns:
        JSON list of commits with hash, author, date, and message.
    """
    commits = get_recent_commits(repo_path, limit)
    return json.dumps({"repo": repo_path, "count": len(commits), "commits": commits}, indent=2, default=str)


@mcp.tool()
def commit_details(repo_path: str, commit_hash: str) -> str:
    """
    Get details of a specific git commit including changed files.

    Args:
        repo_path: Path to the git repository.
        commit_hash: Full or short commit hash.

    Returns:
        JSON with commit details and list of changed files.
    """
    details = get_commit_details(repo_path, commit_hash)
    return json.dumps(details, indent=2, default=str)


@mcp.tool()
def git_status(repo_path: str) -> str:
    """
    Get current git status of a repository.

    Shows modified, staged, and untracked files plus current branch.

    Args:
        repo_path: Path to the git repository.

    Returns:
        JSON with branch name, modified/staged/untracked file lists.
    """
    status = get_git_status(repo_path)
    return json.dumps(status, indent=2, default=str)


@mcp.tool()
def repo_statistics(repo_path: str) -> str:
    """
    Get statistics about a git repository.

    Returns total commits, contributors, current branch, and remote URL.

    Args:
        repo_path: Path to the git repository.

    Returns:
        JSON with repository statistics.
    """
    stats = get_repo_stats(repo_path)
    return json.dumps(stats, indent=2, default=str)


@mcp.tool()
def vscode_recent() -> str:
    """
    Get recently opened files and folders from VSCode.

    Reads the local VSCode state database to find your recent activity.

    Returns:
        JSON list of recently opened files, folders, and workspaces.
    """
    entries = get_vscode_recent_files()
    return json.dumps({"count": len(entries), "recent": entries}, indent=2, default=str)


def main():
    logger.info("Starting code-mcp server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

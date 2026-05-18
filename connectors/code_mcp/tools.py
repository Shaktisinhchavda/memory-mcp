"""
Code MCP — Tools for reading VSCode activity and git commit history.

Extracts:
- Git commit history from any repository
- Git diff and changed files
- VSCode recently opened files (from state.vscdb)
- Repository statistics
"""

import json
import logging
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _run_git(args: list[str], cwd: str) -> tuple[str, str, int]:
    """Run a git command and return (stdout, stderr, returncode)."""
    # Prevent git from opening a pager or prompting for input
    env = {**os.environ, "GIT_PAGER": "", "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(
            ["git", "--no-pager"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            stdin=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", "git not found. Please install git.", 1
    except subprocess.TimeoutExpired:
        return "", "git command timed out", 1


def get_recent_commits(repo_path: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Get recent git commits from a repository.

    Args:
        repo_path: Path to the git repository.
        limit: Number of commits to return.

    Returns:
        List of commit dicts with hash, author, date, message.
    """
    limit = min(max(1, limit), 100)
    fmt = "%H|%an|%ae|%aI|%s"
    stdout, stderr, rc = _run_git(
        ["log", f"-{limit}", f"--format={fmt}", "--no-merges"],
        cwd=repo_path,
    )

    if rc != 0:
        return [{"error": f"git log failed: {stderr.strip()}"}]

    commits = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "hash": parts[0][:8],
                "full_hash": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "message": parts[4],
            })

    return commits


def get_commit_details(repo_path: str, commit_hash: str) -> dict[str, Any]:
    """
    Get details of a specific commit including changed files.

    Args:
        repo_path: Path to the git repository.
        commit_hash: Full or short commit hash.

    Returns:
        Dict with commit details and list of changed files.
    """
    # Get commit info
    fmt = "%H|%an|%ae|%aI|%B"
    stdout, stderr, rc = _run_git(["show", "-s", f"--format={fmt}", commit_hash], cwd=repo_path)
    if rc != 0:
        return {"error": f"Commit not found: {stderr.strip()}"}

    parts = stdout.strip().split("|", 4)

    # Get changed files
    stdout2, _, _ = _run_git(["diff-tree", "--no-commit-id", "-r", "--name-status", commit_hash], cwd=repo_path)
    files = []
    for line in stdout2.strip().split("\n"):
        if line and "\t" in line:
            status, filepath = line.split("\t", 1)
            files.append({"status": status, "file": filepath})

    return {
        "hash": parts[0] if len(parts) > 0 else commit_hash,
        "author": parts[1] if len(parts) > 1 else "",
        "email": parts[2] if len(parts) > 2 else "",
        "date": parts[3] if len(parts) > 3 else "",
        "message": parts[4].strip() if len(parts) > 4 else "",
        "changed_files": files,
    }


def get_git_status(repo_path: str) -> dict[str, Any]:
    """
    Get current git status (modified, staged, untracked files).

    Args:
        repo_path: Path to the git repository.

    Returns:
        Dict with lists of modified, staged, and untracked files.
    """
    stdout, stderr, rc = _run_git(["status", "--porcelain"], cwd=repo_path)
    if rc != 0:
        return {"error": f"git status failed: {stderr.strip()}"}

    modified, staged, untracked = [], [], []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filepath = line[3:]
        if status[0] in ("M", "A", "D", "R"):
            staged.append({"status": status[0], "file": filepath})
        if status[1] in ("M", "D"):
            modified.append({"status": status[1], "file": filepath})
        if status == "??":
            untracked.append(filepath)

    # Get current branch
    branch_stdout, _, _ = _run_git(["branch", "--show-current"], cwd=repo_path)

    return {
        "branch": branch_stdout.strip(),
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "is_clean": not (staged or modified or untracked),
    }


def get_repo_stats(repo_path: str) -> dict[str, Any]:
    """Get repository statistics."""
    # Total commits
    stdout, _, _ = _run_git(["rev-list", "--count", "HEAD"], cwd=repo_path)
    total_commits = int(stdout.strip()) if stdout.strip().isdigit() else 0

    # Contributors — use git log instead of git shortlog (shortlog hangs on Windows)
    stdout2, _, _ = _run_git(
        ["log", "--format=%an", "--no-merges", "-100"],
        cwd=repo_path,
    )
    contributor_counts: dict[str, int] = {}
    for name in stdout2.strip().split("\n"):
        if name.strip():
            contributor_counts[name.strip()] = contributor_counts.get(name.strip(), 0) + 1
    contributors = [
        {"commits": count, "name": name}
        for name, count in sorted(contributor_counts.items(), key=lambda x: -x[1])
    ]

    # Current branch
    branch, _, _ = _run_git(["branch", "--show-current"], cwd=repo_path)

    # Remote URL
    remote, _, _ = _run_git(["remote", "get-url", "origin"], cwd=repo_path)

    return {
        "total_commits": total_commits,
        "current_branch": branch.strip(),
        "remote_url": remote.strip(),
        "contributors": contributors[:10],
        "repo_path": repo_path,
    }


def get_vscode_recent_files() -> list[dict[str, Any]]:
    """
    Get recently opened files from VSCode.

    Reads the VSCode state database (state.vscdb).
    Supports Windows, macOS, and Linux.

    Returns:
        List of recently opened file/folder paths.
    """
    import platform as _platform
    system = _platform.system()

    if system == "Windows":
        vscdb_path = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "state.vscdb"
    elif system == "Darwin":
        vscdb_path = Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "state.vscdb"
    else:  # Linux
        vscdb_path = Path.home() / ".config" / "Code" / "User" / "globalStorage" / "state.vscdb"

    if not vscdb_path.exists():
        return [{"error": f"VSCode state DB not found at: {vscdb_path}"}]

    try:
        conn = sqlite3.connect(str(vscdb_path))
        cursor = conn.execute("SELECT value FROM ItemTable WHERE key = 'history.recentlyOpenedPathsList'")
        row = cursor.fetchone()
        conn.close()

        if row:
            data = json.loads(row[0])
            entries = data.get("entries", [])
            results = []
            for entry in entries[:30]:
                if "folderUri" in entry:
                    results.append({"type": "folder", "path": entry["folderUri"]})
                elif "fileUri" in entry:
                    results.append({"type": "file", "path": entry["fileUri"]})
                elif "workspace" in entry:
                    results.append({"type": "workspace", "path": entry["workspace"].get("configPath", "")})
            return results
        return [{"message": "No recent files found"}]

    except Exception as e:
        return [{"error": f"Failed to read VSCode state: {e}"}]

"""
Browser MCP — Tools for reading Chrome browsing history.

Reads Chrome's local SQLite database to extract:
- Recent browsing history (URLs, titles, visit counts)
- Most visited sites
- Search history from URL patterns
- History filtered by date range

Chrome must be closed OR the database is copied to avoid lock errors.
"""

import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Chrome epoch: January 1, 1601 (microseconds)
CHROME_EPOCH = datetime(1601, 1, 1)


def _get_chrome_history_path() -> Path:
    """Get the default Chrome history database path on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    return Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Default" / "History"


def _chrome_time_to_datetime(chrome_time: int) -> str:
    """Convert Chrome's timestamp (microseconds since 1601-01-01) to ISO string."""
    if not chrome_time:
        return "unknown"
    try:
        dt = CHROME_EPOCH + timedelta(microseconds=chrome_time)
        return dt.isoformat()
    except (ValueError, OverflowError):
        return "unknown"


def _safe_query(query: str, params: tuple = (), db_path: Path | None = None) -> list[dict[str, Any]]:
    """
    Safely query Chrome's history by copying the DB first.

    Chrome locks its database while running, so we copy it
    to a temp location before querying.
    """
    source = db_path or _get_chrome_history_path()

    if not source.exists():
        return [{"error": f"Chrome history not found at: {source}"}]

    # Copy to temp file to avoid lock issues
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, "History_copy")

    try:
        shutil.copy2(str(source), tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.OperationalError as e:
        return [{"error": f"Database error: {e}. Is Chrome running? Try closing it."}]
    except Exception as e:
        return [{"error": f"Error reading history: {e}"}]
    finally:
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def get_recent_history(limit: int = 50) -> list[dict[str, Any]]:
    """
    Get recent browsing history.

    Args:
        limit: Number of entries to return (max 200).

    Returns:
        List of dicts with url, title, visit_count, last_visit.
    """
    limit = min(max(1, limit), 200)
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
        (limit,),
    )

    # Convert Chrome timestamps
    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chrome_time_to_datetime(row.pop("last_visit_time"))

    return rows


def get_most_visited(limit: int = 20) -> list[dict[str, Any]]:
    """
    Get most frequently visited sites.

    Args:
        limit: Number of entries to return.

    Returns:
        List of dicts sorted by visit_count descending.
    """
    limit = min(max(1, limit), 100)
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY visit_count DESC LIMIT ?",
        (limit,),
    )

    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chrome_time_to_datetime(row.pop("last_visit_time"))

    return rows


def search_history(query: str, limit: int = 30) -> list[dict[str, Any]]:
    """
    Search browsing history by URL or title keyword.

    Args:
        query: Search term to look for in URLs and page titles.
        limit: Max results.

    Returns:
        Matching history entries sorted by recency.
    """
    limit = min(max(1, limit), 100)
    search_term = f"%{query}%"
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls WHERE url LIKE ? OR title LIKE ? ORDER BY last_visit_time DESC LIMIT ?",
        (search_term, search_term, limit),
    )

    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chrome_time_to_datetime(row.pop("last_visit_time"))

    return rows


def get_history_stats() -> dict[str, Any]:
    """Get overall browsing statistics."""
    total = _safe_query("SELECT COUNT(*) as total, SUM(visit_count) as total_visits FROM urls")
    if total and "error" not in total[0]:
        return {
            "total_urls": total[0].get("total", 0),
            "total_visits": total[0].get("total_visits", 0),
            "chrome_db_path": str(_get_chrome_history_path()),
            "db_exists": _get_chrome_history_path().exists(),
        }
    return total[0] if total else {"error": "Could not read history stats"}

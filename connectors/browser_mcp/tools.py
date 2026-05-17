"""
Browser MCP — Tools for reading browser history (Chrome, Firefox, Edge).

Reads local SQLite databases to extract:
- Recent browsing history (URLs, titles, visit counts)
- Most visited sites
- Search history from URL patterns

Supports Chrome, Firefox, and Edge on Windows, macOS, and Linux.
Databases are copied before reading to avoid lock issues.
"""

import logging
import os
import platform
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Chrome/Edge epoch: January 1, 1601 (microseconds)
CHROMIUM_EPOCH = datetime(1601, 1, 1)


# ── Browser DB Path Detection ──

def _get_browser_paths() -> dict[str, Path]:
    """
    Detect available browser history databases.

    Returns a dict of {browser_name: db_path} for all found browsers.
    Supports Windows, macOS, and Linux.
    """
    system = platform.system()
    browsers: dict[str, Path] = {}

    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        roaming = os.environ.get("APPDATA", "")

        candidates = {
            "Chrome": Path(local) / "Google" / "Chrome" / "User Data" / "Default" / "History",
            "Edge": Path(local) / "Microsoft" / "Edge" / "User Data" / "Default" / "History",
            "Firefox": None,  # Firefox uses profiles, handled below
        }

        # Firefox: scan profiles directory
        ff_profiles = Path(roaming) / "Mozilla" / "Firefox" / "Profiles"
        if ff_profiles.exists():
            for profile_dir in ff_profiles.iterdir():
                places = profile_dir / "places.sqlite"
                if places.exists():
                    candidates["Firefox"] = places
                    break

    elif system == "Darwin":  # macOS
        home = Path.home()
        candidates = {
            "Chrome": home / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "History",
            "Edge": home / "Library" / "Application Support" / "Microsoft Edge" / "Default" / "History",
            "Firefox": None,
        }
        ff_profiles = home / "Library" / "Application Support" / "Firefox" / "Profiles"
        if ff_profiles.exists():
            for profile_dir in ff_profiles.iterdir():
                places = profile_dir / "places.sqlite"
                if places.exists():
                    candidates["Firefox"] = places
                    break

    else:  # Linux
        home = Path.home()
        candidates = {
            "Chrome": home / ".config" / "google-chrome" / "Default" / "History",
            "Edge": home / ".config" / "microsoft-edge" / "Default" / "History",
            "Firefox": None,
        }
        ff_dir = home / ".mozilla" / "firefox"
        if ff_dir.exists():
            for profile_dir in ff_dir.iterdir():
                places = profile_dir / "places.sqlite"
                if places.exists():
                    candidates["Firefox"] = places
                    break

    for name, path in candidates.items():
        if path and path.exists():
            browsers[name] = path

    return browsers


def _detect_default_browser() -> tuple[str, Path] | tuple[None, None]:
    """Find the first available browser."""
    browsers = _get_browser_paths()
    # Priority: Chrome > Edge > Firefox
    for name in ["Chrome", "Edge", "Firefox"]:
        if name in browsers:
            return name, browsers[name]
    return None, None


# ── Timestamp Conversion ──

def _chromium_time_to_iso(chrome_time: int) -> str:
    """Convert Chromium timestamp (microseconds since 1601-01-01) to ISO string."""
    if not chrome_time:
        return "unknown"
    try:
        return (CHROMIUM_EPOCH + timedelta(microseconds=chrome_time)).isoformat()
    except (ValueError, OverflowError):
        return "unknown"


def _firefox_time_to_iso(ff_time: int) -> str:
    """Convert Firefox timestamp (microseconds since Unix epoch) to ISO string."""
    if not ff_time:
        return "unknown"
    try:
        return datetime.fromtimestamp(ff_time / 1_000_000).isoformat()
    except (ValueError, OverflowError, OSError):
        return "unknown"


# ── Safe Query ──

def _safe_query(query: str, params: tuple = (), db_path: Path | None = None) -> list[dict[str, Any]]:
    """
    Safely query a browser history database by copying it first.

    Browsers lock their database while running, so we copy it
    to a temp location before querying.
    """
    if db_path is None:
        _, db_path = _detect_default_browser()
    if db_path is None:
        return [{"error": "No browser history found. Supported: Chrome, Edge, Firefox."}]

    if not db_path.exists():
        return [{"error": f"Browser history not found at: {db_path}"}]

    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, "History_copy")

    try:
        shutil.copy2(str(db_path), tmp_path)
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.OperationalError as e:
        return [{"error": f"Database error: {e}. Try closing the browser."}]
    except Exception as e:
        return [{"error": f"Error reading history: {e}"}]
    finally:
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


# ── Chromium-based Queries (Chrome, Edge) ──

def _chromium_recent(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT ?",
        (limit,), db_path,
    )
    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chromium_time_to_iso(row.pop("last_visit_time"))
    return rows


def _chromium_search(db_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    term = f"%{query}%"
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls WHERE url LIKE ? OR title LIKE ? ORDER BY last_visit_time DESC LIMIT ?",
        (term, term, limit), db_path,
    )
    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chromium_time_to_iso(row.pop("last_visit_time"))
    return rows


def _chromium_most_visited(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows = _safe_query(
        "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY visit_count DESC LIMIT ?",
        (limit,), db_path,
    )
    for row in rows:
        if "last_visit_time" in row:
            row["last_visit"] = _chromium_time_to_iso(row.pop("last_visit_time"))
    return rows


# ── Firefox Queries ──

def _firefox_recent(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows = _safe_query(
        "SELECT p.url, p.title, p.visit_count, p.last_visit_date "
        "FROM moz_places p WHERE p.visit_count > 0 "
        "ORDER BY p.last_visit_date DESC LIMIT ?",
        (limit,), db_path,
    )
    for row in rows:
        if "last_visit_date" in row:
            row["last_visit"] = _firefox_time_to_iso(row.pop("last_visit_date"))
    return rows


def _firefox_search(db_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    term = f"%{query}%"
    rows = _safe_query(
        "SELECT p.url, p.title, p.visit_count, p.last_visit_date "
        "FROM moz_places p WHERE (p.url LIKE ? OR p.title LIKE ?) AND p.visit_count > 0 "
        "ORDER BY p.last_visit_date DESC LIMIT ?",
        (term, term, limit), db_path,
    )
    for row in rows:
        if "last_visit_date" in row:
            row["last_visit"] = _firefox_time_to_iso(row.pop("last_visit_date"))
    return rows


def _firefox_most_visited(db_path: Path, limit: int) -> list[dict[str, Any]]:
    rows = _safe_query(
        "SELECT p.url, p.title, p.visit_count, p.last_visit_date "
        "FROM moz_places p WHERE p.visit_count > 0 "
        "ORDER BY p.visit_count DESC LIMIT ?",
        (limit,), db_path,
    )
    for row in rows:
        if "last_visit_date" in row:
            row["last_visit"] = _firefox_time_to_iso(row.pop("last_visit_date"))
    return rows


# ── Public API ──

def get_available_browsers() -> dict[str, Any]:
    """List all detected browsers with their history DB paths."""
    browsers = _get_browser_paths()
    return {
        "browsers": {name: str(path) for name, path in browsers.items()},
        "count": len(browsers),
        "platform": platform.system(),
    }


def get_recent_history(limit: int = 50, browser: str | None = None) -> list[dict[str, Any]]:
    """Get recent browsing history from the specified or default browser."""
    limit = min(max(1, limit), 200)
    browsers = _get_browser_paths()

    if browser:
        browser = browser.capitalize()
        if browser not in browsers:
            return [{"error": f"Browser '{browser}' not found. Available: {list(browsers.keys())}"}]
        db_path = browsers[browser]
    else:
        browser, db_path = _detect_default_browser()
        if not db_path:
            return [{"error": "No browser history found. Supported: Chrome, Edge, Firefox."}]

    if browser == "Firefox":
        results = _firefox_recent(db_path, limit)
    else:
        results = _chromium_recent(db_path, limit)

    for r in results:
        r["browser"] = browser
    return results


def get_most_visited(limit: int = 20, browser: str | None = None) -> list[dict[str, Any]]:
    """Get most frequently visited sites."""
    limit = min(max(1, limit), 100)
    browsers = _get_browser_paths()

    if browser:
        browser = browser.capitalize()
        if browser not in browsers:
            return [{"error": f"Browser '{browser}' not found. Available: {list(browsers.keys())}"}]
        db_path = browsers[browser]
    else:
        browser, db_path = _detect_default_browser()
        if not db_path:
            return [{"error": "No browser history found."}]

    if browser == "Firefox":
        results = _firefox_most_visited(db_path, limit)
    else:
        results = _chromium_most_visited(db_path, limit)

    for r in results:
        r["browser"] = browser
    return results


def search_history(query: str, limit: int = 30, browser: str | None = None) -> list[dict[str, Any]]:
    """Search browsing history by URL or title keyword."""
    limit = min(max(1, limit), 100)
    browsers = _get_browser_paths()

    if browser:
        browser = browser.capitalize()
        if browser not in browsers:
            return [{"error": f"Browser '{browser}' not found. Available: {list(browsers.keys())}"}]
        db_path = browsers[browser]
    else:
        browser, db_path = _detect_default_browser()
        if not db_path:
            return [{"error": "No browser history found."}]

    if browser == "Firefox":
        results = _firefox_search(db_path, query, limit)
    else:
        results = _chromium_search(db_path, query, limit)

    for r in results:
        r["browser"] = browser
    return results


def get_history_stats() -> dict[str, Any]:
    """Get overall browsing statistics from all detected browsers."""
    browsers = _get_browser_paths()
    stats: dict[str, Any] = {"browsers_found": list(browsers.keys()), "platform": platform.system()}

    for name, path in browsers.items():
        if name == "Firefox":
            total = _safe_query("SELECT COUNT(*) as total, SUM(visit_count) as total_visits FROM moz_places WHERE visit_count > 0", db_path=path)
        else:
            total = _safe_query("SELECT COUNT(*) as total, SUM(visit_count) as total_visits FROM urls", db_path=path)

        if total and "error" not in total[0]:
            stats[name] = {"total_urls": total[0].get("total", 0), "total_visits": total[0].get("total_visits", 0)}
        else:
            stats[name] = {"error": total[0].get("error", "unknown") if total else "query failed"}

    return stats

"""
SQLite Event Database — Persistent storage for file system events.

Thread-safe: Each write opens its own connection because watchdog
runs the observer in a background thread.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    return str(settings.events_db_path.resolve())


def init_database() -> None:
    """Create the events table if it doesn't exist."""
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                src_path TEXT NOT NULL,
                dest_path TEXT,
                timestamp TEXT NOT NULL,
                file_extension TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON file_events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON file_events(event_type)")
        conn.commit()
        logger.info(f"Event database initialized at: {db_path}")
    finally:
        conn.close()


def log_event(event_type: str, src_path: str, dest_path: str | None = None) -> None:
    """Log a file system event. Thread-safe."""
    db_path = _get_db_path()
    ext = Path(src_path).suffix.lower() if src_path else None
    ts = datetime.now().isoformat()
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO file_events (event_type,src_path,dest_path,timestamp,file_extension) VALUES (?,?,?,?,?)",
            (event_type, src_path, dest_path, ts, ext),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Event logged: {event_type} — {src_path}")
    except Exception as e:
        logger.error(f"Failed to log event: {e}")


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Get the most recent file events, newest first."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM file_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return []


def get_events_by_type(event_type: str, limit: int = 50) -> list[dict[str, Any]]:
    """Get events filtered by type, newest first."""
    db_path = _get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM file_events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (event_type, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to query events: {e}")
        return []

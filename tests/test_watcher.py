"""Tests for the event logger."""

import sys
import os
import time
sys.path.insert(0, ".")

from core_mcp.event_logger.database import init_database, log_event, get_recent_events


def test_event_logging():
    """Test that events can be logged and retrieved."""
    init_database()

    # Log some test events
    log_event("created", "/test/file1.md")
    log_event("modified", "/test/file1.md")
    log_event("created", "/test/file2.txt")
    log_event("deleted", "/test/file1.md")

    events = get_recent_events(limit=10)
    print(f"Logged {len(events)} events:")
    for e in events:
        print(f"  [{e['event_type']}] {e['src_path']} at {e['timestamp']}")

    assert len(events) >= 4, f"Expected at least 4 events, got {len(events)}"
    assert events[0]["event_type"] == "deleted"  # Most recent first
    print("\n✅ test_event_logging passed")


if __name__ == "__main__":
    test_event_logging()
    print("\n🎉 All watcher tests passed!")

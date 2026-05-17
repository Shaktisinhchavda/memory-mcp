"""
Start Watcher Script — Launch the file system event logger.

Run this in a separate terminal:
    uv run python scripts/start_watcher.py
"""

import sys

sys.path.insert(0, ".")

from core_mcp.event_logger.watcher import start_watcher

if __name__ == "__main__":
    start_watcher()

"""
File System Watcher — Monitors data directories for changes using watchdog.

Runs as a background process and logs every file event (create, modify,
delete, move) to SQLite. This builds a timeline of your activity.
"""

import logging
import sys
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core_mcp.event_logger.database import init_database, log_event
from config.settings import settings

logger = logging.getLogger(__name__)


class DataChangeHandler(FileSystemEventHandler):
    """Handles file system events and logs them to SQLite."""

    def on_created(self, event):
        if not event.is_directory:
            log_event("created", event.src_path)
            logger.info(f"CREATED: {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            log_event("modified", event.src_path)
            logger.debug(f"MODIFIED: {event.src_path}")

    def on_deleted(self, event):
        if not event.is_directory:
            log_event("deleted", event.src_path)
            logger.info(f"DELETED: {event.src_path}")

    def on_moved(self, event):
        if not event.is_directory:
            log_event("moved", event.src_path, event.dest_path)
            logger.info(f"MOVED: {event.src_path} -> {event.dest_path}")


def start_watcher() -> None:
    """
    Start the file system watcher on data/notes and data/files.

    This function blocks forever (runs until Ctrl+C).
    Run it in a separate terminal or as a background service.
    """
    # Configure logging for the watcher process
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    init_database()
    settings.ensure_directories()

    handler = DataChangeHandler()
    observer = Observer()

    # Watch both directories
    watch_dirs = [
        settings.notes_dir.resolve(),
        settings.files_dir.resolve(),
    ]

    for watch_dir in watch_dirs:
        watch_dir.mkdir(parents=True, exist_ok=True)
        observer.schedule(handler, str(watch_dir), recursive=True)
        logger.info(f"Watching: {watch_dir}")

    observer.start()
    logger.info("File watcher started. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher...")
        observer.stop()

    observer.join()
    logger.info("File watcher stopped.")


if __name__ == "__main__":
    start_watcher()

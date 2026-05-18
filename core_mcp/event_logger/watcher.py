"""
File System Watcher — Monitors data directories for changes using watchdog.

Runs as a background process and:
1. Logs every file event (create, modify, delete, move) to SQLite
2. **Auto-indexes** new/modified notes into ChromaDB for immediate search

This means `save_note` writes are instantly searchable — no manual re-indexing.
"""

import logging
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core_mcp.event_logger.database import init_database, log_event
from config.settings import settings

logger = logging.getLogger(__name__)

# File types that should be auto-indexed
INDEXABLE_EXTENSIONS = {".md", ".txt", ".rst", ".org"}

# Lazy-loaded indexer (heavy import — only loaded on first file change)
_indexer = None


def _get_indexer():
    """Lazy-load the indexer to avoid slow startup."""
    global _indexer
    if _indexer is None:
        try:
            from core_mcp.vector_store.indexer import Indexer
            _indexer = Indexer()
            logger.info("Auto-indexer loaded")
        except Exception as e:
            logger.warning(f"Could not load auto-indexer: {e}")
    return _indexer


def _should_index(filepath: str) -> bool:
    """Check if a file should trigger auto-indexing."""
    p = Path(filepath)
    notes_dir = str(settings.notes_dir.resolve())
    return (
        p.suffix.lower() in INDEXABLE_EXTENSIONS
        and str(p).startswith(notes_dir)
    )


def _auto_index_file(filepath: str) -> None:
    """Index a single file into ChromaDB."""
    indexer = _get_indexer()
    if indexer is None:
        return
    try:
        p = Path(filepath)
        if p.exists():
            result = indexer.index_file(p)
            logger.info(f"Auto-indexed: {p.name} ({result.get('chunks', 0)} chunks)")
    except Exception as e:
        logger.warning(f"Auto-index failed for {filepath}: {e}")


def _auto_delete_file(filepath: str) -> None:
    """Remove a deleted file from ChromaDB."""
    indexer = _get_indexer()
    if indexer is None:
        return
    try:
        doc_id = Path(filepath).name
        indexer.store.delete_document(doc_id)
        logger.info(f"Auto-removed from index: {doc_id}")
    except Exception as e:
        logger.warning(f"Auto-delete failed for {filepath}: {e}")


class DataChangeHandler(FileSystemEventHandler):
    """Handles file system events: logs to SQLite + auto-indexes notes."""

    def on_created(self, event):
        if not event.is_directory:
            log_event("created", event.src_path)
            logger.info(f"CREATED: {event.src_path}")
            if _should_index(event.src_path):
                _auto_index_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            log_event("modified", event.src_path)
            logger.debug(f"MODIFIED: {event.src_path}")
            if _should_index(event.src_path):
                _auto_index_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            log_event("deleted", event.src_path)
            logger.info(f"DELETED: {event.src_path}")
            if _should_index(event.src_path):
                _auto_delete_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            log_event("moved", event.src_path, event.dest_path)
            logger.info(f"MOVED: {event.src_path} -> {event.dest_path}")
            if _should_index(event.src_path):
                _auto_delete_file(event.src_path)
            if _should_index(event.dest_path):
                _auto_index_file(event.dest_path)


def start_watcher() -> None:
    """
    Start the file system watcher on data/notes and data/files.

    This function blocks forever (runs until Ctrl+C).
    Run it in a separate terminal or as a background service.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )

    init_database()
    settings.ensure_directories()

    handler = DataChangeHandler()
    observer = Observer()

    watch_dirs = [
        settings.notes_dir.resolve(),
        settings.files_dir.resolve(),
    ]

    for watch_dir in watch_dirs:
        watch_dir.mkdir(parents=True, exist_ok=True)
        observer.schedule(handler, str(watch_dir), recursive=True)
        logger.info(f"Watching: {watch_dir}")

    observer.start()
    logger.info("File watcher started (with auto-indexing). Press Ctrl+C to stop.")

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


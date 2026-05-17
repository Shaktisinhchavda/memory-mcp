"""
Notes Tool — Read and list personal notes from the local filesystem.

This MCP tool gives AI agents the ability to:
- List all notes in your notes directory
- Read the full content of any specific note
- Get note metadata (size, last modified, etc.)

The tool reads from the path configured in NOTES_DIR (.env).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

# Supported note file extensions
SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst", ".org"}


def list_notes() -> list[dict[str, Any]]:
    """
    List all notes in the notes directory.

    Returns a list of note metadata dicts, each containing:
    - name: filename
    - path: relative path from notes dir
    - size_bytes: file size
    - modified_at: last modification timestamp
    - extension: file type

    Returns:
        List of note metadata dictionaries.
    """
    notes_dir = settings.notes_dir.resolve()

    if not notes_dir.exists():
        logger.warning(f"Notes directory does not exist: {notes_dir}")
        return []

    notes = []
    for filepath in sorted(notes_dir.rglob("*")):
        if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
            stat = filepath.stat()
            notes.append({
                "name": filepath.name,
                "path": str(filepath.relative_to(notes_dir)),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": filepath.suffix,
            })

    return notes


def read_note(filename: str) -> dict[str, Any]:
    """
    Read the full content of a specific note.

    Searches for the file in the notes directory. Supports both
    exact filenames ("meeting.md") and relative paths ("work/meeting.md").

    Args:
        filename: Name or relative path of the note file.

    Returns:
        Dict with keys: name, content, size_bytes, modified_at.
        If file not found, returns dict with error key.
    """
    notes_dir = settings.notes_dir.resolve()
    filepath = notes_dir / filename

    # Security: prevent path traversal attacks
    try:
        filepath = filepath.resolve()
        if not str(filepath).startswith(str(notes_dir)):
            return {"error": f"Access denied: path outside notes directory"}
    except (OSError, ValueError):
        return {"error": f"Invalid path: {filename}"}

    if not filepath.exists():
        # Try to find by name anywhere in the notes directory
        matches = list(notes_dir.rglob(filename))
        if matches:
            filepath = matches[0]
        else:
            available = [n["name"] for n in list_notes()]
            return {
                "error": f"Note not found: {filename}",
                "available_notes": available[:20],  # Don't overwhelm the context
            }

    if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"error": f"Unsupported file type: {filepath.suffix}"}

    try:
        content = filepath.read_text(encoding="utf-8")
        stat = filepath.stat()
        return {
            "name": filepath.name,
            "path": str(filepath.relative_to(notes_dir)),
            "content": content,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except (UnicodeDecodeError, PermissionError) as e:
        return {"error": f"Could not read {filename}: {e}"}

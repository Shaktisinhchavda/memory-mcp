"""
Notes Tool — Read, list, and write personal notes on the local filesystem.

This MCP tool gives AI agents the ability to:
- List all notes in your notes directory
- Read the full content of any specific note
- **Save new notes** (memory write-back)
- **Append to existing notes**
- Get note metadata (size, last modified, etc.)

The tool reads/writes from the path configured in NOTES_DIR (.env).
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


def save_note(filename: str, content: str) -> dict[str, Any]:
    """
    Save a new note or overwrite an existing one.

    This enables AI agents to **write memories back** into the system.
    The note is saved to the notes directory and can be indexed later.

    Args:
        filename: Name for the note file (e.g., "meeting-summary.md").
                  Must end in a supported extension (.md, .txt, .rst, .org).
        content: Full content to write.

    Returns:
        Dict with saved file metadata, or error.
    """
    notes_dir = settings.notes_dir.resolve()

    # Validate extension
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return {"error": f"Unsupported extension '{ext}'. Use: {SUPPORTED_EXTENSIONS}"}

    filepath = (notes_dir / filename).resolve()

    # Security: prevent path traversal
    if not str(filepath).startswith(str(notes_dir)):
        return {"error": "Access denied: path outside notes directory"}

    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        stat = filepath.stat()
        logger.info(f"Saved note: {filename} ({stat.st_size} bytes)")
        return {
            "status": "saved",
            "name": filepath.name,
            "path": str(filepath.relative_to(notes_dir)),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except (PermissionError, OSError) as e:
        return {"error": f"Could not save {filename}: {e}"}


def append_note(filename: str, content: str) -> dict[str, Any]:
    """
    Append content to an existing note.

    Useful for AI agents to add follow-up context, action items,
    or conversation summaries to existing notes.

    Args:
        filename: Name of the existing note file.
        content: Content to append (will be added with a newline separator).

    Returns:
        Dict with updated file metadata, or error.
    """
    notes_dir = settings.notes_dir.resolve()
    filepath = (notes_dir / filename).resolve()

    if not str(filepath).startswith(str(notes_dir)):
        return {"error": "Access denied: path outside notes directory"}

    if not filepath.exists():
        return {"error": f"Note not found: {filename}. Use save_note to create new notes."}

    try:
        existing = filepath.read_text(encoding="utf-8")
        updated = existing.rstrip() + "\n\n" + content
        filepath.write_text(updated, encoding="utf-8")
        stat = filepath.stat()
        logger.info(f"Appended to note: {filename}")
        return {
            "status": "appended",
            "name": filepath.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except (PermissionError, OSError, UnicodeDecodeError) as e:
        return {"error": f"Could not append to {filename}: {e}"}


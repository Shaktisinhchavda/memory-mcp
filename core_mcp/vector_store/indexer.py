"""
Document Indexer — Reads notes/files and feeds them into the vector store.

This module handles:
- Scanning the notes directory for markdown files
- Splitting long documents into semantic chunks
- Indexing everything into ChromaDB with metadata

Usage:
    from core_mcp.vector_store.indexer import Indexer
    
    indexer = Indexer()
    stats = indexer.index_all_notes()
    print(f"Indexed {stats['total_files']} files, {stats['total_chunks']} chunks")
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

# Chunk settings
CHUNK_SIZE = 500  # characters per chunk
CHUNK_OVERLAP = 50  # overlap between chunks for context continuity


def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into overlapping chunks for better retrieval.

    Uses a simple character-based splitter that respects line boundaries
    where possible. For Phase 1 this is sufficient — we can upgrade to
    semantic chunking in later phases.

    Args:
        text: The full document text.
        chunk_size: Target size of each chunk in characters.
        overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a newline boundary for cleaner chunks
        if end < len(text):
            newline_pos = text.rfind("\n", start + chunk_size // 2, end)
            if newline_pos != -1:
                end = newline_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


def extract_metadata_from_note(filepath: Path) -> dict[str, Any]:
    """
    Extract metadata from a note file.

    Currently extracts:
    - filename
    - file extension
    - last modified date
    - file size in bytes

    Future: parse YAML frontmatter for tags, title, etc.

    Args:
        filepath: Path to the note file.

    Returns:
        Metadata dictionary.
    """
    stat = filepath.stat()
    return {
        "filename": filepath.name,
        "extension": filepath.suffix,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size_bytes": stat.st_size,
        "source": "notes",
    }


class Indexer:
    """
    Scans the notes directory and indexes content into ChromaDB.

    The indexer is designed to be idempotent — running it multiple times
    will update existing documents rather than creating duplicates.
    """

    def __init__(self) -> None:
        """Initialize the indexer (lazy-loads the vector store)."""
        # Lazy import to avoid circular dependencies and heavy model loading
        # until actually needed
        self._store = None

    @property
    def store(self):
        """Lazy-load the vector store (triggers model download on first use)."""
        if self._store is None:
            from core_mcp.vector_store.store import VectorStore
            self._store = VectorStore()
        return self._store

    def index_file(self, filepath: Path) -> dict[str, Any]:
        """
        Index a single file into the vector store.

        Args:
            filepath: Path to the file to index.

        Returns:
            Dict with indexing stats (chunks_created, etc.).
        """
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError) as e:
            logger.warning(f"Skipping {filepath}: {e}")
            return {"file": str(filepath), "status": "skipped", "error": str(e)}

        if not content.strip():
            logger.debug(f"Skipping empty file: {filepath}")
            return {"file": str(filepath), "status": "skipped", "error": "empty"}

        metadata = extract_metadata_from_note(filepath)
        chunks = split_into_chunks(content)
        doc_id = filepath.name

        if len(chunks) == 1:
            # Small file — store as single document
            self.store.add_document(doc_id, content, metadata)
        else:
            # Large file — store as chunks
            self.store.add_chunks(doc_id, chunks, metadata)

        return {
            "file": str(filepath),
            "status": "indexed",
            "chunks": len(chunks),
        }

    def index_all_notes(self) -> dict[str, Any]:
        """
        Scan and index all supported files in the notes directory.

        Supported formats: .md, .txt, .rst, .org

        Returns:
            Summary dict with total_files, total_chunks, errors.
        """
        settings.ensure_directories()
        notes_dir = settings.notes_dir.resolve()

        if not notes_dir.exists():
            logger.warning(f"Notes directory does not exist: {notes_dir}")
            return {"total_files": 0, "total_chunks": 0, "errors": []}

        # Supported text formats
        extensions = {".md", ".txt", ".rst", ".org"}
        files = [
            f for f in notes_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in extensions
        ]

        logger.info(f"Found {len(files)} files to index in {notes_dir}")

        results = []
        for filepath in sorted(files):
            result = self.index_file(filepath)
            results.append(result)

        total_chunks = sum(r.get("chunks", 0) for r in results if r["status"] == "indexed")
        errors = [r for r in results if r["status"] == "skipped"]

        summary = {
            "total_files": len(files),
            "indexed_files": len(results) - len(errors),
            "total_chunks": total_chunks,
            "errors": errors,
        }

        logger.info(
            f"Indexing complete: {summary['indexed_files']}/{summary['total_files']} files, "
            f"{total_chunks} chunks"
        )

        return summary

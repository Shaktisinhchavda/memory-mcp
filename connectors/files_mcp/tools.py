"""
Files MCP — Tools for reading local files (PDFs, DOCX, Markdown, text).

Supports:
- Plain text (.txt, .md, .rst, .org, .csv, .json, .yaml, .yml)
- PDF extraction via PyMuPDF
- Word documents via python-docx
- Directory listing with metadata
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported file types by category
TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".org", ".csv", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".log", ".py", ".js", ".ts", ".html", ".css"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
ALL_SUPPORTED = TEXT_EXTENSIONS | PDF_EXTENSIONS | DOCX_EXTENSIONS


def _read_text_file(filepath: Path) -> str:
    """Read a plain text file."""
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return filepath.read_text(encoding="latin-1")


def _read_pdf_file(filepath: Path) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        import pymupdf
        doc = pymupdf.open(str(filepath))
        text_parts = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
        doc.close()
        return "\n\n".join(text_parts) if text_parts else "(No extractable text in PDF)"
    except Exception as e:
        return f"(Error reading PDF: {e})"


def _read_docx_file(filepath: Path) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(str(filepath))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs) if paragraphs else "(Empty document)"
    except Exception as e:
        return f"(Error reading DOCX: {e})"


def read_file(filepath: str, base_dir: str | None = None) -> dict[str, Any]:
    """
    Read a file and extract its text content.

    Supports PDF, DOCX, and plain text formats.

    Args:
        filepath: Path to the file (absolute or relative to base_dir).
        base_dir: Optional base directory for relative paths.

    Returns:
        Dict with name, content, size_bytes, modified_at, file_type.
    """
    path = Path(filepath)
    if not path.is_absolute() and base_dir:
        path = Path(base_dir) / path

    path = path.resolve()

    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    if not path.is_file():
        return {"error": f"Not a file: {filepath}"}

    stat = path.stat()
    suffix = path.suffix.lower()

    # Read content based on file type
    if suffix in PDF_EXTENSIONS:
        content = _read_pdf_file(path)
        file_type = "pdf"
    elif suffix in DOCX_EXTENSIONS:
        content = _read_docx_file(path)
        file_type = "docx"
    elif suffix in TEXT_EXTENSIONS:
        content = _read_text_file(path)
        file_type = "text"
    else:
        return {"error": f"Unsupported file type: {suffix}"}

    return {
        "name": path.name,
        "path": str(path),
        "content": content,
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "file_type": file_type,
    }


def list_files(directory: str, recursive: bool = True) -> list[dict[str, Any]]:
    """
    List all supported files in a directory.

    Args:
        directory: Path to the directory to scan.
        recursive: Whether to include subdirectories.

    Returns:
        List of file metadata dicts.
    """
    dir_path = Path(directory).resolve()

    if not dir_path.exists():
        return [{"error": f"Directory not found: {directory}"}]

    files = []
    iterator = dir_path.rglob("*") if recursive else dir_path.glob("*")

    for fp in sorted(iterator):
        if fp.is_file() and fp.suffix.lower() in ALL_SUPPORTED:
            stat = fp.stat()
            files.append({
                "name": fp.name,
                "path": str(fp),
                "relative_path": str(fp.relative_to(dir_path)),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": fp.suffix.lower(),
            })

    return files


def search_files(directory: str, pattern: str) -> list[dict[str, Any]]:
    """
    Search for files matching a name pattern.

    Args:
        directory: Directory to search in.
        pattern: Glob pattern (e.g., "*.pdf", "report*").

    Returns:
        List of matching file metadata dicts.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.exists():
        return [{"error": f"Directory not found: {directory}"}]

    files = []
    for fp in sorted(dir_path.rglob(pattern)):
        if fp.is_file() and fp.suffix.lower() in ALL_SUPPORTED:
            stat = fp.stat()
            files.append({
                "name": fp.name,
                "path": str(fp),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

    return files

"""
Conversations MCP — Tools for reading exported AI conversation JSON.

Supports:
- Claude exported conversations (from claude.ai Settings > Export Data)
- ChatGPT exported conversations (from Settings > Data Controls > Export)

Place exported files in data/conversations/ directory.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

CONVERSATIONS_DIR = settings.data_dir / "conversations"


def _ensure_dir():
    """Create conversations directory if it doesn't exist."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_claude_conversations(filepath: Path) -> list[dict[str, Any]]:
    """Parse Claude export format (conversations.json)."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))

        conversations = []
        items = data if isinstance(data, list) else [data]

        for conv in items:
            messages = []
            chat_messages = conv.get("chat_messages", [])
            for msg in chat_messages:
                content_parts = msg.get("content", [])
                text = ""
                for part in content_parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text += part.get("text", "")
                    elif isinstance(part, str):
                        text += part

                if text:
                    messages.append({
                        "role": msg.get("sender", "unknown"),
                        "text": text[:500],  # Truncate long messages
                    })

            conversations.append({
                "title": conv.get("name", conv.get("title", "Untitled")),
                "uuid": conv.get("uuid", ""),
                "created_at": conv.get("created_at", ""),
                "updated_at": conv.get("updated_at", ""),
                "message_count": len(messages),
                "messages": messages[:50],  # Cap at 50 messages
                "source": "claude",
            })

        return conversations
    except Exception as e:
        return [{"error": f"Failed to parse Claude export: {e}"}]


def _load_chatgpt_conversations(filepath: Path) -> list[dict[str, Any]]:
    """Parse ChatGPT export format (conversations.json)."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))

        conversations = []
        items = data if isinstance(data, list) else [data]

        for conv in items:
            messages = []
            mapping = conv.get("mapping", {})

            for node_id, node in mapping.items():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    text = " ".join(str(p) for p in msg["content"]["parts"] if isinstance(p, str))
                    if text.strip():
                        messages.append({
                            "role": msg.get("author", {}).get("role", "unknown"),
                            "text": text[:500],
                        })

            create_time = conv.get("create_time")
            conversations.append({
                "title": conv.get("title", "Untitled"),
                "id": conv.get("id", ""),
                "created_at": datetime.fromtimestamp(create_time).isoformat() if create_time else "",
                "message_count": len(messages),
                "messages": messages[:50],
                "source": "chatgpt",
            })

        return conversations
    except Exception as e:
        return [{"error": f"Failed to parse ChatGPT export: {e}"}]


def list_conversation_files() -> list[dict[str, Any]]:
    """List all conversation export files in data/conversations/."""
    _ensure_dir()
    files = []
    for fp in sorted(CONVERSATIONS_DIR.rglob("*.json")):
        stat = fp.stat()
        files.append({
            "name": fp.name,
            "path": str(fp),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return files


def load_conversations(filepath: str, source: str = "auto") -> list[dict[str, Any]]:
    """
    Load conversations from an export file.

    Args:
        filepath: Path to the JSON export file.
        source: "claude", "chatgpt", or "auto" (detect from content).

    Returns:
        List of parsed conversation dicts.
    """
    path = Path(filepath)
    if not path.is_absolute():
        path = CONVERSATIONS_DIR / path

    if not path.exists():
        return [{"error": f"File not found: {filepath}"}]

    # Auto-detect source
    if source == "auto":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sample = data[0] if isinstance(data, list) else data
            if "chat_messages" in sample:
                source = "claude"
            elif "mapping" in sample:
                source = "chatgpt"
            else:
                source = "unknown"
        except Exception:
            source = "unknown"

    if source == "claude":
        return _load_claude_conversations(path)
    elif source == "chatgpt":
        return _load_chatgpt_conversations(path)
    else:
        return [{"error": f"Unknown conversation format. Use source='claude' or 'chatgpt'."}]


def search_conversations(filepath: str, query: str, source: str = "auto") -> list[dict[str, Any]]:
    """
    Search conversations for a keyword.

    Args:
        filepath: Path to conversation export file.
        query: Search term.
        source: "claude", "chatgpt", or "auto".

    Returns:
        Conversations containing the query.
    """
    conversations = load_conversations(filepath, source)
    query_lower = query.lower()

    matches = []
    for conv in conversations:
        if "error" in conv:
            return [conv]

        # Search in title and messages
        title_match = query_lower in conv.get("title", "").lower()
        msg_matches = []
        for msg in conv.get("messages", []):
            if query_lower in msg.get("text", "").lower():
                msg_matches.append(msg)

        if title_match or msg_matches:
            matches.append({
                "title": conv.get("title"),
                "source": conv.get("source"),
                "created_at": conv.get("created_at"),
                "matching_messages": len(msg_matches),
                "sample_matches": msg_matches[:5],
            })

    return matches

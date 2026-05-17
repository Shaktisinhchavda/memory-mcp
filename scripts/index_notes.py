"""
Index Notes Script — One-shot indexing of all notes into ChromaDB.

Run this after adding new notes to data/notes/:
    uv run python scripts/index_notes.py
"""

import logging
import sys

# Add project root to path
sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from core_mcp.vector_store.indexer import Indexer


def main():
    print("=" * 50)
    print("  Personal MCP — Note Indexer")
    print("=" * 50)

    indexer = Indexer()
    stats = indexer.index_all_notes()

    print(f"\n✅ Indexing complete!")
    print(f"   Files found:   {stats['total_files']}")
    print(f"   Files indexed: {stats['indexed_files']}")
    print(f"   Total chunks:  {stats['total_chunks']}")

    if stats["errors"]:
        print(f"\n⚠️  Skipped {len(stats['errors'])} files:")
        for err in stats["errors"]:
            print(f"   - {err['file']}: {err['error']}")


if __name__ == "__main__":
    main()

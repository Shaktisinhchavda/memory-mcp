"""
Index Notes Script — Incremental indexing of notes into ChromaDB.

Only re-indexes new or modified files by default.
Use --force for a full rebuild.

    uv run python scripts/index_notes.py          # incremental
    uv run python scripts/index_notes.py --force   # full rebuild
"""

import logging
import sys

sys.path.insert(0, ".")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from core_mcp.vector_store.indexer import Indexer


def main():
    force = "--force" in sys.argv

    print("=" * 50)
    print("  Personal MCP — Note Indexer")
    print(f"  Mode: {'FULL REBUILD' if force else 'INCREMENTAL'}")
    print("=" * 50)

    indexer = Indexer()
    stats = indexer.index_all_notes(force=force)

    print(f"\nIndexing complete!")
    print(f"   Mode:              {stats['mode']}")
    print(f"   Files found:       {stats['total_files']}")
    print(f"   Files indexed:     {stats['indexed_files']}")
    print(f"   Skipped unchanged: {stats['skipped_unchanged']}")
    print(f"   Total chunks:      {stats['total_chunks']}")

    if stats["errors"]:
        print(f"\n   Skipped {len(stats['errors'])} files:")
        for err in stats["errors"]:
            print(f"   - {err['file']}: {err['error']}")


if __name__ == "__main__":
    main()

"""
ChromaDB Vector Store — Local semantic storage for your personal data.

This module wraps ChromaDB with sentence-transformers to provide:
- Local-only embeddings (nothing leaves your machine)
- Persistent storage across restarts
- Metadata-rich document indexing
- Fast semantic similarity search

Usage:
    from core_mcp.vector_store.store import VectorStore
    
    store = VectorStore()
    store.add_document("my_note.md", "Contents of the note...", {"tags": "work"})
    results = store.search("what did I write about AI?", top_k=5)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-backed vector store with sentence-transformer embeddings.
    
    All data is stored locally in the path specified by CHROMA_DB_PATH.
    Uses the all-MiniLM-L6-v2 model (384 dimensions) by default.
    """

    COLLECTION_NAME = "personal_notes"

    def __init__(self) -> None:
        """Initialize ChromaDB client and embedding function."""
        settings.ensure_directories()

        # Resolve to absolute path for ChromaDB
        db_path = str(settings.chroma_db_path.resolve())
        logger.info(f"Initializing ChromaDB at: {db_path}")

        self._client = chromadb.PersistentClient(path=db_path)
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model,
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"description": "Personal notes and documents"},
        )
        logger.info(
            f"Collection '{self.COLLECTION_NAME}' ready "
            f"({self._collection.count()} documents)"
        )

    def add_document(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add or update a document in the vector store.

        Args:
            doc_id: Unique identifier (typically the filename).
            content: Full text content to embed.
            metadata: Optional metadata dict (filename, date, tags, etc.).
        """
        meta = {
            "filename": doc_id,
            "indexed_at": datetime.now().isoformat(),
            **(metadata or {}),
        }

        # ChromaDB upsert: adds if new, updates if exists
        self._collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[meta],
        )
        logger.info(f"Indexed document: {doc_id}")

    def add_chunks(
        self,
        doc_id: str,
        chunks: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a document as multiple chunks for better retrieval.

        Long documents are split into smaller chunks so semantic search
        can find the most relevant *section*, not just the most relevant file.

        Args:
            doc_id: Base document identifier.
            chunks: List of text chunks from the document.
            metadata: Shared metadata applied to all chunks.
        """
        ids = [f"{doc_id}::chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "filename": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "indexed_at": datetime.now().isoformat(),
                **(metadata or {}),
            }
            for i in range(len(chunks))
        ]

        self._collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )
        logger.info(f"Indexed {len(chunks)} chunks for: {doc_id}")

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic similarity search.

        Args:
            query: Natural language search query.
            top_k: Number of results to return (default 5).

        Returns:
            List of dicts with keys: id, content, metadata, distance.
            Lower distance = more similar.
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count() or 1),
            include=["documents", "metadatas", "distances"],
        )

        # Reshape ChromaDB's nested list format into a clean list of dicts
        output = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                output.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                })

        return output

    def delete_document(self, doc_id: str) -> None:
        """Remove a document (and all its chunks) from the store."""
        # Get all IDs that start with this doc_id (handles chunks)
        all_ids = self._collection.get(
            where={"filename": doc_id},
            include=[],
        )["ids"]

        if all_ids:
            self._collection.delete(ids=all_ids)
            logger.info(f"Deleted {len(all_ids)} entries for: {doc_id}")

    @property
    def count(self) -> int:
        """Total number of documents/chunks in the store."""
        return self._collection.count()

    def reset(self) -> None:
        """Delete the entire collection. Use with caution!"""
        self._client.delete_collection(self.COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._embedding_fn,
        )
        logger.warning("Vector store collection has been reset.")

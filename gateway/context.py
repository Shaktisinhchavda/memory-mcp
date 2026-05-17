"""
PersonalContext — Unified response model for the gateway.

Aggregates results from all MCP tools into a single structured
response that any AI caller can consume.
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ContextSource(BaseModel):
    """A single piece of context from one source."""
    source: str = Field(description="Which tool/server provided this")
    content: str = Field(description="The actual content")
    relevance: float = Field(default=0.5, description="Relevance score 0-1")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalContext(BaseModel):
    """
    Unified context object returned by the gateway.

    Combines vector search results, graph connections, recent activity,
    and file contents into a single ranked response.
    """
    query: str = Field(description="Original query")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sources: list[ContextSource] = Field(default_factory=list)
    summary: str = Field(default="", description="AI-generated summary if available")
    total_sources: int = Field(default=0)

    # Breakdown by category
    semantic_results: list[dict[str, Any]] = Field(default_factory=list)
    graph_results: list[dict[str, Any]] = Field(default_factory=list)
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)
    file_contents: list[dict[str, Any]] = Field(default_factory=list)

    def add_source(self, source: str, content: str, relevance: float = 0.5, **meta):
        """Add a context source and update total count."""
        self.sources.append(ContextSource(
            source=source, content=content, relevance=relevance, metadata=meta,
        ))
        self.total_sources = len(self.sources)

    def ranked_sources(self) -> list[ContextSource]:
        """Return sources sorted by relevance (highest first)."""
        return sorted(self.sources, key=lambda s: s.relevance, reverse=True)

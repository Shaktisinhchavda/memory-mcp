"""
Configuration module for the Personal MCP Ecosystem.

Uses pydantic-settings to load environment variables from .env file
with type validation and sensible defaults.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the MCP ecosystem.
    
    All settings are loaded from environment variables or .env file.
    Every setting has a sensible default so the system works out of the box.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Paths ---
    data_dir: Path = Path("./data")
    notes_dir: Path = Path("./data/notes")
    files_dir: Path = Path("./data/files")

    # --- Vector Store ---
    chroma_db_path: Path = Path("./.chroma")
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Event Logger ---
    events_db_path: Path = Path("./events.db")

    # --- MCP Server ---
    mcp_server_name: str = "memory-mcp"
    mcp_transport: str = "stdio"

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)


# Singleton instance — import this everywhere
settings = Settings()
